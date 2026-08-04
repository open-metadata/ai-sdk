"""Single source of truth for the banking demo's raw table schemas.

Every raw table is declared once here, in CSV column order. Three consumers
read it:

* ``scripts/generate_ddl.py`` renders ``sql/redshift_init.sql``,
  ``sql/bigquery_init.sql`` and the ``sql/bq_schemas/*.json`` payloads that
  ``bq load`` consumes.
* ``scripts/generate_seed_data.py`` takes CSV headers from it.
* ``scripts/<warehouse>/load_*.sh`` iterate the schema/table pairs.

Because all of them share this declaration, column order cannot drift between
the CSVs and either warehouse's DDL.

Logical types are warehouse-neutral. ``generate_ddl.py`` owns the mapping to
each dialect's concrete types.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache


@dataclass(frozen=True)
class LogicalType:
    """A warehouse-neutral column type.

    ``length`` applies to strings, ``precision``/``scale`` to decimals. The
    remaining kinds carry no parameters.
    """

    kind: str
    length: int | None = None
    precision: int | None = None
    scale: int | None = None


def string(length: int) -> LogicalType:
    """Variable-length text of at most ``length`` characters."""
    return LogicalType(kind="string", length=length)


def decimal(precision: int, scale: int) -> LogicalType:
    """Fixed-point number with ``precision`` total digits, ``scale`` after the point."""
    return LogicalType(kind="decimal", precision=precision, scale=scale)


INT = LogicalType(kind="int")
BOOL = LogicalType(kind="bool")
DATE = LogicalType(kind="date")
TIMESTAMP = LogicalType(kind="timestamp")


@dataclass(frozen=True)
class Column:
    name: str
    type: LogicalType


@dataclass(frozen=True)
class Distribution:
    """Redshift distribution and sort choices.

    BigQuery ignores this entirely: it has no distribution styles, and its
    automatic clustering makes an explicit sort key unnecessary at this scale.
    """

    style: str
    key: str | None = None
    sort_key: str | None = None


AUTO = Distribution(style="AUTO")
ALL = Distribution(style="ALL")


@dataclass(frozen=True)
class Table:
    schema: str
    name: str
    distribution: Distribution
    columns: tuple[Column, ...]


@cache
def all_tables() -> tuple[Table, ...]:
    """Every raw table in the demo, in the order the loaders should process them."""
    return (
        # raw_core_banking --------------------------------------------------
        Table(
            schema="raw_core_banking",
            name="customers",
            distribution=AUTO,
            columns=(
                Column("customer_id",         string(30)),
                Column("first_name",          string(120)),
                Column("last_name",           string(80)),
                Column("email",               string(160)),
                Column("phone",               string(20)),
                Column("ssn",                 string(11)),
                Column("tax_id",              string(20)),
                Column("date_of_birth",       DATE),
                Column("customer_segment",    string(30)),
                Column("customer_type",       string(30)),
                Column("branch_id",           string(30)),
                Column("primary_employee_id", string(30)),
                Column("kyc_status",          string(20)),
                Column("risk_band",           string(20)),
                Column("created_at",          TIMESTAMP),
                Column("updated_at",          TIMESTAMP),
            ),
        ),
        Table(
            schema="raw_core_banking",
            name="customer_addresses",
            distribution=AUTO,
            columns=(
                Column("address_id",     string(30)),
                Column("customer_id",    string(30)),
                Column("address_type",   string(20)),
                Column("address_line_1", string(120)),
                Column("address_line_2", string(120)),
                Column("city",           string(80)),
                Column("state",          string(20)),
                Column("postal_code",    string(20)),
                Column("country",        string(20)),
                Column("is_primary",     BOOL),
                Column("effective_from", DATE),
                Column("effective_to",   DATE),
            ),
        ),
        Table(
            schema="raw_core_banking",
            name="customer_contacts",
            distribution=AUTO,
            columns=(
                Column("contact_id",    string(30)),
                Column("customer_id",   string(30)),
                Column("contact_type",  string(20)),
                Column("contact_value", string(120)),
                Column("is_primary",    BOOL),
                Column("is_verified",   BOOL),
                Column("opt_out",       BOOL),
                Column("added_at",      TIMESTAMP),
            ),
        ),
        Table(
            schema="raw_core_banking",
            name="branches",
            distribution=ALL,
            columns=(
                Column("branch_id",           string(30)),
                Column("branch_name",         string(80)),
                Column("address_line_1",      string(120)),
                Column("city",                string(80)),
                Column("state",               string(20)),
                Column("postal_code",         string(20)),
                Column("country",             string(20)),
                Column("region",              string(30)),
                Column("phone",               string(20)),
                Column("manager_employee_id", string(30)),
                Column("opened_date",         DATE),
                Column("closed_date",         DATE),
                Column("is_active",           BOOL),
            ),
        ),
        Table(
            schema="raw_core_banking",
            name="employees",
            distribution=AUTO,
            columns=(
                Column("employee_id",      string(30)),
                Column("first_name",       string(80)),
                Column("last_name",        string(80)),
                Column("email",            string(120)),
                Column("phone",            string(20)),
                Column("hire_date",        DATE),
                Column("termination_date", DATE),
                Column("role",             string(80)),
                Column("branch_id",        string(30)),
                Column("manager_id",       string(30)),
                Column("salary_band",      string(20)),
                Column("is_active",        BOOL),
            ),
        ),
        Table(
            schema="raw_core_banking",
            name="accounts",
            distribution=AUTO,
            columns=(
                Column("account_id",    string(30)),
                Column("customer_id",   string(30)),
                Column("account_type",  string(30)),
                Column("product_code",  string(30)),
                Column("opened_date",   DATE),
                Column("closed_date",   DATE),
                Column("status",        string(20)),
                Column("balance",       decimal(18,4)),
                Column("currency",      string(3)),
                Column("branch_id",     string(30)),
                Column("interest_rate", decimal(10,6)),
                Column("credit_limit",  decimal(18,4)),
                Column("is_joint",      BOOL),
                Column("created_at",    TIMESTAMP),
                Column("updated_at",    TIMESTAMP),
            ),
        ),
        Table(
            schema="raw_core_banking",
            name="account_holders",
            distribution=AUTO,
            columns=(
                Column("holder_id",    string(30)),
                Column("account_id",   string(30)),
                Column("customer_id",  string(30)),
                Column("holder_order", INT),
                Column("relationship", string(30)),
                Column("added_at",     TIMESTAMP),
                Column("removed_at",   TIMESTAMP),
            ),
        ),
        Table(
            schema="raw_core_banking",
            name="account_types",
            distribution=ALL,
            columns=(
                Column("account_type_code", string(30)),
                Column("account_type_name", string(80)),
                Column("product_category",  string(30)),
            ),
        ),

        # raw_transactions --------------------------------------------------
        Table(
            schema="raw_transactions",
            name="transactions",
            distribution=Distribution(style="KEY", key="account_id", sort_key="posted_at"),
            columns=(
                Column("transaction_id",   string(30)),
                Column("account_id",       string(30)),
                Column("posted_at",        TIMESTAMP),
                Column("amount",           decimal(18,4)),
                Column("currency",         string(3)),
                Column("transaction_type", string(30)),
                Column("merchant_id",      string(30)),
                Column("description",      string(500)),
                Column("is_reversal",      BOOL),
                Column("channel",          string(30)),
                Column("running_balance",  decimal(18,4)),
                Column("created_at",       TIMESTAMP),
            ),
        ),
        Table(
            schema="raw_transactions",
            name="transaction_categories",
            distribution=ALL,
            columns=(
                Column("category_code",  string(30)),
                Column("category_name",  string(80)),
                Column("category_group", string(30)),
                Column("sign_hint",      string(20)),
            ),
        ),
        Table(
            schema="raw_transactions",
            name="atm_withdrawals",
            distribution=Distribution(style="KEY", key="account_id", sort_key="withdrawn_at"),
            columns=(
                Column("atm_withdrawal_id",     string(30)),
                Column("account_id",            string(30)),
                Column("atm_terminal_id",       string(30)),
                Column("atm_city",              string(80)),
                Column("atm_state",             string(20)),
                Column("amount",                decimal(18,4)),
                Column("fee_amount",            decimal(18,4)),
                Column("withdrawn_at",          TIMESTAMP),
                Column("is_foreign",            BOOL),
                Column("network",               string(20)),
                Column("parent_transaction_id", string(30)),
            ),
        ),
        Table(
            schema="raw_transactions",
            name="wire_transfers",
            distribution=Distribution(style="KEY", key="account_id", sort_key="sent_at"),
            columns=(
                Column("wire_id",               string(30)),
                Column("account_id",            string(30)),
                Column("direction",             string(20)),
                Column("amount",                decimal(18,4)),
                Column("currency",              string(3)),
                Column("from_iban",             string(40)),
                Column("to_iban",               string(40)),
                Column("swift_code",            string(20)),
                Column("fee_amount",            decimal(18,4)),
                Column("originator_name",       string(120)),
                Column("beneficiary_name",      string(120)),
                Column("wire_purpose",          string(120)),
                Column("sent_at",               TIMESTAMP),
                Column("status",                string(20)),
                Column("parent_transaction_id", string(30)),
            ),
        ),
        Table(
            schema="raw_transactions",
            name="ach_transfers",
            distribution=Distribution(style="KEY", key="account_id", sort_key="originated_at"),
            columns=(
                Column("ach_id",                      string(30)),
                Column("account_id",                  string(30)),
                Column("direction",                   string(20)),
                Column("amount",                      decimal(18,4)),
                Column("ach_type",                    string(20)),
                Column("counterparty_routing",        string(20)),
                Column("counterparty_account_masked", string(40)),
                Column("counterparty_name",           string(120)),
                Column("settled_date",                DATE),
                Column("originated_at",               TIMESTAMP),
                Column("status",                      string(20)),
                Column("sec_code",                    string(20)),
                Column("return_reason_code",          string(10)),
                Column("parent_transaction_id",       string(30)),
            ),
        ),

        # raw_cards ---------------------------------------------------------
        Table(
            schema="raw_cards",
            name="card_products",
            distribution=ALL,
            columns=(
                Column("product_code",      string(30)),
                Column("product_name",      string(80)),
                Column("product_class",     string(30)),
                Column("annual_fee",        decimal(18,4)),
                Column("credit_limit_band", string(20)),
                Column("is_active",         BOOL),
            ),
        ),
        Table(
            schema="raw_cards",
            name="cards",
            distribution=AUTO,
            columns=(
                Column("card_id",            string(30)),
                Column("customer_id",        string(30)),
                Column("card_number_masked", string(30)),
                Column("product_code",       string(30)),
                Column("issued_date",        DATE),
                Column("expires_date",       DATE),
                Column("status",             string(20)),
                Column("credit_limit",       decimal(18,4)),
                Column("linked_account_id",  string(30)),
            ),
        ),
        Table(
            schema="raw_cards",
            name="card_authorizations",
            distribution=Distribution(style="KEY", key="card_id", sort_key="auth_timestamp"),
            columns=(
                Column("authorization_id", string(30)),
                Column("card_id",          string(30)),
                Column("merchant_id",      string(30)),
                Column("amount",           decimal(18,4)),
                Column("currency",         string(3)),
                Column("auth_status",      string(20)),
                Column("decline_reason",   string(120)),
                Column("auth_timestamp",   TIMESTAMP),
                Column("is_card_present",  BOOL),
                Column("ip_address",       string(45)),
            ),
        ),
        Table(
            schema="raw_cards",
            name="card_disputes",
            distribution=AUTO,
            columns=(
                Column("dispute_id",        string(30)),
                Column("authorization_id",  string(30)),
                Column("card_id",           string(30)),
                Column("dispute_reason",    string(120)),
                Column("dispute_amount",    decimal(18,4)),
                Column("opened_date",       DATE),
                Column("resolved_date",     DATE),
                Column("status",            string(40)),
                Column("chargeback_amount", decimal(18,4)),
            ),
        ),
        Table(
            schema="raw_cards",
            name="merchants",
            distribution=AUTO,
            columns=(
                Column("merchant_id",     string(30)),
                Column("merchant_name",   string(120)),
                Column("mcc_code",        string(20)),
                Column("mcc_description", string(120)),
                Column("city",            string(80)),
                Column("state",           string(20)),
                Column("country",         string(20)),
                Column("created_at",      TIMESTAMP),
            ),
        ),

        # raw_lending -------------------------------------------------------
        Table(
            schema="raw_lending",
            name="loan_products",
            distribution=ALL,
            columns=(
                Column("product_code",        string(30)),
                Column("product_name",        string(80)),
                Column("product_class",       string(30)),
                Column("default_term_months", INT),
                Column("base_apr",            decimal(10,6)),
                Column("min_amount",          decimal(18,4)),
                Column("max_amount",          decimal(18,4)),
                Column("is_secured",          BOOL),
                Column("is_active",           BOOL),
            ),
        ),
        Table(
            schema="raw_lending",
            name="loan_applications",
            distribution=AUTO,
            columns=(
                Column("application_id",      string(30)),
                Column("customer_id",         string(30)),
                Column("product_code",        string(30)),
                Column("applied_date",        DATE),
                Column("requested_amount",    decimal(18,4)),
                Column("fico_at_application", INT),
                Column("annual_income",       decimal(18,4)),
                Column("dti_ratio",           decimal(10,6)),
                Column("purpose",             string(120)),
                Column("status",              string(20)),
                Column("decision_date",       DATE),
                Column("denial_reason",       string(120)),
                Column("loan_officer_id",     string(30)),
                Column("branch_id",           string(30)),
            ),
        ),
        Table(
            schema="raw_lending",
            name="loans",
            distribution=AUTO,
            columns=(
                Column("loan_id",            string(30)),
                Column("application_id",     string(30)),
                Column("customer_id",        string(30)),
                Column("product_code",       string(30)),
                Column("principal",          decimal(18,4)),
                Column("interest_rate",      decimal(10,6)),
                Column("term_months",        INT),
                Column("origination_date",   DATE),
                Column("maturity_date",      DATE),
                Column("first_payment_date", DATE),
                Column("next_due_date",      DATE),
                Column("status",             string(20)),
                Column("balance",            decimal(18,4)),
                Column("monthly_payment",    decimal(18,4)),
                Column("branch_id",          string(30)),
                Column("days_past_due",      INT),
                Column("ifrs9_stage",        INT),
                Column("pd_12m",             decimal(10,6)),
                Column("lgd",                decimal(10,6)),
                Column("ead",                decimal(18,4)),
                Column("ecl_amount",         decimal(18,4)),
            ),
        ),
        Table(
            schema="raw_lending",
            name="loan_payments",
            distribution=Distribution(style="KEY", key="loan_id", sort_key="payment_date"),
            columns=(
                Column("payment_id",        string(30)),
                Column("loan_id",           string(30)),
                Column("payment_date",      DATE),
                Column("amount",            decimal(18,4)),
                Column("principal_portion", decimal(18,4)),
                Column("interest_portion",  decimal(18,4)),
                Column("payment_type",      string(30)),
                Column("status",            string(20)),
                Column("channel",           string(30)),
                Column("created_at",        TIMESTAMP),
            ),
        ),
        Table(
            schema="raw_lending",
            name="collateral",
            distribution=AUTO,
            columns=(
                Column("collateral_id",   string(30)),
                Column("loan_id",         string(30)),
                Column("collateral_type", string(30)),
                Column("description",     string(500)),
                Column("appraised_value", decimal(18,4)),
                Column("appraisal_date",  DATE),
                Column("ltv_ratio",       decimal(10,6)),
                Column("lien_position",   INT),
            ),
        ),

        # raw_risk ----------------------------------------------------------
        Table(
            schema="raw_risk",
            name="credit_scores",
            distribution=AUTO,
            columns=(
                Column("score_id",    string(30)),
                Column("customer_id", string(30)),
                Column("score_type",  string(30)),
                Column("score_value", INT),
                Column("score_date",  DATE),
                Column("bureau",      string(30)),
                Column("pull_reason", string(80)),
                Column("created_at",  TIMESTAMP),
            ),
        ),
        Table(
            schema="raw_risk",
            name="kyc_checks",
            distribution=AUTO,
            columns=(
                Column("kyc_id",                   string(30)),
                Column("customer_id",              string(30)),
                Column("check_type",               string(30)),
                Column("check_date",               DATE),
                Column("check_status",             string(20)),
                Column("verification_method",      string(80)),
                Column("documents_provided",       string(500)),
                Column("performed_by_employee_id", string(30)),
                Column("next_review_date",         DATE),
                Column("risk_assessment_band",     string(20)),
                Column("created_at",               TIMESTAMP),
            ),
        ),
        Table(
            schema="raw_risk",
            name="aml_alerts",
            distribution=AUTO,
            columns=(
                Column("alert_id",                string(30)),
                Column("customer_id",             string(30)),
                Column("account_id",              string(30)),
                Column("transaction_id",          string(30)),
                Column("alert_type",              string(30)),
                Column("severity",                string(20)),
                Column("status",                  string(20)),
                Column("alert_date",              DATE),
                Column("triaged_date",            DATE),
                Column("closed_date",             DATE),
                Column("assigned_to_employee_id", string(30)),
                Column("narrative",               string(500)),
                Column("scenario_code",           string(30)),
                Column("created_at",              TIMESTAMP),
            ),
        ),
        Table(
            schema="raw_risk",
            name="sanctions_screening",
            distribution=AUTO,
            columns=(
                Column("screening_id",       string(30)),
                Column("customer_id",        string(30)),
                Column("screening_date",     DATE),
                Column("list_name",          string(80)),
                Column("screen_result",      string(20)),
                Column("match_score",        decimal(10,6)),
                Column("matched_name",       string(120)),
                Column("disposition",        string(80)),
                Column("screened_by_system", string(80)),
                Column("created_at",         TIMESTAMP),
            ),
        ),
        Table(
            schema="raw_risk",
            name="suspicious_activity_reports",
            distribution=AUTO,
            columns=(
                Column("sar_id",                   string(30)),
                Column("alert_id",                 string(30)),
                Column("customer_id",              string(30)),
                Column("filing_date",              DATE),
                Column("filing_institution",       string(120)),
                Column("regulator",                string(80)),
                Column("filing_reference",         string(80)),
                Column("suspicious_activity_type", string(80)),
                Column("total_amount_involved",    decimal(18,4)),
                Column("narrative",                string(500)),
                Column("filed_by_employee_id",     string(30)),
                Column("status",                   string(20)),
                Column("created_at",               TIMESTAMP),
            ),
        ),

        # raw_wealth --------------------------------------------------------
        Table(
            schema="raw_wealth",
            name="investment_accounts",
            distribution=AUTO,
            columns=(
                Column("investment_account_id", string(30)),
                Column("customer_id",           string(30)),
                Column("account_type",          string(30)),
                Column("opened_date",           DATE),
                Column("status",                string(20)),
                Column("risk_tolerance",        string(20)),
                Column("investment_objective",  string(80)),
                Column("advisor_employee_id",   string(30)),
                Column("created_at",            TIMESTAMP),
            ),
        ),
        Table(
            schema="raw_wealth",
            name="securities",
            distribution=ALL,
            columns=(
                Column("security_id",   string(30)),
                Column("ticker",        string(20)),
                Column("isin",          string(20)),
                Column("name",          string(120)),
                Column("asset_class",   string(30)),
                Column("sector",        string(80)),
                Column("exchange",      string(20)),
                Column("currency",      string(3)),
                Column("current_price", decimal(18,4)),
                Column("price_as_of",   DATE),
            ),
        ),
        Table(
            schema="raw_wealth",
            name="holdings",
            distribution=Distribution(style="KEY", key="investment_account_id"),
            columns=(
                Column("holding_id",            string(30)),
                Column("investment_account_id", string(30)),
                Column("security_id",           string(30)),
                Column("quantity",              decimal(18,4)),
                Column("cost_basis",            decimal(18,4)),
                Column("as_of_date",            DATE),
                Column("acquired_date",         DATE),
            ),
        ),
        Table(
            schema="raw_wealth",
            name="trades",
            distribution=Distribution(style="KEY", key="investment_account_id", sort_key="trade_timestamp"),
            columns=(
                Column("trade_id",              string(30)),
                Column("investment_account_id", string(30)),
                Column("security_id",           string(30)),
                Column("side",                  string(20)),
                Column("quantity",              decimal(18,4)),
                Column("trade_price",           decimal(18,4)),
                Column("commission",            decimal(18,4)),
                Column("trade_timestamp",       TIMESTAMP),
                Column("settle_date",           DATE),
                Column("status",                string(20)),
                Column("venue",                 string(30)),
            ),
        ),

        # raw_digital -------------------------------------------------------
        Table(
            schema="raw_digital",
            name="web_sessions",
            distribution=Distribution(style="KEY", key="customer_id", sort_key="started_at"),
            columns=(
                Column("session_id",       string(30)),
                Column("customer_id",      string(30)),
                Column("started_at",       TIMESTAMP),
                Column("ended_at",         TIMESTAMP),
                Column("duration_seconds", INT),
                Column("device_type",      string(30)),
                Column("browser",          string(30)),
                Column("os",               string(30)),
                Column("ip_address",       string(45)),
                Column("user_agent",       string(500)),
                Column("referrer",         string(500)),
                Column("landing_page",     string(500)),
                Column("pages_viewed",     INT),
            ),
        ),
        Table(
            schema="raw_digital",
            name="mobile_app_events",
            distribution=Distribution(style="KEY", key="customer_id", sort_key="event_timestamp"),
            columns=(
                Column("event_id",        string(30)),
                Column("customer_id",     string(30)),
                Column("event_type",      string(30)),
                Column("event_timestamp", TIMESTAMP),
                Column("device_os",       string(30)),
                Column("device_model",    string(80)),
                Column("app_version",     string(20)),
                Column("geo_latitude",    decimal(10,6)),
                Column("geo_longitude",   decimal(10,6)),
                Column("session_id",      string(30)),
                Column("screen_name",     string(80)),
            ),
        ),
        Table(
            schema="raw_digital",
            name="login_attempts",
            distribution=Distribution(style="KEY", key="customer_id", sort_key="attempted_at"),
            columns=(
                Column("login_id",           string(30)),
                Column("customer_id",        string(30)),
                Column("attempted_at",       TIMESTAMP),
                Column("success",            BOOL),
                Column("failure_reason",     string(120)),
                Column("channel",            string(30)),
                Column("ip_address",         string(45)),
                Column("user_agent",         string(500)),
                Column("mfa_method",         string(30)),
                Column("device_fingerprint", string(120)),
            ),
        ),

        # raw_marketing -----------------------------------------------------
        Table(
            schema="raw_marketing",
            name="campaigns",
            distribution=AUTO,
            columns=(
                Column("campaign_id",       string(30)),
                Column("campaign_name",     string(120)),
                Column("channel",           string(30)),
                Column("objective",         string(120)),
                Column("start_date",        DATE),
                Column("end_date",          DATE),
                Column("budget",            decimal(18,4)),
                Column("target_segment",    string(30)),
                Column("owner_employee_id", string(30)),
                Column("status",            string(20)),
            ),
        ),
        Table(
            schema="raw_marketing",
            name="customer_segments",
            distribution=ALL,
            columns=(
                Column("segment_code", string(30)),
                Column("segment_name", string(80)),
                Column("description",  string(500)),
            ),
        ),
        Table(
            schema="raw_marketing",
            name="customer_interactions",
            distribution=Distribution(style="KEY", key="customer_id", sort_key="interaction_timestamp"),
            columns=(
                Column("interaction_id",        string(30)),
                Column("customer_id",           string(30)),
                Column("campaign_id",           string(30)),
                Column("channel",               string(30)),
                Column("topic",                 string(120)),
                Column("employee_id",           string(30)),
                Column("interaction_timestamp", TIMESTAMP),
                Column("duration_minutes",      INT),
                Column("outcome",               string(80)),
                Column("satisfaction_score",    INT),
                Column("notes",                 string(500)),
            ),
        ),
    )


@cache
def raw_schemas() -> tuple[str, ...]:
    """The distinct raw schema names, in declaration order."""
    seen: list[str] = []
    for table in all_tables():
        if table.schema not in seen:
            seen.append(table.schema)
    return tuple(seen)


@cache
def _tables_by_key() -> dict[tuple[str, str], Table]:
    return {(table.schema, table.name): table for table in all_tables()}


def find_table(schema: str, name: str) -> Table | None:
    """Return the named table, or ``None`` when it is not declared."""
    return _tables_by_key().get((schema, name))
