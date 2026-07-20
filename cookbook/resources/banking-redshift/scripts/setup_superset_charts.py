#!/usr/bin/env python3
"""Provision the banking-redshift demo in Superset.

Creates (idempotently):
  - One Redshift database connection
  - One dataset per mart table listed in DATASETS
  - One chart per entry in CHARTS
  - One dashboard per entry in DASHBOARDS, with charts attached

Only the Python standard library is used (urllib, json) so the script can
run inside any environment that has Python 3 available.

Re-runs are safe: 409 / 422 responses are treated as "already exists" and
silently skipped.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

SUPERSET_URL = os.environ.get("SUPERSET_URL", "http://localhost:8088")
ADMIN_USER = os.environ.get("SUPERSET_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("SUPERSET_ADMIN_PASSWORD", "BankAdmin123!")

# Populated by login()/get_csrf().
ACCESS_TOKEN: str | None = None
CSRF_TOKEN: str | None = None


def api(
    method: str,
    path: str,
    body: dict | None = None,
    headers: dict | None = None,
) -> dict:
    """Make a JSON API call. Returns parsed JSON, or an ``{"error": ...}``
    dict for HTTP errors so callers can branch on status without raising.
    """
    url = f"{SUPERSET_URL}{path}"
    req = urllib.request.Request(url, method=method)

    # Default auth headers — callers can still override via ``headers``.
    if ACCESS_TOKEN and "/security/login" not in path:
        req.add_header("Authorization", f"Bearer {ACCESS_TOKEN}")
    if CSRF_TOKEN and method.upper() not in ("GET", "HEAD"):
        req.add_header("X-CSRFToken", CSRF_TOKEN)
        req.add_header("Referer", SUPERSET_URL)

    if headers:
        for k, v in headers.items():
            req.add_header(k, v)

    data = None
    if body is not None:
        req.add_header("Content-Type", "application/json")
        data = json.dumps(body).encode()

    try:
        with urllib.request.urlopen(req, data) as r:
            raw = r.read()
            if not raw:
                return {}
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode()
        except Exception:
            err_body = ""
        return {"error": e.code, "body": err_body}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def login() -> None:
    global ACCESS_TOKEN
    res = api(
        "POST",
        "/api/v1/security/login",
        body={
            "username": ADMIN_USER,
            "password": ADMIN_PASSWORD,
            "provider": "db",
            "refresh": True,
        },
    )
    if "access_token" not in res:
        print(f"ERROR: login failed: {res}", file=sys.stderr)
        sys.exit(1)
    ACCESS_TOKEN = res["access_token"]
    print("Logged in to Superset.")


def get_csrf() -> None:
    global CSRF_TOKEN
    res = api("GET", "/api/v1/security/csrf_token/")
    if "result" in res:
        CSRF_TOKEN = res["result"]
        print("Fetched CSRF token.")
    else:
        # WTF_CSRF_ENABLED is False in superset_config.py, so this is
        # non-fatal — Superset will accept requests without the header.
        print(f"WARN: could not fetch CSRF token (continuing): {res}")


# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------


def get_or_create_database() -> int | None:
    """Create the Redshift connection if not already present.

    Returns the database ID. Returns None on failure so the caller can
    abort gracefully.
    """
    db_name = "Banking Redshift"

    # Build parameters up-front so the existing-found path can also patch.
    host = os.environ.get("REDSHIFT_HOST")
    port = os.environ.get("REDSHIFT_PORT", "5439")
    database = os.environ.get("REDSHIFT_DATABASE")
    user = os.environ.get("REDSHIFT_USER")
    password = os.environ.get("REDSHIFT_PASSWORD")

    if not all([host, database, user, password]):
        print("ERROR: REDSHIFT_HOST/DATABASE/USER/PASSWORD must be set.", file=sys.stderr)
        return None

    from urllib.parse import quote_plus

    sqlalchemy_uri = (
        f"redshift+redshift_connector://{user}:{quote_plus(password)}@{host}:{port}/{database}"
    )

    # `parameters` is required so the OpenMetadata Superset connector can
    # read the warehouse database name and emit cross-service lineage to the
    # Redshift tables. Without it, OM resolves database_name=None and skips
    # lineage even though dbServiceNames is configured.
    db_parameters = {
        "host": host,
        "port": int(port),
        "database": database,
        "username": user,
        "password": password,
    }

    # Check if a database with that name already exists.
    existing = api(
        "GET",
        "/api/v1/database/?q=" + urllib.parse.quote(
            json.dumps({"filters": [{"col": "database_name", "opr": "eq", "value": db_name}]})
        ),
    )
    if "result" in existing and existing["result"]:
        db_id = existing["result"][0]["id"]
        print(f"Database '{db_name}' already exists (id={db_id}).")
        _ensure_db_parameters(db_id, db_parameters)
        return db_id

    res = api(
        "POST",
        "/api/v1/database/",
        body={
            "database_name": db_name,
            "sqlalchemy_uri": sqlalchemy_uri,
            "engine": "redshift+redshift_connector",
            "parameters": db_parameters,
            "expose_in_sqllab": True,
            "allow_ctas": False,
            "allow_cvas": False,
            "allow_dml": False,
        },
    )
    if "id" in res:
        db_id = res["id"]
        print(f"Created database '{db_name}' (id={db_id}).")
        _ensure_db_parameters(db_id, db_parameters)
        return db_id
    if res.get("error") in (409, 422):
        existing = api(
            "GET",
            "/api/v1/database/?q=" + urllib.parse.quote(
                json.dumps({"filters": [{"col": "database_name", "opr": "eq", "value": db_name}]})
            ),
        )
        if "result" in existing and existing["result"]:
            db_id = existing["result"][0]["id"]
            _ensure_db_parameters(db_id, db_parameters)
            return db_id
    print(f"ERROR: could not create database: {res}", file=sys.stderr)
    return None


def _ensure_db_parameters(db_id: int, parameters: dict) -> None:
    """Make sure the Superset DB connection carries `parameters.database`.

    The OM Superset connector reads it via `database.parameters.database`
    when building cross-service lineage; missing it = no lineage.
    """
    cur = api("GET", f"/api/v1/database/{db_id}")
    current = (cur.get("result") or {}).get("parameters") or {}
    if current.get("database"):
        return
    res = api(
        "PUT",
        f"/api/v1/database/{db_id}",
        body={"parameters": parameters},
    )
    if "error" in res:
        print(f"  WARN: could not PATCH database parameters: {res}")
    else:
        print(f"  Patched database {db_id} parameters.database={parameters['database']}.")


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------

# (schema, table) pairs for every mart we want to expose.
DATASETS: list[tuple[str, str]] = [
    ("marts_finance", "fct_nim"),
    ("marts_finance", "fct_monthly_pnl"),
    ("marts_finance", "fct_fee_revenue"),
    ("marts_finance", "fct_branch_performance"),
    ("marts_finance", "fct_daily_balances"),
    ("marts_risk", "fct_delinquency"),
    ("marts_risk", "fct_loan_loss_provision"),
    ("marts_risk", "fct_aml_pipeline"),
    ("marts_risk", "dim_credit_risk"),
    ("marts_core", "dim_customers"),
    ("marts_core", "dim_accounts"),
    ("marts_core", "dim_branches"),
    ("marts_core", "fct_transactions"),
    ("marts_core", "dim_cards"),
    ("marts_wealth", "fct_aum"),
    ("marts_wealth", "fct_trades"),
    ("marts_marketing", "fct_campaign_attribution"),
    ("marts_marketing", "fct_customer_engagement"),
]


def get_or_create_dataset(db_id: int, schema: str, table: str) -> int | None:
    """Create a dataset for ``schema.table`` if it doesn't already exist."""
    # Check first.
    q = json.dumps(
        {
            "filters": [
                {"col": "table_name", "opr": "eq", "value": table},
                {"col": "schema", "opr": "eq", "value": schema},
            ]
        }
    )
    existing = api("GET", "/api/v1/dataset/?q=" + urllib.parse.quote(q))
    if "result" in existing and existing["result"]:
        ds_id = existing["result"][0]["id"]
        print(f"  Dataset {schema}.{table} already exists (id={ds_id}).")
        return ds_id

    res = api(
        "POST",
        "/api/v1/dataset/",
        body={"database": db_id, "schema": schema, "table_name": table},
    )
    if "id" in res:
        print(f"  Created dataset {schema}.{table} (id={res['id']}).")
        return res["id"]
    if res.get("error") in (409, 422):
        # Re-query
        existing = api("GET", "/api/v1/dataset/?q=" + urllib.parse.quote(q))
        if "result" in existing and existing["result"]:
            return existing["result"][0]["id"]
    print(f"  WARN: could not create dataset {schema}.{table}: {res}")
    return None


# ---------------------------------------------------------------------------
# Chart param builders
# ---------------------------------------------------------------------------


def metric(column: str, aggregate: str = "SUM", label: str | None = None) -> dict:
    """Build a Superset 'adhoc metric' object."""
    return {
        "label": label or f"{aggregate}({column})",
        "expressionType": "SIMPLE",
        "column": {"column_name": column},
        "aggregate": aggregate,
        "optionName": f"metric_{column}_{aggregate.lower()}",
    }


def line_params(x_axis: str, metric_col: str, aggregate: str = "SUM") -> dict:
    return {
        "viz_type": "line",
        "x_axis": x_axis,
        "metrics": [metric(metric_col, aggregate)],
        "groupby": [],
        "time_range": "No filter",
        "row_limit": 10000,
        "color_scheme": "supersetColors",
    }


def bar_params(
    x_axis: str,
    metric_col: str,
    aggregate: str = "SUM",
    row_limit: int = 1000,
    groupby: list[str] | None = None,
) -> dict:
    return {
        "viz_type": "bar",
        "x_axis": x_axis,
        "metrics": [metric(metric_col, aggregate)],
        "groupby": groupby or [],
        "row_limit": row_limit,
        "time_range": "No filter",
        "color_scheme": "supersetColors",
    }


def big_number_params(metric_col: str, aggregate: str = "SUM") -> dict:
    return {
        "viz_type": "big_number_total",
        "metric": metric(metric_col, aggregate),
        "time_range": "No filter",
        "y_axis_format": "SMART_NUMBER",
    }


def pie_params(groupby: str, metric_col: str, aggregate: str = "SUM") -> dict:
    return {
        "viz_type": "pie",
        "groupby": [groupby],
        "metric": metric(metric_col, aggregate),
        "row_limit": 100,
        "color_scheme": "supersetColors",
    }


def table_params(all_columns: list[str], row_limit: int = 100) -> dict:
    return {
        "viz_type": "table",
        "all_columns": all_columns,
        "metrics": [],
        "row_limit": row_limit,
        "query_mode": "raw",
    }


def funnel_params(groupby: str, metric_col: str, aggregate: str = "SUM") -> dict:
    return {
        "viz_type": "funnel",
        "groupby": [groupby],
        "metric": metric(metric_col, aggregate),
        "row_limit": 100,
    }


def histogram_params(column: str, bins: int = 25) -> dict:
    return {
        "viz_type": "histogram",
        "all_columns_x": [column],
        "row_limit": 10000,
        "link_length": bins,
    }


def stacked_bar_params(x_axis: str, metric_col: str, color_col: str) -> dict:
    return {
        "viz_type": "bar",
        "x_axis": x_axis,
        "metrics": [metric(metric_col, "SUM")],
        "groupby": [color_col],
        "stacked_style": "stack",
        "row_limit": 10000,
        "time_range": "No filter",
        "color_scheme": "supersetColors",
    }


# ---------------------------------------------------------------------------
# Chart definitions
# ---------------------------------------------------------------------------
# Each entry: (chart_name, viz_type, (schema, table), params_builder, dashboard_name)

CHARTS: list[tuple[str, str, tuple[str, str], dict, str]] = [
    # -------- Executive / CFO --------
    (
        "Monthly NIM Trend",
        "line",
        ("marts_finance", "fct_nim"),
        line_params("period_month", "nim_pct", "AVG"),
        "Executive / CFO",
    ),
    (
        "Net Interest Income (Monthly)",
        "bar",
        ("marts_finance", "fct_nim"),
        bar_params("period_month", "net_interest_income"),
        "Executive / CFO",
    ),
    (
        "Fee Revenue by Category",
        "bar",
        ("marts_finance", "fct_fee_revenue"),
        bar_params("fee_category", "fee_amount"),
        "Executive / CFO",
    ),
    (
        "Top 5 Branches by Deposits",
        "bar",
        ("marts_finance", "fct_branch_performance"),
        bar_params("branch_name", "total_deposits", row_limit=5),
        "Executive / CFO",
    ),
    (
        "Deposit-to-Loan Ratio (Monthly)",
        "line",
        ("marts_finance", "fct_branch_performance"),
        line_params("period_month", "deposit_to_loan_ratio", "AVG"),
        "Executive / CFO",
    ),
    (
        "Loan-Loss Provision Total",
        "big_number_total",
        ("marts_risk", "fct_loan_loss_provision"),
        big_number_params("expected_credit_loss"),
        "Executive / CFO",
    ),
    # -------- Risk & Compliance --------
    (
        "AML Alert Funnel",
        "funnel",
        ("marts_risk", "fct_aml_pipeline"),
        funnel_params("alert_type", "alerts_count"),
        "Risk & Compliance",
    ),
    (
        "Delinquency Aging",
        "bar",
        ("marts_risk", "fct_delinquency"),
        stacked_bar_params("period_month", "loan_balance", "delinquency_bucket"),
        "Risk & Compliance",
    ),
    (
        "ECL Trend",
        "line",
        ("marts_risk", "fct_loan_loss_provision"),
        line_params("period_month", "expected_credit_loss"),
        "Risk & Compliance",
    ),
    (
        "Credit Score Distribution",
        "histogram",
        ("marts_risk", "dim_credit_risk"),
        histogram_params("fico_score"),
        "Risk & Compliance",
    ),
    (
        "Top AML Alert Types",
        "pie",
        ("marts_risk", "fct_aml_pipeline"),
        pie_params("alert_type", "alerts_count"),
        "Risk & Compliance",
    ),
    # -------- Customer & Ops --------
    (
        "Active vs Dormant Accounts",
        "pie",
        ("marts_core", "dim_accounts"),
        pie_params("status", "account_id", "COUNT"),
        "Customer & Ops",
    ),
    (
        "AUM by Customer Segment",
        "bar",
        ("marts_wealth", "fct_aum"),
        bar_params("customer_segment", "aum_amount"),
        "Customer & Ops",
    ),
    (
        "Account Opening Velocity",
        "line",
        ("marts_core", "dim_accounts"),
        line_params("opened_date", "account_id", "COUNT"),
        "Customer & Ops",
    ),
    (
        "Customer Count by Segment",
        "pie",
        ("marts_core", "dim_customers"),
        pie_params("value_segment", "customer_id", "COUNT"),
        "Customer & Ops",
    ),
    (
        "Top 10 Customers by Total Balance",
        "table",
        ("marts_core", "dim_customers"),
        table_params(
            ["customer_id", "full_name", "value_segment", "total_balance"],
            row_limit=10,
        ),
        "Customer & Ops",
    ),
    # -------- Digital Engagement --------
    (
        "Mobile DAU Trend",
        "line",
        ("marts_marketing", "fct_customer_engagement"),
        line_params("event_date", "customer_id", "COUNT_DISTINCT"),
        "Digital Engagement",
    ),
    (
        "Login Failure Rate",
        "line",
        ("marts_marketing", "fct_customer_engagement"),
        line_params("event_date", "login_failure_rate", "AVG"),
        "Digital Engagement",
    ),
    (
        "Campaign Conversion Rate",
        "bar",
        ("marts_marketing", "fct_campaign_attribution"),
        bar_params("campaign_name", "conversion_rate", "AVG"),
        "Digital Engagement",
    ),
    (
        "Mobile Event Volume by Type",
        "bar",
        ("marts_marketing", "fct_customer_engagement"),
        bar_params("event_type", "event_count"),
        "Digital Engagement",
    ),
]

DASHBOARDS: list[str] = [
    "Executive / CFO",
    "Risk & Compliance",
    "Customer & Ops",
    "Digital Engagement",
]


# ---------------------------------------------------------------------------
# Chart creation
# ---------------------------------------------------------------------------


def create_chart(
    name: str,
    viz_type: str,
    dataset_id: int,
    params: dict,
    dashboard_ids: list[int],
) -> int | None:
    """Create (or skip) a chart by name."""
    q = json.dumps({"filters": [{"col": "slice_name", "opr": "eq", "value": name}]})
    existing = api("GET", "/api/v1/chart/?q=" + urllib.parse.quote(q))
    if "result" in existing and existing["result"]:
        chart_id = existing["result"][0]["id"]
        print(f"  Chart '{name}' already exists (id={chart_id}).")
        # Still ensure it's wired to the requested dashboards.
        attach_chart_to_dashboards(chart_id, dashboard_ids)
        return chart_id

    # Superset wants the datasource baked into params as "<id>__table".
    params_with_ds = dict(params)
    params_with_ds["datasource"] = f"{dataset_id}__table"

    body = {
        "slice_name": name,
        "viz_type": viz_type,
        "datasource_id": dataset_id,
        "datasource_type": "table",
        "params": json.dumps(params_with_ds),
        "dashboards": dashboard_ids,
    }
    res = api("POST", "/api/v1/chart/", body=body)
    if "id" in res:
        print(f"  Created chart '{name}' (id={res['id']}).")
        return res["id"]
    if res.get("error") in (409, 422):
        # Race — re-query.
        existing = api("GET", "/api/v1/chart/?q=" + urllib.parse.quote(q))
        if "result" in existing and existing["result"]:
            return existing["result"][0]["id"]
    print(f"  WARN: could not create chart '{name}': {res}")
    return None


def attach_chart_to_dashboards(chart_id: int, dashboard_ids: list[int]) -> None:
    """Ensure a chart belongs to all of the given dashboards (idempotent).

    Writes BOTH:
      1. The chart.dashboards M:N association (shows in /chart/{id}/dashboards)
      2. The dashboard.position_json layout grid (what BI tools — and the
         OpenMetadata Superset connector — read to enumerate dashboard charts)
    """
    if not dashboard_ids:
        return
    # 1) Association table
    cur = api("GET", f"/api/v1/chart/{chart_id}")
    current_ids: list[int] = []
    chart_name = ""
    if "result" in cur:
        current_ids = [d["id"] for d in cur["result"].get("dashboards", [])]
        chart_name = cur["result"].get("slice_name", "")
    merged = sorted(set(current_ids + dashboard_ids))
    if merged != sorted(current_ids):
        res = api("PUT", f"/api/v1/chart/{chart_id}", body={"dashboards": merged})
        if "error" in res:
            print(f"  WARN: could not attach chart {chart_id} to dashboards: {res}")

    # 2) Dashboard layout grid
    for d_id in dashboard_ids:
        ensure_chart_in_position_json(d_id, chart_id, chart_name)


def ensure_chart_in_position_json(
    dashboard_id: int, chart_id: int, chart_name: str
) -> None:
    """Place a chart on a dashboard's position_json grid (idempotent)."""
    dash = api("GET", f"/api/v1/dashboard/{dashboard_id}")
    if "result" not in dash:
        print(f"  WARN: cannot load dashboard {dashboard_id} to update layout: {dash}")
        return
    raw_pos = dash["result"].get("position_json") or "{}"
    try:
        position = json.loads(raw_pos) if raw_pos else {}
    except json.JSONDecodeError:
        position = {}

    # Already on grid? bail.
    chart_node_id = f"CHART-{chart_id}"
    if chart_node_id in position:
        return

    # Seed the root grid skeleton on first use.
    if "ROOT_ID" not in position:
        position = {
            "DASHBOARD_VERSION_KEY": "v2",
            "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
            "GRID_ID": {
                "type": "GRID",
                "id": "GRID_ID",
                "children": [],
                "parents": ["ROOT_ID"],
            },
        }

    grid = position["GRID_ID"]
    # Find or create a row that has space (each row holds 2 charts at width=6).
    target_row_id = None
    for row_id in grid["children"]:
        row = position.get(row_id, {})
        if row.get("type") == "ROW" and len(row.get("children", [])) < 2:
            target_row_id = row_id
            break
    if target_row_id is None:
        target_row_id = f"ROW-{len(grid['children']) + 1}"
        position[target_row_id] = {
            "type": "ROW",
            "id": target_row_id,
            "children": [],
            "parents": ["ROOT_ID", "GRID_ID"],
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }
        grid["children"].append(target_row_id)

    position[target_row_id]["children"].append(chart_node_id)
    position[chart_node_id] = {
        "type": "CHART",
        "id": chart_node_id,
        "children": [],
        "parents": ["ROOT_ID", "GRID_ID", target_row_id],
        "meta": {
            "chartId": chart_id,
            "sliceName": chart_name or f"Chart {chart_id}",
            "width": 6,
            "height": 50,
            "uuid": str(uuid.uuid4()),
        },
    }

    res = api(
        "PUT",
        f"/api/v1/dashboard/{dashboard_id}",
        body={"position_json": json.dumps(position)},
    )
    if "error" in res:
        print(
            f"  WARN: could not update position_json on dashboard {dashboard_id}: {res}"
        )


# ---------------------------------------------------------------------------
# Dashboards
# ---------------------------------------------------------------------------


def _all_dashboards_by_title() -> dict[str, int]:
    """Walk the full /dashboard/ paginated list, return {title: id}.

    Avoids the q-rison filter which doesn't reliably accept JSON in Superset
    4.x and was silently returning empty for some titles.
    """
    by_title: dict[str, int] = {}
    page = 0
    while True:
        res = api("GET", f"/api/v1/dashboard/?q=(page:{page},page_size:100)")
        rows = res.get("result", []) if isinstance(res, dict) else []
        if not rows:
            break
        for d in rows:
            by_title[d["dashboard_title"]] = d["id"]
        if len(rows) < 100:
            break
        page += 1
    return by_title


def get_or_create_dashboard(title: str) -> int | None:
    existing = _all_dashboards_by_title()
    if title in existing:
        dash_id = existing[title]
        print(f"Dashboard '{title}' already exists (id={dash_id}).")
        return dash_id

    slug = title.lower().replace(" / ", "-").replace(" & ", "-").replace(" ", "-")
    res = api(
        "POST",
        "/api/v1/dashboard/",
        body={
            "dashboard_title": title,
            "slug": slug,
            "published": True,
        },
    )
    if "id" in res:
        print(f"Created dashboard '{title}' (id={res['id']}).")
        return res["id"]
    # POST failed (409 / 422). Re-fetch the full list to recover the id of the
    # existing dashboard whose slug or title we collided with.
    if res.get("error") in (409, 422):
        for found_title, found_id in _all_dashboards_by_title().items():
            if found_title == title:
                print(f"Dashboard '{title}' exists from a prior run (id={found_id}).")
                return found_id
    print(f"WARN: could not create dashboard '{title}': {res}")
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    print(f"Superset URL: {SUPERSET_URL}")
    login()
    get_csrf()

    db_id = get_or_create_database()
    if db_id is None:
        return 1

    # Create datasets.
    print("\nCreating datasets ...")
    dataset_ids: dict[tuple[str, str], int] = {}
    for schema, table in DATASETS:
        ds_id = get_or_create_dataset(db_id, schema, table)
        if ds_id is not None:
            dataset_ids[(schema, table)] = ds_id

    # Create dashboards first so we can attach charts on creation.
    print("\nCreating dashboards ...")
    dashboard_ids: dict[str, int] = {}
    for title in DASHBOARDS:
        d_id = get_or_create_dashboard(title)
        if d_id is not None:
            dashboard_ids[title] = d_id

    # Create charts.
    print("\nCreating charts ...")
    for name, viz_type, (schema, table), params, dashboard_name in CHARTS:
        ds_id = dataset_ids.get((schema, table))
        if ds_id is None:
            print(f"  SKIP '{name}': dataset {schema}.{table} not available.")
            continue
        d_id = dashboard_ids.get(dashboard_name)
        create_chart(
            name=name,
            viz_type=viz_type,
            dataset_id=ds_id,
            params=params,
            dashboard_ids=[d_id] if d_id else [],
        )

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
