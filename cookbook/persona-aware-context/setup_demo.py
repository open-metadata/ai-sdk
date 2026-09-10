"""
Configure the Jaffle Shop demo database for the Persona-aware Context demo.

Run this ONCE (with an admin token) after ``cookbook/resources/demo-database``
has been ingested into OpenMetadata. It is idempotent — safe to re-run.

It sets up everything the demo shows off:

  Access — the demo users must be able to read the catalog at all
      Freshly created users inherit whatever default roles the ``Organization``
      team carries. On instances where that list is empty every non-admin call
      fails with ``403 ... operations [ViewAll] not allowed``, which looks like
      "the demo is broken" rather than "the users have no role". The script
      grants each demo user the built-in ``DataConsumer`` role so both can read
      metadata — the *difference* between them then comes from ownership and
      persona, not from one of them being locked out. Disable with
      ``--skip-roles``.

  Data — profiles, sample rows, and PII column tags
      PII masking only bites on columns tagged ``PII.Sensitive``, and it is only
      *visible* if those columns have a profile to hide. A freshly ingested
      Jaffle Shop has neither, so the script:
        * tags the sensitive columns (``email``, ``phone_number``,
          ``ssn_last_four``, ``date_of_birth``, names, address) on the customer
          tables — ``--skip-pii-tags`` to opt out;
        * profiles the demo tables straight from the running demo Postgres and
          pushes column profiles + sample rows over the REST API —
          ``--skip-profiles`` to opt out (also skipped automatically when
          ``psycopg2`` is missing or the database is unreachable);
        * executes the data-quality tests that dbt ingestion registered but never
          ran, so the ``dataQuality`` section reports an actual verdict instead of
          "0 passed, 0 failed" — plus one extra test that genuinely fails on the
          demo data. ``--skip-tests`` to opt out.

  Axis B — AI Persona Context
      Attaches a ``contextDefinition`` (rules + sections) to the
      ``ComplianceOfficer`` and ``DataEngineer`` personas so that
      ``get_persona_context`` renders a different curated document for each:
        * Compliance -> description, tags, glossary terms, articles, data quality
        * Engineer   -> schema, constraints, joins, lineage, profile
      (Both point at the same PII-tagged customer/account tables, so the
      side-by-side contrast is purely the persona lens.)

      To give the compliance-only sections real content, it also creates a
      governance GLOSSARY (terms tagged onto the PII table) and one Knowledge
      Center ARTICLE linked to that table — both surface in the Compliance
      persona document, never in the Engineer's. Disable with ``--skip-knowledge``.

      It also sets each demo user's DEFAULT PERSONA (David -> ComplianceOfficer,
      Sara -> DataEngineer) and guarantees persona membership. This is required:
      ``get_persona_context`` called with no persona name resolves the caller's
      active persona, falling back to their ``defaultPersona``. Without one set
      the server returns "No active persona is configured for this user" and the
      persona scene renders empty.

  Axis A — AI Entity Context (RBAC / PII masking)
      OpenMetadata masks ``PII.Sensitive`` column profiles and sample values
      for everyone except admins, bots, and *owners* of the asset. To make
      ``get_asset_context`` diverge between the two users, this script adds the
      Compliance Officer (David Kim) as an OWNER of the PII tables. The Data
      Engineer (Sara Johnson) stays a non-owner and therefore sees those
      columns masked. No DENY policy is needed — masking is the default.

      (Optional ``--with-pii-policy`` also creates an allow-policy/role for
      builds whose PII masking is policy-driven rather than owner-driven, e.g.
      an enterprise authorizer. It is a no-op on stock open-source builds.)

  Operating rules — how each role should answer
      Each persona also gets its OWN Knowledge Center article ("Compliance
      Operating Rules" / "Engineering Operating Rules") pulled in by a second
      persona rule over ``entityType: page``. The articles are deliberately not
      attached to any table: the persona filter is the only thing that selects
      them, so each one appears in exactly one persona's document. That is the
      easy-to-show, non-PII behavioural difference — compliance leads with
      owner/governance and cites the policy, engineering gives the dbt model
      path, the SLA, and a runnable SELECT.

      The same guidance is ALSO upserted as a private ``Preference`` memory per
      user (owned by that person, attached to the demo table), which is how you
      would model a genuinely per-*person* rule. Note that on current builds
      ``get_asset_context`` surfaces ``Private`` memories to admins only, so the
      visible per-role difference comes from the persona articles above; the
      memories are there for the Context Center UI and for builds that render
      them. Disable with ``--skip-ground-rules``.

  Access tokens
      Prints a paste-ready ``export DEMO_*_TOKEN=...`` line per demo user.
      OpenMetadata forbids an admin from minting another regular user's token
      (anti-impersonation), and bot tokens bypass PII masking — so the script sets
      a known password on each user and logs in AS them to obtain a token that
      still respects RBAC. Basic-auth instances only; on SSO it prints
      manual-generation guidance. Disable with ``--skip-tokens``.

--------------------------------------------------------------------------------
Prerequisites
--------------------------------------------------------------------------------
* The Jaffle Shop demo database ingested into OpenMetadata as a database service
  (``make demo-database`` + ``make demo-dbt`` from the repo root, then an
  OpenMetadata metadata ingestion against ``localhost:5433``). Pass
  ``--service`` if you named the service something other than "jaffle shop".
  Everything else — USERS (``david.kim`` / ``sara.johnson``), PERSONAS
  (``ComplianceOfficer`` / ``DataEngineer``), roles, PII tags, profiles,
  glossary, article, memories — is created by this script.
* An ADMIN token — persona AI-context config requires admin.
* ``pip install requests``; ``pip install psycopg2-binary`` for the profiling
  step (optional — skipped with a warning if missing).

--------------------------------------------------------------------------------
Usage
--------------------------------------------------------------------------------
    export AI_SDK_HOST=http://localhost:8585
    export AI_SDK_TOKEN=<admin-jwt>

    python setup_demo.py                 # the whole demo, end to end
    python setup_demo.py --service "jaffle shop"
    python setup_demo.py --pii-table-fqn "jaffle shop.jaffle_shop.marts_core.dim_customers"
    python setup_demo.py --with-pii-policy
    python setup_demo.py --dry-run       # print what it would do, change nothing
"""

from __future__ import annotations

import argparse
import base64
import datetime
import decimal
import importlib.util
import json
import logging
import os
import sys
from typing import Any

import requests

logger = logging.getLogger("persona_setup")

TIMEOUT = 30
PII_TAG = "PII.Sensitive"

# The Compliance Officer becomes an owner of the PII tables so they see
# unmasked PII in get_asset_context; the Data Engineer stays a non-owner.
PII_OWNER_USERNAME = "david.kim"  # David Kim -> ComplianceOfficer

# The database service holding the Jaffle Shop demo tables, as named in
# OpenMetadata. Override with --service if your ingestion used another name.
DEFAULT_SERVICE = "jaffle shop"

# The demo tables, relative to the service FQN. The FIRST one is the "hero"
# asset every scene focuses on: the glossary terms, the knowledge article, and
# the per-person operating rules all attach to it.
DEMO_TABLE_SUFFIXES: list[str] = [
    "jaffle_shop.marts_core.dim_customers",
    "jaffle_shop.staging.stg_jaffle_shop__customers",
    "jaffle_shop.raw_jaffle_shop.customers",
    "jaffle_shop.marts_core.fct_orders",
]

# Columns tagged PII.Sensitive wherever they appear in the demo tables. This is
# the actual masking lever: OpenMetadata drops the profile of a PII.Sensitive
# COLUMN for non-owners — a table-level tag alone changes nothing.
PII_COLUMN_NAMES: frozenset[str] = frozenset(
    {
        "first_name",
        "last_name",
        "full_name",
        "email",
        "customer_email",
        "phone_number",
        "date_of_birth",
        "ssn_last_four",
        "address_line_1",
        "postal_code",
    }
)

# The running demo database (cookbook/resources/demo-database). Profiles and
# sample rows are read from here and pushed to OpenMetadata, because a plain
# metadata ingestion carries neither — and with no profile there is nothing for
# PII masking to visibly remove.
DEMO_DB_DSN = "postgresql://jaffle_user:jaffle_pass@localhost:5433/jaffle_shop"

# Rows pulled per table for the sample-data payload.
SAMPLE_ROW_LIMIT = 20

# Every non-admin needs at least this role to read the catalog. Instances whose
# Organization team has no default roles hand new users nothing at all.
BASELINE_ROLE = "DataConsumer"


# ---------------------------------------------------------------------------
# Persona context definitions (Axis B)
# ---------------------------------------------------------------------------

# Both personas point at the same PII-tagged tables; only the rendered
# `sections` differ. That makes the side-by-side contrast unambiguous. In a
# real deployment you would also scope each persona to its own domain — adjust
# `queryFilter` to taste (build it in the Explore UI and copy the payload).
#
# `cacheTtlMinutes` is deliberately short. The rendered persona document is
# cached server-side, so a long TTL means catalog edits made while you are
# demoing (or a second run of this script) do not show up and the demo looks
# broken. Five minutes keeps it responsive; raise it for production.
#
# The filter is scoped to the demo SERVICE as well as the tag, so an instance
# that happens to carry PII.Sensitive elsewhere (OpenMetadata's own sample data
# does) doesn't drag unrelated tables into the persona document.


def _pii_tables_filter(service: str) -> dict[str, Any]:
    """Search filter for "PII-tagged tables inside the demo service"."""
    return {
        "bool": {
            "must": [
                {"term": {"tags.tagFQN": PII_TAG}},
                {"term": {"service.name.keyword": service}},
            ]
        }
    }


# Each persona also carries its own OPERATING RULES: a Knowledge Center article
# describing how that role should answer, pulled in by a second persona rule over
# `entityType: page`. Unlike the shared governance article these are NOT attached
# to any table — the persona's own filter is what makes each one appear in exactly
# one persona's document and nowhere else.
OPERATING_RULE_ARTICLES: dict[str, dict[str, str]] = {
    "ComplianceOfficer": {
        "name": "compliance-operating-rules",
        "displayName": "Compliance Operating Rules",
        "description": (
            "# Compliance Operating Rules\n\n"
            "When you explain any dataset:\n\n"
            "- Lead with its owner, its domain, and its governance status.\n"
            "- Name the sensitive columns and say which classification they carry.\n"
            "- Cite the governing policy (retention, consent basis) and the glossary term.\n"
            "- Point to the certified dataset rather than a raw table.\n"
            "- If a field is masked for the caller, say so explicitly instead of guessing.\n"
        ),
    },
    "DataEngineer": {
        "name": "engineering-operating-rules",
        "displayName": "Engineering Operating Rules",
        "description": (
            "# Engineering Operating Rules\n\n"
            "When you explain any dataset:\n\n"
            "- Give the dbt model path, e.g. `models/marts/core/dim_customers.sql`.\n"
            "- State the freshness SLA and the upstream models it depends on.\n"
            "- List the join keys someone will actually need.\n"
            "- Include a short, runnable `SELECT` the reader can paste.\n"
            "- Prefer the masked mart over a raw table when the query does not need PII.\n"
        ),
    },
}


def _operating_rules_filter(persona: str) -> dict[str, Any]:
    """Search filter selecting exactly one persona's operating-rules article.

    Note the explicit ``query`` wrapper. The table rules above match with a bare
    clause, but the page index does not — without the wrapper this rule silently
    matches zero articles and the section renders empty.
    """
    return {
        "query": {"term": {"name.keyword": OPERATING_RULE_ARTICLES[persona]["name"]}}
    }


_PERSONA_TEMPLATES: list[dict[str, Any]] = [
    {
        "persona": "ComplianceOfficer",
        "displayName": "Compliance Officer",
        "description": (
            "Compliance and data-governance persona: sensitive/PII data, glossary "
            "terms, and data-quality standing."
        ),
        "settings": {"enabled": True, "characterBudget": 400000, "cacheTtlMinutes": 5},
        "rules": [
            {
                "name": "Sensitive customer and account data",
                "description": "Customer/account tables carrying sensitive PII.",
                "entityType": "table",
                "queryFilter": None,  # filled in by persona_configs()
                # `articles` surfaces attached Context Center Knowledge Articles
                # (the compliance "ground rules") in this persona's document.
                # NB: for entityType "table" the server allows only ASSET_SECTIONS
                # (PersonaRepository) — `owner` is NOT one of them (metrics-only), so
                # ownership shows up via Scene 2 masking, not this persona section.
                "sections": [
                    "description",
                    "tags",
                    "glossaryTerms",
                    "articles",
                    "dataQuality",
                ],
                "maxAssets": 50,
                "alwaysInContext": True,
                "enabled": True,
            },
        ],
    },
    {
        "persona": "DataEngineer",
        "displayName": "Data Engineer",
        "description": (
            "Data-engineering persona: schema, constraints, joins, lineage, and "
            "profiling for building and fixing pipelines."
        ),
        "settings": {"enabled": True, "characterBudget": 400000, "cacheTtlMinutes": 5},
        "rules": [
            {
                "name": "Customer and account data pipelines",
                "description": "The same customer/account tables, seen as pipelines.",
                "entityType": "table",
                "queryFilter": None,  # filled in by persona_configs()
                "sections": ["schema", "constraints", "joins", "lineage", "profile"],
                "maxAssets": 50,
                "alwaysInContext": True,
                "enabled": True,
            },
        ],
    },
]


def persona_configs(service: str) -> list[dict[str, Any]]:
    """The persona templates, resolved against ``service``.

    Fills in the asset rule's ``queryFilter`` and appends the persona's own
    operating-rules page rule.
    """
    configs: list[dict[str, Any]] = []
    for template in _PERSONA_TEMPLATES:
        persona = template["persona"]
        config = dict(template)
        config["rules"] = [
            {**rule, "queryFilter": _pii_tables_filter(service)}
            for rule in template["rules"]
        ]
        config["rules"].append(
            {
                "name": f"{OPERATING_RULE_ARTICLES[persona]['displayName']} (how to answer)",
                "description": "How this role should answer questions about a dataset.",
                "entityType": "page",
                "queryFilter": _operating_rules_filter(persona),
                "sections": ["titleSummary", "fullBody"],
                "maxAssets": 5,
                "fullyRendered": True,
                "alwaysInContext": True,
                "enabled": True,
            }
        )
        configs.append(config)
    return configs


# The two demo users. Created if missing (name + email are required), then given
# a default persona so no-argument get_persona_context resolves it. Edit the
# emails if your instance restricts the principal domain.
DEMO_USERS: list[dict[str, str]] = [
    {
        "username": "david.kim",
        "display_name": "David Kim",
        "email": "david.kim@openmetadata.org",
        "persona": "ComplianceOfficer",
    },
    {
        "username": "sara.johnson",
        "display_name": "Sara Johnson",
        "email": "sara.johnson@openmetadata.org",
        "persona": "DataEngineer",
    },
]

# Env var each user's printed token should be pasted into (keyed by persona).
TOKEN_ENV_BY_PERSONA = {
    "ComplianceOfficer": "DEMO_COMPLIANCE_TOKEN",
    "DataEngineer": "DEMO_ENGINEER_TOKEN",
}

# Password the script sets on each demo user so it can log in AS them and print a
# token. Meets OpenMetadata's default policy (>=8 chars, upper/lower/digit/special).
# Override with --demo-password. Login tokens respect RBAC (unlike bot tokens).
DEMO_PASSWORD = "Persona@Demo1"

# ---------------------------------------------------------------------------
# Axis B enrichment — glossary terms + one knowledge article
# ---------------------------------------------------------------------------

# A small governance glossary. Selected terms are tagged onto the PII table so the
# ComplianceOfficer persona's `glossaryTerms` section renders them; the
# DataEngineer persona (no such section) never sees them. Same catalog, different
# lens: the persona `queryFilter` (PII.Sensitive) is the asset filter, the
# `sections` list is the field filter.
GLOSSARY_NAME = "DataGovernance"
GLOSSARY_DISPLAY = "Data Governance"
GLOSSARY_TERMS: list[dict[str, str]] = [
    {
        "name": "PersonallyIdentifiableInformation",
        "displayName": "Personally Identifiable Information",
        "description": (
            "Data that can identify a specific individual — e.g. email, phone number, "
            "date of birth, or the last four digits of a national ID."
        ),
    },
    {
        "name": "DataRetention",
        "displayName": "Data Retention",
        "description": "Policy governing how long customer data may be stored before deletion.",
    },
    {
        "name": "ConsentBasis",
        "displayName": "Consent Basis",
        "description": "The lawful basis under which personal data is processed.",
    },
]
# Which of the above get tagged onto the demo PII table.
GLOSSARY_TERMS_ON_TABLE: list[str] = [
    "PersonallyIdentifiableInformation",
    "DataRetention",
]

# One Knowledge Center article, linked to the PII table via a HAS relationship so
# the ComplianceOfficer persona's `articles` section renders it. The body lives in
# `description` — that is what the AI-context builder renders (fullContentOf).
#
# The body is deliberately LONG and split into three self-contained topics. The
# context builder inlines an attached item in full only while it stays under
# MAX_ITEM_CHARS (~1500); past that it marks the item `contentTruncated` and
# returns ONE chunk (chunked every ~380 words), picked by semantic similarity to
# the caller's `query`. Three ~400-word topics therefore land in three different
# chunks — which is what makes the `?query=` parameter visibly change the excerpt
# in explore_context_endpoint.ipynb. Shorten this and that demo stops working.
_ARTICLE_ACCESS_CONTROL = """\
## Sensitive fields, access control, and retention

`dim_customers` is the certified customer master for the Jaffle Shop warehouse and it
carries directly identifying personal data. The fields classified `PII.Sensitive` are
`first_name`, `last_name`, `full_name`, `email`, `phone_number` and `postal_code`; the
upstream staging and raw customer tables additionally carry `date_of_birth` and
`ssn_last_four`. Treat all of them as restricted. Raw values must never be pasted into
tickets, dashboards, spreadsheets, chat threads, or model prompts, and must never be
copied into a schema outside the `marts_core` and `staging` boundary.

Access is granted through ownership, not through ad-hoc requests. A person who owns the
asset in OpenMetadata sees the full column profile and sample values; everyone else sees
the same table with those columns dropped from the profile entirely. That is deliberate:
the masking happens on the server, before the payload is serialised, so an assistant that
answers on a non-owner's behalf never receives the sensitive values in the first place and
therefore cannot leak them, quote them, or summarise them. If you need access, request
ownership or a delegated grant through the data governance team rather than exporting a
copy of the table.

The retention window for identifying customer attributes is twenty-four months from the
customer's last recorded order. After that window `email`, `phone_number`, `postal_code`,
`date_of_birth` and `ssn_last_four` are nulled by the quarterly erasure job, while the
surrogate `customer_id` and the aggregate lifetime metrics are preserved so that historical
revenue reporting stays reconcilable. Deletion requests received directly from a customer
are honoured within thirty days and take precedence over the standard window.

Any analysis that leaves the warehouse — an exported CSV, a shared dashboard, a model
training set — must use the pseudonymised view rather than this table. When you report on
customer data, state the retention window you relied on and name the lawful basis for
processing. If you cannot identify a lawful basis, stop and escalate before running the
query. Contract-basis processing covers order fulfilment and support; anything marketing
related requires recorded consent, which lives on the campaign side of the model and is
not inferable from this table alone.
"""

_ARTICLE_FRESHNESS = """\
## Refresh cadence, freshness SLA, and upstream dependencies

`dim_customers` is a dbt model materialised as a table in the `marts_core` schema. The
source of record is `raw_jaffle_shop.customers`, which is loaded by the ingestion job that
lands the operational Postgres extract. From there the model passes through
`staging.stg_jaffle_shop__customers`, where types are cast, whitespace is trimmed and the
`full_name` field is derived, and through `intermediate.int_orders__enriched`, which
supplies the order-level aggregates: `total_orders`, `completed_orders`,
`cancelled_orders`, `lifetime_value`, `avg_order_value`, `first_order_date`,
`last_order_date`, `total_items_purchased` and `orders_with_coupon`. Support-ticket counts
join in from `staging.stg_support__tickets`.

The pipeline runs every night at 02:00 UTC and typically completes in under four minutes
on the demo dataset. The freshness SLA is six hours: if the newest `customer_created_at`
in the table is more than six hours behind the newest row in the raw extract, the model is
considered stale and the on-call analytics engineer is paged. Because the model is a full
rebuild rather than an incremental merge, a failed run leaves the previous successful
build in place — stale but internally consistent — which is the behaviour downstream
consumers should assume when they see an old timestamp.

Two consequences follow for anyone querying it. First, intraday changes are invisible: a
customer who registered this morning will not appear until tomorrow's build, so never use
this table for operational lookups or for anything that needs same-day accuracy. Use the
raw customer table for that, accepting that it carries no derived metrics and no
classification. Second, the derived metrics are computed as of the build time, not as of
query time, so `days_since_last_order` drifts by up to one day and should be treated as an
approximation in any cohort analysis.

Downstream, no marts currently read from `dim_customers` directly in the demo catalog, but
the analytics views `customer_ltv` and `campaign_roi` reproduce parts of the same logic
independently. If you change a metric definition here, check those two before you assume
the change is contained. Schema changes require a pull request against the dbt project and
a heads-up in the analytics channel one working day before the merge, so that dashboard
owners can adjust.
"""

_ARTICLE_DATA_QUALITY = """\
## Known data-quality issues and the dbt test suite

The model ships with a small test suite, and it does not currently pass cleanly — the
failures are known, understood and accepted rather than unnoticed, so do not treat a red
result as a reason to distrust the whole table.

The most visible issue is null contact detail. Roughly eight percent of rows have a null
`email` and about four percent have a null `phone_number`, `full_name`, `city`, `state`
or `postal_code`. These are genuine gaps in the operational source: guest checkouts and
records imported from the pre-migration system were never backfilled. A `not_null` test on
`email` is therefore deliberately configured as a warning rather than an error. When you
compute any contactability or deliverability rate, divide by the count of non-null values
rather than by the row count, and say which denominator you used, otherwise the number
will silently disagree with the marketing team's.

The second issue is segment drift. `value_segment` is derived from `lifetime_value` using
fixed thresholds that were set when the catalogue was much smaller. On the current data
the high-value tier is over-populated relative to its intended definition. The thresholds
are under review; until they change, treat `value_segment` as indicative rather than
authoritative and prefer a direct `lifetime_value` comparison when precision matters.

The third issue is a reconciliation gap. `lifetime_value` sums the net order value of
completed orders only, whereas the finance mart `fct_daily_revenue` recognises revenue at
payment capture. The two will not tie out for orders that are captured but not yet marked
complete, and the difference grows at the end of a reporting period. Neither number is
wrong; they answer different questions. Say which one you used.

Uniqueness and referential integrity are healthy: `customer_id` is unique and not null,
every `customer_id` in `fct_orders` resolves here, and `country` is single-valued in the
demo data. Test results are attached to the asset and surface in its context profile, so
check the current pass and fail counts there before quoting a figure rather than relying
on this article, which records the shape of the problems rather than today's numbers.
"""

KNOWLEDGE_ARTICLE: dict[str, str] = {
    "name": "customer-360-data-model",
    "displayName": "Customer 360 Data Model",
    "description": (
        "# Customer 360 Data Model\n\n"
        "Governance, operations, and quality notes for the certified customer master.\n\n"
        f"{_ARTICLE_ACCESS_CONTROL}\n"
        f"{_ARTICLE_FRESHNESS}\n"
        f"{_ARTICLE_DATA_QUALITY}"
    ),
}

# Articles created by earlier revisions of this script, removed on re-run so the
# demo table does not end up carrying two overlapping governance documents.
SUPERSEDED_ARTICLE_NAMES: list[str] = ["customer-pii-handling-policy"]

# Optional policy path (enterprise / policy-driven masking builds only).
PII_POLICY_NAME = "compliance-view-pii"
PII_ROLE_NAME = "compliance-pii-viewer"


# ---------------------------------------------------------------------------
# Foundational context — per-person "ground rules" (Context Center memories)
# ---------------------------------------------------------------------------

# `Preference` memories encode behavior, not facts. Each is PRIVATE and owned by
# one user, so it surfaces in *that* person's get_asset_context and no one
# else's (visibility is owner-based). Attached to the demo PII table.
GROUND_RULES: list[dict[str, str]] = [
    {
        "username": "david.kim",  # ComplianceOfficer
        "name": "compliance-operating-rule",
        "title": "Operating rule — Compliance",
        "question": "How should I answer questions about a dataset?",
        "answer": (
            "When explaining any dataset, always:\n"
            "- Lead with its data owner, domain, and governance status.\n"
            "- Cite the governing policy (e.g. the Data Retention policy) and the "
            "relevant glossary term.\n"
            "- Recommend the certified / approved dataset rather than a raw table."
        ),
    },
    {
        "username": "sara.johnson",  # DataEngineer
        "name": "engineering-operating-rule",
        "title": "Operating rule — Data Engineering",
        "question": "How should I answer questions about a dataset?",
        "answer": (
            "When explaining any dataset, always:\n"
            "- Give the dbt model path (e.g. `models/marts/core/dim_customers.sql`).\n"
            "- State the freshness SLA and the frequent join keys.\n"
            "- Include a short, runnable `SELECT` the reader can paste."
        ),
    },
]

# Memories from earlier PII-framed runs, superseded by the operating rules above.
# Removed on re-run so they do not surface alongside the new ones.
SUPERSEDED_MEMORY_NAMES: list[str] = [
    "compliance-pii-ground-rules",
    "engineering-data-handling-ground-rules",
]


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _api_base(host: str) -> str:
    host = host.rstrip("/")
    return host if host.endswith("/api") else f"{host}/api"


class OMClient:
    """Thin OpenMetadata REST helper over ``requests`` (admin token)."""

    def __init__(self, host: str, token: str, dry_run: bool) -> None:
        self.base = _api_base(host)
        self.dry_run = dry_run
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def close(self) -> None:
        self._session.close()

    def get(self, path: str, params: dict[str, Any] | None = None) -> requests.Response:
        return self._session.get(f"{self.base}{path}", params=params, timeout=TIMEOUT)

    def _mutate(
        self, method: str, path: str, payload: Any, content_type: str | None
    ) -> None:
        if self.dry_run:
            logger.info(
                "[dry-run] %s %s\n%s", method, path, json.dumps(payload, indent=2)
            )
            return
        headers = {"Content-Type": content_type} if content_type else None
        response = self._session.request(
            method, f"{self.base}{path}", json=payload, headers=headers, timeout=TIMEOUT
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"{method} {path} -> {response.status_code}: {response.text}"
            )

    def put(self, path: str, payload: Any) -> None:
        self._mutate("PUT", path, payload, None)

    def post(self, path: str, payload: Any) -> None:
        self._mutate("POST", path, payload, None)

    def json_patch(self, path: str, patch: list[dict[str, Any]]) -> None:
        self._mutate("PATCH", path, patch, "application/json-patch+json")

    def send(self, method: str, path: str, payload: Any) -> requests.Response | None:
        """Like the mutating helpers but RETURNS the response and never raises.

        For best-effort calls (login, admin password reset) where a 4xx is an
        expected outcome (e.g. an SSO instance) to be handled, not aborted on.
        Returns None under --dry-run.
        """
        if self.dry_run:
            logger.info("[dry-run] %s %s", method, path)
            return None
        return self._session.request(
            method, f"{self.base}{path}", json=payload, timeout=TIMEOUT
        )


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------


def get_id_by_name(client: OMClient, resource: str, name: str) -> str | None:
    """Resolve an entity UUID by name (personas, users, ...)."""
    response = client.get(f"/v1/{resource}/name/{name}")
    if response.status_code == 200:
        return response.json().get("id")
    logger.warning("%s '%s' not found (HTTP %s)", resource, name, response.status_code)
    return None


def get_entity(client: OMClient, resource: str, name: str) -> dict[str, Any] | None:
    """Fetch a full entity by name, or None (quiet — no warning on 404)."""
    response = client.get(f"/v1/{resource}/name/{name}")
    return response.json() if response.status_code == 200 else None


def get_entity_fields(
    client: OMClient, resource: str, name: str, fields: str
) -> dict[str, Any] | None:
    """Fetch an entity by name with extra ``fields`` requested (e.g. relationships), or None."""
    response = client.get(f"/v1/{resource}/name/{name}", params={"fields": fields})
    return response.json() if response.status_code == 200 else None


def _ref(entity: dict[str, Any], entity_type: str) -> dict[str, Any]:
    """Build an EntityReference from a fetched entity."""
    return {
        "id": entity["id"],
        "type": entity_type,
        "name": entity.get("name"),
        "fullyQualifiedName": entity.get("fullyQualifiedName", entity.get("name")),
    }


def demo_tables(client: OMClient, service: str) -> list[str]:
    """The demo tables that actually exist in this instance, hero table first."""
    present: list[str] = []
    for suffix in DEMO_TABLE_SUFFIXES:
        fqn = f"{service}.{suffix}"
        if get_entity(client, "tables", fqn) is None:
            logger.warning("  table '%s' not found — skipping it", fqn)
            continue
        present.append(fqn)
    return present


def discover_pii_tables(client: OMClient, service: str, limit: int) -> list[str]:
    """Find tables in ``service`` carrying the PII.Sensitive tag, via the search API."""
    query_filter = json.dumps({"query": _pii_tables_filter(service)})
    response = client.get(
        "/v1/search/query",
        params={
            "q": "*",
            "index": "table_search_index",
            "query_filter": query_filter,
            "size": limit,
        },
    )
    if response.status_code != 200:
        logger.warning(
            "PII table search failed (HTTP %s); pass --pii-table-fqn",
            response.status_code,
        )
        return []
    hits = response.json().get("hits", {}).get("hits", [])
    fqns = [
        hit["_source"]["fullyQualifiedName"]
        for hit in hits
        if isinstance(hit, dict) and "fullyQualifiedName" in hit.get("_source", {})
    ]
    return fqns


# ---------------------------------------------------------------------------
# Demo users — create them, and make sure they can read anything at all
# ---------------------------------------------------------------------------


def ensure_users_exist(client: OMClient) -> None:
    """Create each demo user if missing (idempotent).

    This makes the demo self-contained — no ingest is expected to seed
    ``david.kim`` / ``sara.johnson``. Only ``name`` + ``email`` are required.
    It does NOT generate access tokens; that happens in ``print_user_tokens``.
    """
    for entry in DEMO_USERS:
        if get_entity(client, "users", entry["username"]) is not None:
            logger.info("  user '%s' already exists — skipping", entry["username"])
            continue
        logger.info("  creating user '%s' <%s>", entry["username"], entry["email"])
        client.post(
            "/v1/users",
            {
                "name": entry["username"],
                "displayName": entry["display_name"],
                "email": entry["email"],
            },
        )


def grant_baseline_role(client: OMClient) -> None:
    """Give both demo users the ``DataConsumer`` role so they can read the catalog.

    A new user's effective permissions come from the default roles of the teams
    they join — normally ``Organization`` carries ``DataConsumer``. On instances
    where that list has been emptied, a brand-new user can call nothing at all
    and every scene fails with ``403 ... operations [ViewAll] not allowed``. The
    demo's point is that David and Sara see *different* things, not that one of
    them is locked out, so both get the same baseline role here and diverge only
    through ownership and persona.
    """
    role = get_entity(client, "roles", BASELINE_ROLE)
    if role is None:
        logger.warning("  role '%s' not found — skipping baseline grant", BASELINE_ROLE)
        return
    role_ref = _ref(role, "role")
    for entry in DEMO_USERS:
        username = entry["username"]
        user = get_entity_fields(client, "users", username, "roles")
        if user is None:
            logger.warning("  user '%s' not found — skipping baseline role", username)
            continue
        roles = user.get("roles") or []
        if any(existing.get("id") == role_ref["id"] for existing in roles):
            logger.info("  %s already has '%s' — skipping", username, BASELINE_ROLE)
            continue
        patch = (
            [{"op": "add", "path": "/roles/-", "value": role_ref}]
            if roles
            else [{"op": "add", "path": "/roles", "value": [role_ref]}]
        )
        logger.info("  granting '%s' to %s", BASELINE_ROLE, username)
        client.json_patch(f"/v1/users/{user['id']}", patch)


# ---------------------------------------------------------------------------
# Data — PII column tags (the masking lever's precondition)
# ---------------------------------------------------------------------------


def tag_pii_columns(client: OMClient, table_fqns: list[str]) -> None:
    """Tag the sensitive columns of each demo table with ``PII.Sensitive``.

    Masking is per COLUMN: OpenMetadata removes the profile of a column tagged
    ``PII.Sensitive`` for anyone who is not an admin, a bot, or an owner of the
    asset. A table-level tag is documentation — it masks nothing. Without this
    step Scene 2 renders two identical documents.
    """
    for fqn in table_fqns:
        table = get_entity_fields(client, "tables", fqn, "columns,tags")
        if table is None:
            logger.warning("  table '%s' not found — skipping PII tags", fqn)
            continue
        label = {
            "tagFQN": PII_TAG,
            "source": "Classification",
            "labelType": "Manual",
            "state": "Confirmed",
        }
        patch: list[dict[str, Any]] = []
        tagged: list[str] = []
        # The table-level tag masks nothing; it is documentation, and it keeps the
        # asset's `tags` field from reading as empty in the Context Profile.
        table_tags = table.get("tags") or []
        if not any(tag.get("tagFQN") == PII_TAG for tag in table_tags):
            patch.append(
                {"op": "add", "path": "/tags/-", "value": label}
                if table_tags
                else {"op": "add", "path": "/tags", "value": [label]}
            )
            tagged.append("(table)")
        for index, column in enumerate(table.get("columns") or []):
            if column.get("name") not in PII_COLUMN_NAMES:
                continue
            existing = column.get("tags") or []
            if any(tag.get("tagFQN") == PII_TAG for tag in existing):
                continue
            path = f"/columns/{index}/tags"
            patch.append(
                {"op": "add", "path": f"{path}/-", "value": label}
                if existing
                else {"op": "add", "path": path, "value": [label]}
            )
            tagged.append(column["name"])
        if not patch:
            logger.info("  '%s' already tagged — skipping", fqn)
            continue
        logger.info("  tagging '%s': %s", fqn, ", ".join(tagged))
        client.json_patch(f"/v1/tables/{table['id']}", patch)


# ---------------------------------------------------------------------------
# Data — column profiles + sample rows, read from the demo database
# ---------------------------------------------------------------------------

_NUMERIC_TYPES = frozenset(
    {"BIGINT", "DECIMAL", "DOUBLE", "FLOAT", "INT", "NUMERIC", "SMALLINT", "TINYINT"}
)


def _json_safe(value: object) -> object:
    """Coerce a psycopg2 value into something ``json.dumps`` accepts."""
    if isinstance(value, (datetime.date, datetime.datetime, datetime.time)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    return value


def _split_fqn(fqn: str) -> tuple[str, str] | None:
    """Return ``(schema, table)`` for a table FQN, or None if it is malformed."""
    parts = fqn.split(".")
    if len(parts) < 4:
        logger.warning(
            "  cannot parse schema/table out of '%s' — skipping profile", fqn
        )
        return None
    return parts[-2], parts[-1]


def _column_profile(
    cursor: Any, schema: str, table: str, column: dict[str, Any]
) -> dict[str, Any]:
    """Profile one column with a handful of aggregates."""
    name = column["name"]
    qualified = f'"{schema}"."{table}"'
    cursor.execute(
        f'SELECT count(*), count("{name}"), count(DISTINCT "{name}") FROM {qualified}'  # noqa: S608
    )
    total, non_null, distinct = cursor.fetchone()
    profile: dict[str, Any] = {
        "name": name,
        "valuesCount": float(total),
        "nullCount": float(total - non_null),
        "nullProportion": float(total - non_null) / total if total else 0.0,
        "distinctCount": float(distinct),
        "uniqueProportion": float(distinct) / total if total else 0.0,
        "valuesPercentage": float(non_null) / total if total else 0.0,
    }
    if column.get("dataType") in _NUMERIC_TYPES:
        cursor.execute(
            f'SELECT min("{name}"), max("{name}"), avg("{name}") FROM {qualified}'  # noqa: S608
        )
    else:
        cursor.execute(
            f'SELECT min(length("{name}"::text)), max(length("{name}"::text)), '  # noqa: S608
            f'avg(length("{name}"::text)) FROM {qualified}'
        )
    low, high, mean = cursor.fetchone()
    if low is None:
        return profile
    if column.get("dataType") in _NUMERIC_TYPES:
        profile.update(min=float(low), max=float(high), mean=float(mean))
    else:
        profile.update(minLength=float(low), maxLength=float(high), mean=float(mean))
    return profile


def _profile_one_table(client: OMClient, cursor: Any, fqn: str, timestamp: int) -> bool:
    """Push sample rows + a column profile for one table. True if anything landed."""
    table = get_entity_fields(client, "tables", fqn, "columns")
    if table is None:
        logger.warning("  table '%s' not found — skipping profile", fqn)
        return False
    location = _split_fqn(fqn)
    if location is None:
        return False
    schema, name = location
    columns = table.get("columns") or []
    column_names = [column["name"] for column in columns]
    quoted = ", ".join(f'"{column}"' for column in column_names)
    cursor.execute(
        f'SELECT {quoted} FROM "{schema}"."{name}" LIMIT {SAMPLE_ROW_LIMIT}'  # noqa: S608
    )
    rows = [[_json_safe(value) for value in row] for row in cursor.fetchall()]
    client.put(
        f"/v1/tables/{table['id']}/sampleData", {"columns": column_names, "rows": rows}
    )

    cursor.execute(f'SELECT count(*) FROM "{schema}"."{name}"')  # noqa: S608
    (row_count,) = cursor.fetchone()
    client.put(
        f"/v1/tables/{table['id']}/tableProfile",
        {
            "tableProfile": {
                "timestamp": timestamp,
                "rowCount": float(row_count),
                "columnCount": float(len(columns)),
            },
            "columnProfile": [
                dict(_column_profile(cursor, schema, name, column), timestamp=timestamp)
                for column in columns
            ],
        },
    )
    logger.info("  profiled '%s' (%d rows, %d columns)", fqn, row_count, len(columns))
    return True


def seed_profiles_and_samples(
    client: OMClient, table_fqns: list[str], dsn: str
) -> None:
    """Read the demo database and push column profiles + sample rows to OpenMetadata.

    A metadata-only ingestion gives you schemas and lineage but no profile and no
    sample values — and PII masking that has nothing to hide is invisible. Rather
    than shipping invented numbers, this profiles the live demo Postgres
    (``cookbook/resources/demo-database``, port 5433) and uploads the result.

    Skipped, loudly but harmlessly, when ``psycopg2`` is not installed or the
    database is not reachable: everything else in the demo still works, Scene 2
    just has less to show.
    """
    if client.dry_run:
        logger.info("[dry-run] would profile %d table(s) from %s", len(table_fqns), dsn)
        return
    if importlib.util.find_spec("psycopg2") is None:
        logger.warning(
            "  psycopg2 not installed — skipping profiles "
            "(pip install psycopg2-binary, or pass --skip-profiles)"
        )
        return

    import psycopg2

    try:
        connection = psycopg2.connect(dsn, connect_timeout=TIMEOUT)
    except psycopg2.Error as error:
        logger.warning(
            "  demo database unreachable at %s (%s) — skipping profiles. "
            "Start it with `make demo-database`.",
            dsn,
            str(error).strip(),
        )
        return

    timestamp = int(datetime.datetime.now(tz=datetime.UTC).timestamp() * 1000)
    profiled = 0
    try:
        with connection, connection.cursor() as cursor:
            for fqn in table_fqns:
                profiled += _profile_one_table(client, cursor, fqn, timestamp)
    finally:
        connection.close()
    logger.info("  %d table(s) profiled", profiled)


# ---------------------------------------------------------------------------
# Data — execute the ingested data-quality tests
# ---------------------------------------------------------------------------

# One extra test the dbt project does not define, added because it genuinely
# FAILS on the demo data (guest checkouts leave `email` null). A data-quality
# section where everything is green says nothing; one real failure is what makes
# the compliance persona's `dataQuality` section worth reading.
EXTRA_TEST_CASES: list[dict[str, str]] = [
    {
        "table_suffix": "jaffle_shop.marts_core.dim_customers",
        "column": "email",
        "name": "not_null_dim_customers_email",
        "displayName": "dim_customers.email is not null",
        "description": "Contact-detail completeness: every customer should have an email.",
        "testDefinition": "columnValuesToBeNotNull",
    },
]

# dbt ingestion registers its own short-named test definitions; a native
# OpenMetadata test suite uses the long names. Both mean the same thing here.
_NOT_NULL_DEFINITIONS = frozenset({"not_null", "columnValuesToBeNotNull"})
_UNIQUE_DEFINITIONS = frozenset({"unique", "columnValuesToBeUnique"})
_ACCEPTED_VALUES_DEFINITIONS = frozenset({"accepted_values", "columnValuesToBeInSet"})


def ensure_extra_test_cases(client: OMClient, service: str) -> None:
    """Create the demo's own test cases if the ingest didn't (idempotent)."""
    for spec in EXTRA_TEST_CASES:
        table_fqn = f"{service}.{spec['table_suffix']}"
        case_fqn = f"{table_fqn}.{spec['column']}.{spec['name']}"
        if get_entity(client, "dataQuality/testCases", case_fqn) is not None:
            logger.info("  test case '%s' already present — skipping", spec["name"])
            continue
        if get_entity(client, "tables", table_fqn) is None:
            logger.warning("  table '%s' not found — skipping test case", table_fqn)
            continue
        logger.info("  creating test case '%s'", spec["name"])
        client.post(
            "/v1/dataQuality/testCases",
            {
                "name": spec["name"],
                "displayName": spec["displayName"],
                "description": spec["description"],
                "entityLink": f"<#E::table::{table_fqn}::columns::{spec['column']}>",
                "testDefinition": spec["testDefinition"],
                "parameterValues": [],
            },
        )


def _test_case_column(entity_link: str) -> str | None:
    """Pull the column name out of an ``<#E::table::fqn::columns::name>`` link."""
    marker = "::columns::"
    if marker not in entity_link:
        return None
    return entity_link.split(marker, 1)[1].rstrip(">")


def _evaluate_test(
    cursor: Any,
    schema: str,
    table: str,
    column: str,
    definition: str,
    parameters: list[Any],
) -> tuple[str, str] | None:
    """Run one test against the demo database. Returns ``(status, message)``."""
    qualified = f'"{schema}"."{table}"'
    if definition in _NOT_NULL_DEFINITIONS:
        cursor.execute(f'SELECT count(*) FROM {qualified} WHERE "{column}" IS NULL')  # noqa: S608
        (bad,) = cursor.fetchone()
        return (
            "Success" if bad == 0 else "Failed",
            f"Found {bad} null value(s) in {column}",
        )
    if definition in _UNIQUE_DEFINITIONS:
        cursor.execute(
            f'SELECT count(*) FROM (SELECT "{column}" FROM {qualified} '  # noqa: S608
            f'WHERE "{column}" IS NOT NULL GROUP BY "{column}" HAVING count(*) > 1) AS duplicates'
        )
        (bad,) = cursor.fetchone()
        return (
            "Success" if bad == 0 else "Failed",
            f"Found {bad} duplicate value(s) in {column}",
        )
    if definition in _ACCEPTED_VALUES_DEFINITIONS:
        raw = next((str(item.get("value", "")) for item in parameters), "")
        allowed = [
            value.strip().strip("'\"[] ") for value in raw.split(",") if value.strip()
        ]
        if not allowed:
            return None
        cursor.execute(
            f'SELECT count(*) FROM {qualified} WHERE "{column}" IS NOT NULL '  # noqa: S608
            f'AND "{column}"::text <> ALL(%s)',
            (allowed,),
        )
        (bad,) = cursor.fetchone()
        return (
            "Success" if bad == 0 else "Failed",
            f"Found {bad} unexpected value(s) in {column}",
        )
    return None


def _run_tests_for_table(
    client: OMClient, cursor: Any, fqn: str, timestamp: int
) -> tuple[int, int]:
    """Execute every test case attached to one table. Returns ``(passed, failed)``."""
    suite = get_entity_fields(
        client, "dataQuality/testSuites", f"{fqn}.testSuite", "tests"
    )
    if suite is None:
        logger.info("  '%s' has no test suite — skipping", fqn)
        return (0, 0)
    location = _split_fqn(fqn)
    if location is None:
        return (0, 0)
    schema, table = location
    passed = failed = 0
    for entry in suite.get("tests") or []:
        case = get_entity_fields(
            client,
            "dataQuality/testCases",
            entry["fullyQualifiedName"],
            "testDefinition",
        )
        if case is None:
            continue
        column = _test_case_column(case.get("entityLink") or "")
        definition = (case.get("testDefinition") or {}).get("name")
        if column is None or definition is None:
            continue
        outcome = _evaluate_test(
            cursor, schema, table, column, definition, case.get("parameterValues") or []
        )
        if outcome is None:
            logger.info(
                "    %s: '%s' not executable here — skipping", case["name"], definition
            )
            continue
        status, message = outcome
        client.post(
            f"/v1/dataQuality/testCases/testCaseResults/{entry['fullyQualifiedName']}",
            {"timestamp": timestamp, "testCaseStatus": status, "result": message},
        )
        logger.info("    %-8s %s — %s", status, case["name"], message)
        passed += status == "Success"
        failed += status == "Failed"
    return (passed, failed)


def run_data_quality_tests(client: OMClient, table_fqns: list[str], dsn: str) -> None:
    """Execute the ingested dbt tests against the demo database and record results.

    dbt ingestion registers the test *definitions* but never their results, so
    every asset reports "0 passed, 0 failed" — which the context builder
    correctly refuses to call healthy. Running them here turns the compliance
    persona's `dataQuality` section into something with an actual verdict.
    """
    if client.dry_run:
        logger.info(
            "[dry-run] would execute the test suites of %d table(s)", len(table_fqns)
        )
        return
    if importlib.util.find_spec("psycopg2") is None:
        logger.warning("  psycopg2 not installed — skipping test execution")
        return

    import psycopg2

    try:
        connection = psycopg2.connect(dsn, connect_timeout=TIMEOUT)
    except psycopg2.Error as error:
        logger.warning(
            "  demo database unreachable at %s (%s) — skipping test execution",
            dsn,
            str(error).strip(),
        )
        return

    timestamp = int(datetime.datetime.now(tz=datetime.UTC).timestamp() * 1000)
    passed = failed = 0
    try:
        with connection, connection.cursor() as cursor:
            for fqn in table_fqns:
                table_passed, table_failed = _run_tests_for_table(
                    client, cursor, fqn, timestamp
                )
                passed += table_passed
                failed += table_failed
    finally:
        connection.close()
    logger.info("  %d passed, %d failed", passed, failed)


# ---------------------------------------------------------------------------
# Axis B — persona context definitions
# ---------------------------------------------------------------------------


def existing_rule_ids(client: OMClient, persona_id: str) -> dict[str, str]:
    """Map rule name -> rule id for the rules already on this persona."""
    response = client.get(f"/v1/personas/{persona_id}/aiContext")
    if response.status_code != 200:
        return {}
    rules = response.json().get("rules", []) or []
    return {
        rule["name"]: rule["id"]
        for rule in rules
        if isinstance(rule, dict) and "name" in rule and "id" in rule
    }


def _persona_user_ids(client: OMClient, persona_name: str) -> list[str]:
    """Resolve the UUIDs of the demo users that belong to this persona."""
    user_ids: list[str] = []
    for entry in DEMO_USERS:
        if entry["persona"] != persona_name:
            continue
        user_id = get_id_by_name(client, "users", entry["username"])
        if user_id is None:
            logger.warning(
                "  user '%s' not found — persona '%s' created without them",
                entry["username"],
                persona_name,
            )
            continue
        user_ids.append(user_id)
    return user_ids


def create_persona(client: OMClient, config: dict[str, Any]) -> str | None:
    """Create (or update) the teams Persona so the demo does not depend on the ingest.

    PUT ``/v1/personas`` is create-or-update, so this is idempotent. Returns the
    persona UUID (None only under --dry-run, where nothing is written).
    """
    name = config["persona"]
    logger.info("Persona '%s' not found — creating it", name)
    client.put(
        "/v1/personas",
        {
            "name": name,
            "displayName": config.get("displayName", name),
            "description": config.get("description", ""),
            "users": _persona_user_ids(client, name),
        },
    )
    return get_id_by_name(client, "personas", name)


def configure_persona(client: OMClient, config: dict[str, Any]) -> None:
    name = config["persona"]
    persona_id = get_id_by_name(client, "personas", name)
    if persona_id is None:
        persona_id = create_persona(client, config)
    if persona_id is None:
        logger.warning(
            "Persona '%s' not resolvable (dry-run?) — skipping AI context.", name
        )
        return

    logger.info("Persona '%s' (%s): enabling AI context", name, persona_id)
    client.put(f"/v1/personas/{persona_id}/aiContext", config["settings"])

    # Rules are replaced rather than skipped when they already exist, so editing
    # a filter or a section list in this file and re-running actually takes
    # effect. Skipping would leave a stale rule in place and look like the edit
    # did nothing.
    present = existing_rule_ids(client, persona_id)
    for rule in config["rules"]:
        verb = "adding"
        if rule["name"] in present:
            verb = "replacing"
            client.send(
                "DELETE",
                f"/v1/personas/{persona_id}/aiContext/rules/{present[rule['name']]}",
                None,
            )
        # queryFilter must be a JSON-ENCODED STRING, not a nested object.
        body = dict(rule)
        body["queryFilter"] = json.dumps(rule["queryFilter"])
        logger.info(
            "  %s rule '%s' (sections: %s)",
            verb,
            rule["name"],
            ", ".join(rule["sections"]),
        )
        client.post(f"/v1/personas/{persona_id}/aiContext/rules", body)


# ---------------------------------------------------------------------------
# Axis B — default persona per user (makes get_persona_context resolve)
# ---------------------------------------------------------------------------


def _ensure_persona_membership(
    client: OMClient, user: dict[str, Any], persona_ref: dict[str, Any], username: str
) -> None:
    """Add the user to the persona if not already a member (the server's authorize() requires it)."""
    personas = user.get("personas") or []
    if any(member.get("id") == persona_ref["id"] for member in personas):
        return
    patch = (
        [{"op": "add", "path": "/personas/-", "value": persona_ref}]
        if personas
        else [{"op": "add", "path": "/personas", "value": [persona_ref]}]
    )
    logger.info("  adding %s to persona '%s'", username, persona_ref.get("name"))
    client.json_patch(f"/v1/users/{user['id']}", patch)


def _ensure_default_persona(
    client: OMClient, user: dict[str, Any], persona_ref: dict[str, Any], username: str
) -> None:
    """Set the user's defaultPersona so no-argument get_persona_context resolves it."""
    current = user.get("defaultPersona") or {}
    if current.get("id") == persona_ref["id"]:
        logger.info(
            "  %s default persona already '%s' — skipping",
            username,
            persona_ref.get("name"),
        )
        return
    logger.info(
        "  setting %s default persona -> '%s'", username, persona_ref.get("name")
    )
    client.json_patch(
        f"/v1/users/{user['id']}",
        [{"op": "add", "path": "/defaultPersona", "value": persona_ref}],
    )


def assign_default_personas(client: OMClient) -> None:
    """Give each demo user a default persona (and membership) for the persona scene.

    ``get_persona_context`` called with no persona name resolves the caller's
    active persona, falling back to their ``defaultPersona``. With neither set it
    raises "No active persona is configured for this user" and Scene 1 renders
    empty — so this is what actually lights up the persona showcase.
    """
    for entry in DEMO_USERS:
        username = entry["username"]
        user = get_entity_fields(client, "users", username, "personas,defaultPersona")
        if user is None:
            logger.warning("  user '%s' not found — skipping default persona", username)
            continue
        persona = get_entity(client, "personas", entry["persona"])
        if persona is None:
            logger.warning(
                "  persona '%s' not found — skipping for %s", entry["persona"], username
            )
            continue
        persona_ref = _ref(persona, "persona")
        _ensure_persona_membership(client, user, persona_ref, username)
        _ensure_default_persona(client, user, persona_ref, username)


# ---------------------------------------------------------------------------
# Axis A — ownership (the PII-masking lever)
# ---------------------------------------------------------------------------


def add_table_owner(client: OMClient, fqn: str, user_id: str, username: str) -> None:
    response = client.get(f"/v1/tables/name/{fqn}", params={"fields": "owners"})
    if response.status_code != 200:
        logger.warning(
            "  table '%s' not found (HTTP %s) — skipping", fqn, response.status_code
        )
        return
    owners = response.json().get("owners") or []
    if any(owner.get("id") == user_id for owner in owners):
        logger.info("  %s already owns '%s' — skipping", username, fqn)
        return
    owner_ref = {"id": user_id, "type": "user"}
    patch = (
        [{"op": "add", "path": "/owners/-", "value": owner_ref}]
        if owners
        else [{"op": "add", "path": "/owners", "value": [owner_ref]}]
    )
    logger.info("  adding %s as owner of '%s'", username, fqn)
    client.json_patch(f"/v1/tables/name/{fqn}", patch)


def assign_pii_ownership(client: OMClient, table_fqns: list[str]) -> None:
    user_id = get_id_by_name(client, "users", PII_OWNER_USERNAME)
    if user_id is None:
        logger.error(
            "Cannot assign ownership — user '%s' not found.", PII_OWNER_USERNAME
        )
        return
    logger.info(
        "Assigning %s as owner of %d PII table(s)", PII_OWNER_USERNAME, len(table_fqns)
    )
    for fqn in table_fqns:
        add_table_owner(client, fqn, user_id, PII_OWNER_USERNAME)


# ---------------------------------------------------------------------------
# Optional policy path (enterprise / policy-driven masking)
# ---------------------------------------------------------------------------


def create_pii_policy_and_role(client: OMClient) -> None:
    logger.info(
        "Creating PII allow-policy '%s' + role '%s' (enterprise builds)",
        PII_POLICY_NAME,
        PII_ROLE_NAME,
    )
    client.put(
        "/v1/policies",
        {
            "name": PII_POLICY_NAME,
            "displayName": "Compliance view PII assets",
            "description": "Allow viewing PII-tagged table data for compliance.",
            "rules": [
                {
                    "name": "allow-view-pii-tables",
                    "effect": "allow",
                    "resources": ["table"],
                    "operations": [
                        "ViewAll",
                        "ViewDataProfile",
                        "ViewSampleData",
                        "ViewTests",
                    ],
                    "condition": f"matchAnyTag('{PII_TAG}')",
                }
            ],
        },
    )
    client.put(
        "/v1/roles",
        {
            "name": PII_ROLE_NAME,
            "displayName": "Compliance PII Viewer",
            "policies": [PII_POLICY_NAME],
        },
    )
    role_id = get_id_by_name(client, "roles", PII_ROLE_NAME)
    user_id = get_id_by_name(client, "users", PII_OWNER_USERNAME)
    if role_id and user_id:
        logger.info("Assigning role '%s' to %s", PII_ROLE_NAME, PII_OWNER_USERNAME)
        client.json_patch(
            f"/v1/users/{user_id}",
            [
                {
                    "op": "add",
                    "path": "/roles/0",
                    "value": {"id": role_id, "type": "role"},
                }
            ],
        )


# ---------------------------------------------------------------------------
# Foundational context — create the per-person ground-rules memories
# ---------------------------------------------------------------------------


def _delete_superseded_memories(client: OMClient) -> None:
    """Remove PII-framed ground-rule memories from earlier runs (best-effort)."""
    for name in SUPERSEDED_MEMORY_NAMES:
        memory = get_entity(client, "contextCenter/memories", name)
        if memory is None:
            continue
        logger.info("  removing superseded memory '%s'", name)
        client.send(
            "DELETE", f"/v1/contextCenter/memories/{memory['id']}?hardDelete=true", None
        )


def create_ground_rules(client: OMClient, table_fqns: list[str]) -> None:
    """Upsert a private, per-user Preference memory (operating rule) on the demo table.

    Each memory is owner-scoped (visibility Private), so a caller's get_asset_context
    carries only their own rule — David the compliance rule, Sara the engineering
    rule. That per-person operating rule is what makes the agent answer the same
    question differently. Uses PUT (create-or-update) so re-runs refresh the content.
    """
    _delete_superseded_memories(client)

    primary_entity: dict[str, Any] | None = None
    if table_fqns:
        table = get_entity(client, "tables", table_fqns[0])
        if table is not None:
            primary_entity = _ref(table, "table")
            logger.info("Operating-rule memories will attach to '%s'", table_fqns[0])

    for rule in GROUND_RULES:
        user = get_entity(client, "users", rule["username"])
        if user is None:
            logger.warning(
                "  user '%s' not found — skipping operating rule", rule["username"]
            )
            continue
        payload: dict[str, Any] = {
            "name": rule["name"],
            "title": rule["title"],
            "question": rule["question"],
            "answer": rule["answer"],
            "memoryType": "Preference",
            "memoryScope": "EntityScoped",
            "shareConfig": {"visibility": "Private"},
            "owners": [_ref(user, "user")],
        }
        if primary_entity is not None:
            payload["primaryEntity"] = primary_entity
        logger.info(
            "  upserting operating-rule memory '%s' for %s",
            rule["name"],
            rule["username"],
        )
        client.put("/v1/contextCenter/memories", payload)


# ---------------------------------------------------------------------------
# Axis B enrichment — glossary terms + knowledge article
# ---------------------------------------------------------------------------


def ensure_glossary(client: OMClient) -> None:
    """Create the governance glossary and its terms if missing (idempotent)."""
    if get_entity(client, "glossaries", GLOSSARY_NAME) is None:
        logger.info("  creating glossary '%s'", GLOSSARY_NAME)
        client.put(
            "/v1/glossaries",
            {
                "name": GLOSSARY_NAME,
                "displayName": GLOSSARY_DISPLAY,
                "description": "Governance glossary for the persona-aware-context demo.",
            },
        )
    for term in GLOSSARY_TERMS:
        term_fqn = f"{GLOSSARY_NAME}.{term['name']}"
        if get_entity(client, "glossaryTerms", term_fqn) is not None:
            logger.info("  glossary term '%s' already present — skipping", term_fqn)
            continue
        logger.info("  creating glossary term '%s'", term["name"])
        client.put(
            "/v1/glossaryTerms",
            {
                "glossary": GLOSSARY_NAME,
                "name": term["name"],
                "displayName": term["displayName"],
                "description": term["description"],
            },
        )


def assign_glossary_terms_to_table(client: OMClient, table_fqn: str) -> None:
    """Tag the PII table with glossary terms so the compliance persona surfaces them."""
    table = get_entity_fields(client, "tables", table_fqn, "tags")
    if table is None:
        logger.warning("  table '%s' not found — skipping glossary tags", table_fqn)
        return
    existing = {tag.get("tagFQN") for tag in (table.get("tags") or [])}
    new_labels = [
        {
            "tagFQN": f"{GLOSSARY_NAME}.{term_name}",
            "source": "Glossary",
            "labelType": "Manual",
            "state": "Confirmed",
        }
        for term_name in GLOSSARY_TERMS_ON_TABLE
        if f"{GLOSSARY_NAME}.{term_name}" not in existing
    ]
    if not new_labels:
        logger.info("  glossary terms already on '%s' — skipping", table_fqn)
        return
    logger.info("  tagging '%s' with %d glossary term(s)", table_fqn, len(new_labels))
    patch = (
        [{"op": "add", "path": "/tags/-", "value": label} for label in new_labels]
        if table.get("tags")
        else [{"op": "add", "path": "/tags", "value": new_labels}]
    )
    client.json_patch(f"/v1/tables/name/{table_fqn}", patch)


def _delete_superseded_articles(client: OMClient) -> None:
    """Remove knowledge articles created by earlier revisions (best-effort)."""
    for name in SUPERSEDED_ARTICLE_NAMES:
        article = get_entity(client, "contextCenter/pages", name)
        if article is None:
            continue
        logger.info("  removing superseded article '%s'", name)
        client.send(
            "DELETE", f"/v1/contextCenter/pages/{article['id']}?hardDelete=true", None
        )


def ensure_knowledge_article(client: OMClient, table_fqn: str) -> None:
    """Create a Knowledge Center article linked to the PII table (idempotent).

    A knowledge article is a Page (``pageType=Article``); its body is the
    ``description`` (what the context builder renders). Listing the table in
    ``relatedEntities`` stores the ``asset HAS page`` relationship the persona /
    asset context builder reads for the ``articles`` section. ``PUT`` is
    create-or-update, so re-running is safe.
    """
    table = get_entity(client, "tables", table_fqn)
    if table is None:
        logger.warning("  table '%s' not found — skipping knowledge article", table_fqn)
        return
    verb = (
        "already present — updating"
        if get_entity(client, "contextCenter/pages", KNOWLEDGE_ARTICLE["name"])
        is not None
        else "creating"
    )
    logger.info(
        "  knowledge article '%s' %s (linked to '%s')",
        KNOWLEDGE_ARTICLE["name"],
        verb,
        table_fqn,
    )
    client.put(
        "/v1/contextCenter/pages",
        {
            "name": KNOWLEDGE_ARTICLE["name"],
            "displayName": KNOWLEDGE_ARTICLE["displayName"],
            "pageType": "Article",
            "description": KNOWLEDGE_ARTICLE["description"],
            "page": {},
            "relatedEntities": [_ref(table, "table")],
        },
    )


def ensure_operating_rule_articles(client: OMClient) -> None:
    """Upsert one operating-rules article per persona (idempotent).

    Deliberately NOT linked to any table: if these were attached to the demo
    asset both personas would see both, because the ``articles`` section renders
    everything attached to the asset. Keeping them unattached means the only
    thing that pulls one in is the persona's own page rule — which is exactly the
    behaviour the demo is showing off.
    """
    for persona, article in OPERATING_RULE_ARTICLES.items():
        verb = (
            "updating"
            if get_entity(client, "contextCenter/pages", article["name"]) is not None
            else "creating"
        )
        logger.info(
            "  %s operating-rules article '%s' (%s)", verb, article["name"], persona
        )
        client.put(
            "/v1/contextCenter/pages",
            {
                "name": article["name"],
                "displayName": article["displayName"],
                "pageType": "Article",
                "description": article["description"],
                "page": {},
            },
        )


def enrich_governance_context(client: OMClient, table_fqns: list[str]) -> None:
    """Glossary terms + knowledge articles, attached to the demo PII table."""
    ensure_glossary(client)
    ensure_operating_rule_articles(client)
    _delete_superseded_articles(client)
    if not table_fqns:
        logger.warning("  no PII table resolved — skipping glossary tags + article")
        return
    assign_glossary_terms_to_table(client, table_fqns[0])
    ensure_knowledge_article(client, table_fqns[0])


# ---------------------------------------------------------------------------
# Access tokens — log in AS each user and print a paste-ready token
# ---------------------------------------------------------------------------


def _encode_password(password: str) -> str:
    """OpenMetadata basic-auth endpoints expect base64-encoded passwords (as the UI sends)."""
    return base64.b64encode(password.encode("utf-8")).decode("ascii")


def _acquire_user_token(
    client: OMClient, entry: dict[str, str], password: str
) -> str | None:
    """Admin-reset the user's password, log in as them, return their access token.

    Returns None (with a warning) if the instance blocks it — e.g. SSO, where
    there is no password login. The token authenticates as the real, non-bot
    user, so RBAC and PII masking still apply (a bot token would not).
    """
    username = entry["username"]
    user = get_entity(client, "users", username)
    if user is None:
        logger.warning("  user '%s' not found — cannot mint a token", username)
        return None

    # Encoding asymmetry (verified in OSS UserResource): POST /login base64-decodes
    # the password, but PUT /changePassword does NOT. So set the RAW password here
    # and send base64 only at login — encoding both stores the hash of the base64
    # string and every login 401s.
    reset = client.send(
        "PUT",
        "/v1/users/changePassword",
        {
            "username": username,
            "newPassword": password,
            "confirmPassword": password,
            "requestType": "USER",
        },
    )
    if reset is None:
        return None  # dry-run
    if reset.status_code >= 400:
        logger.warning(
            "  could not set password for '%s' (HTTP %s) — generate a token manually (SSO?)",
            username,
            reset.status_code,
        )
        return None

    login = client.send(
        "POST",
        "/v1/users/login",
        {"email": user.get("email"), "password": _encode_password(password)},
    )
    if login is None or login.status_code >= 400:
        code = "n/a" if login is None else login.status_code
        logger.warning(
            "  login failed for '%s' (HTTP %s) — generate a token manually",
            username,
            code,
        )
        return None
    token = login.json().get("accessToken")
    if not token:
        logger.warning("  no accessToken returned for '%s'", username)
        return None
    logger.info("  %s (%s): token acquired", username, entry["persona"])
    return token


def print_user_tokens(client: OMClient, password: str) -> None:
    """Print a paste-ready ``export DEMO_*_TOKEN=...`` line per demo user.

    OpenMetadata forbids an admin from minting another regular user's token
    (anti-impersonation) and bots bypass PII masking, so the only correct way to
    get a per-user token is to log in AS that user — which is what this does.
    """
    exports: list[tuple[str, str]] = []
    for entry in DEMO_USERS:
        token = _acquire_user_token(client, entry, password)
        if token is None:
            continue
        env = TOKEN_ENV_BY_PERSONA.get(entry["persona"])
        if env is not None:
            exports.append((env, token))

    if not exports:
        logger.info(
            "  No tokens minted. Generate one per user in the UI (log in as each -> "
            "Access Tokens) and export DEMO_COMPLIANCE_TOKEN / DEMO_ENGINEER_TOKEN."
        )
        return
    logger.info("\nPaste these to run persona_demo.ipynb / persona_demo.py:")
    for env, token in exports:
        logger.info("export %s=%s", env, token)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _resolve_demo_tables(
    client: OMClient, explicit: list[str], service: str, limit: int
) -> list[str]:
    """The tables every later step operates on, most specific source first.

    Explicit ``--pii-table-fqn`` wins, then ``DEMO_TABLE_FQN``, then the known
    Jaffle Shop demo tables, and finally — for instances that carry PII tags from
    somewhere else entirely — whatever search turns up inside the service.
    """
    if explicit:
        return explicit
    env_fqn = os.environ.get("DEMO_TABLE_FQN")
    if env_fqn:
        return [env_fqn]
    known = demo_tables(client, service)
    if known:
        logger.info("Using %d demo table(s) from service '%s'", len(known), service)
        return known
    discovered = discover_pii_tables(client, service, limit)
    if discovered:
        logger.info("Discovered %d PII table(s) via search", len(discovered))
    return discovered


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Configure the Persona-aware Context demo"
    )
    parser.add_argument("--host", default=os.environ.get("AI_SDK_HOST"))
    parser.add_argument("--token", default=os.environ.get("AI_SDK_TOKEN"))
    parser.add_argument(
        "--service",
        default=os.environ.get("DEMO_SERVICE", DEFAULT_SERVICE),
        help=f"Database service holding the demo tables (default: {DEFAULT_SERVICE!r}).",
    )
    parser.add_argument(
        "--demo-db-dsn",
        default=os.environ.get("DEMO_DB_DSN", DEMO_DB_DSN),
        help="Postgres DSN of the running demo database, used for profiling.",
    )
    parser.add_argument(
        "--pii-table-fqn",
        action="append",
        default=[],
        help="FQN of a demo table (repeatable). Defaults to the known Jaffle Shop tables.",
    )
    parser.add_argument(
        "--max-owned-tables",
        type=int,
        default=25,
        help="Cap on tables owned when discovering via search (default: 25).",
    )
    parser.add_argument(
        "--with-pii-policy",
        action="store_true",
        help="Also create a PII allow-policy/role (enterprise / policy-driven masking).",
    )
    parser.add_argument(
        "--skip-users",
        action="store_true",
        help="Skip creating the demo users (david.kim / sara.johnson).",
    )
    parser.add_argument(
        "--skip-roles",
        action="store_true",
        help=f"Skip granting the demo users the baseline '{BASELINE_ROLE}' role.",
    )
    parser.add_argument(
        "--skip-pii-tags",
        action="store_true",
        help="Skip tagging sensitive columns with PII.Sensitive.",
    )
    parser.add_argument(
        "--skip-profiles",
        action="store_true",
        help="Skip profiling the demo database into column profiles + sample rows.",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip executing the ingested data-quality tests against the demo database.",
    )
    parser.add_argument(
        "--skip-personas", action="store_true", help="Skip Axis B persona config."
    )
    parser.add_argument(
        "--skip-default-persona",
        action="store_true",
        help="Skip assigning each demo user's default persona (and membership).",
    )
    parser.add_argument(
        "--skip-ownership", action="store_true", help="Skip Axis A ownership."
    )
    parser.add_argument(
        "--skip-ground-rules",
        action="store_true",
        help="Skip the per-person ground-rules Context Center memories.",
    )
    parser.add_argument(
        "--skip-knowledge",
        action="store_true",
        help="Skip the glossary terms + knowledge article enrichment.",
    )
    parser.add_argument(
        "--skip-tokens",
        action="store_true",
        help="Skip minting + printing a login token per demo user.",
    )
    parser.add_argument(
        "--demo-password",
        default=DEMO_PASSWORD,
        help="Password set on demo users so the script can log in as them (basic-auth only).",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print changes without applying."
    )
    args = parser.parse_args()

    if not args.host or not args.token:
        print(
            "Set AI_SDK_HOST and AI_SDK_TOKEN (admin token), or pass --host/--token.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    client = OMClient(args.host, args.token, args.dry_run)
    try:
        if not args.skip_users:
            logger.info("=== Demo users — create if missing ===")
            ensure_users_exist(client)

        if not args.skip_roles:
            logger.info("\n=== Access — baseline role so both users can read ===")
            grant_baseline_role(client)

        logger.info("\n=== Demo tables ===")
        table_fqns = _resolve_demo_tables(
            client, args.pii_table_fqn, args.service, args.max_owned_tables
        )
        if not table_fqns:
            logger.warning(
                "No demo tables resolved in service '%s'. Ingest the demo database, pass "
                "--service/--pii-table-fqn, or set DEMO_TABLE_FQN — every scene below "
                "needs an asset to attach to.",
                args.service,
            )

        if not args.skip_pii_tags:
            logger.info("\n=== Data — PII column tags (the masking lever) ===")
            tag_pii_columns(client, table_fqns)

        if not args.skip_profiles:
            logger.info("\n=== Data — column profiles + sample rows ===")
            seed_profiles_and_samples(client, table_fqns, args.demo_db_dsn)

        if not args.skip_tests:
            logger.info("\n=== Data — execute the data-quality tests ===")
            ensure_extra_test_cases(client, args.service)
            run_data_quality_tests(client, table_fqns, args.demo_db_dsn)

        # Knowledge first: the persona rules below select the operating-rules
        # articles by name, so those articles have to exist before the rules are
        # written or the first run renders an empty section.
        if not args.skip_knowledge:
            logger.info(
                "\n=== Axis B enrichment — glossary terms + knowledge articles ==="
            )
            enrich_governance_context(client, table_fqns)

        if not args.skip_personas:
            logger.info("\n=== Axis B — persona context definitions ===")
            for config in persona_configs(args.service):
                configure_persona(client, config)

        if not args.skip_default_persona:
            logger.info("\n=== Axis B — default persona per user ===")
            assign_default_personas(client)

        if not args.skip_ownership:
            logger.info("\n=== Axis A — PII ownership (masking lever) ===")
            if table_fqns:
                assign_pii_ownership(client, table_fqns)

        if not args.skip_ground_rules:
            logger.info("\n=== Foundational context — per-person ground rules ===")
            create_ground_rules(client, table_fqns)

        if args.with_pii_policy:
            logger.info("\n=== Optional — PII allow-policy/role ===")
            create_pii_policy_and_role(client)

        if not args.skip_tokens:
            logger.info("\n=== Access tokens — log in as each user ===")
            print_user_tokens(client, args.demo_password)

        logger.info("\nDone.%s", " (dry run — nothing changed)" if args.dry_run else "")
    finally:
        client.close()


if __name__ == "__main__":
    main()
