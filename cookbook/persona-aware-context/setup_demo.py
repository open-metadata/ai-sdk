"""
Configure the banking-redshift instance for the Persona-aware Context demo.

Run this ONCE (with an admin token) after the banking-redshift cookbook has
been ingested. It is idempotent — safe to re-run.

It sets up the three things the demo shows off:

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

  Foundational context — per-person operating rule (Context Center)
      Upserts a PRIVATE ``Preference`` memory per user, owned by and visible only
      to that user, attached to the demo table. Each person's ``get_asset_context``
      then carries only their own operating rule, so the SAME question yields
      visibly different answers (compliance: lead with owner/governance, cite the
      policy + glossary, point to the certified dataset; engineering: give the dbt
      model path, freshness SLA, and a runnable SELECT). This is the easy-to-show,
      non-PII behavioral difference. Disable with ``--skip-ground-rules``.

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
* The banking-redshift cookbook ingested for the PII tables + classification.
  The two demo USERS (``david.kim`` / ``sara.johnson``) and the
  ``ComplianceOfficer`` / ``DataEngineer`` PERSONAS are CREATED by this script if
  missing — so the only hard requirement is an admin token and a reachable
  instance with the banking tables.
* An ADMIN token — persona AI-context config requires admin.
* ``pip install requests``

--------------------------------------------------------------------------------
Usage
--------------------------------------------------------------------------------
    export AI_SDK_HOST=http://localhost:8585
    export AI_SDK_TOKEN=<admin-jwt>

    python setup_demo.py                 # discover PII tables via search
    python setup_demo.py --pii-table-fqn redshift.banking.marts_core.dim_customers
    python setup_demo.py --with-pii-policy
    python setup_demo.py --dry-run       # print what it would do, change nothing
"""

from __future__ import annotations

import argparse
import base64
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


# ---------------------------------------------------------------------------
# Persona context definitions (Axis B)
# ---------------------------------------------------------------------------

# Both personas point at the same PII-tagged tables; only the rendered
# `sections` differ. That makes the side-by-side contrast unambiguous. In a
# real deployment you would also scope each persona to its own domain — adjust
# `queryFilter` to taste (build it in the Explore UI and copy the payload).
_PII_TABLES_FILTER = {"term": {"tags.tagFQN": PII_TAG}}

PERSONA_CONFIGS: list[dict[str, Any]] = [
    {
        "persona": "ComplianceOfficer",
        "displayName": "Compliance Officer",
        "description": (
            "Compliance and data-governance persona: sensitive/PII data, glossary "
            "terms, and data-quality standing."
        ),
        "settings": {"enabled": True, "characterBudget": 400000, "cacheTtlMinutes": 30},
        "rules": [
            {
                "name": "Sensitive customer and account data",
                "description": "Customer/account tables carrying sensitive PII.",
                "entityType": "table",
                "queryFilter": _PII_TABLES_FILTER,
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
        "settings": {"enabled": True, "characterBudget": 400000, "cacheTtlMinutes": 30},
        "rules": [
            {
                "name": "Customer and account data pipelines",
                "description": "The same customer/account tables, seen as pipelines.",
                "entityType": "table",
                "queryFilter": _PII_TABLES_FILTER,
                "sections": ["schema", "constraints", "joins", "lineage", "profile"],
                "maxAssets": 50,
                "alwaysInContext": True,
                "enabled": True,
            },
        ],
    },
]

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
        "description": "Data that can identify a specific individual — e.g. SSN, tax ID, date of birth.",
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
GLOSSARY_TERMS_ON_TABLE: list[str] = ["PersonallyIdentifiableInformation", "DataRetention"]

# One Knowledge Center article, linked to the PII table via a HAS relationship so
# the ComplianceOfficer persona's `articles` section renders it. The body lives in
# `description` — that is what the AI-context builder renders (fullContentOf).
KNOWLEDGE_ARTICLE: dict[str, str] = {
    "name": "customer-pii-handling-policy",
    "displayName": "Customer PII Handling Policy",
    "description": (
        "# Customer PII Handling Policy\n\n"
        "- Treat `ssn`, `tax_id`, and `date_of_birth` as **restricted**: never export "
        "or paste raw values.\n"
        "- Cite the applicable **data-retention** window when reporting on customer data.\n"
        "- Confirm a lawful **consent basis** before processing personal data.\n"
    ),
}

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
            "- Give the dbt model path (e.g. `models/marts/dim_customers.sql`).\n"
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

    def _mutate(self, method: str, path: str, payload: Any, content_type: str | None) -> None:
        if self.dry_run:
            logger.info("[dry-run] %s %s\n%s", method, path, json.dumps(payload, indent=2))
            return
        headers = {"Content-Type": content_type} if content_type else None
        response = self._session.request(
            method, f"{self.base}{path}", json=payload, headers=headers, timeout=TIMEOUT
        )
        if response.status_code >= 400:
            raise RuntimeError(f"{method} {path} -> {response.status_code}: {response.text}")

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
        return self._session.request(method, f"{self.base}{path}", json=payload, timeout=TIMEOUT)


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


def discover_pii_tables(client: OMClient, limit: int) -> list[str]:
    """Find tables carrying the PII.Sensitive tag via the search API."""
    query_filter = json.dumps({"query": {"term": {"tags.tagFQN": PII_TAG}}})
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
            "PII table search failed (HTTP %s); pass --pii-table-fqn", response.status_code
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
# Demo users — create them if the ingest didn't
# ---------------------------------------------------------------------------


def ensure_users_exist(client: OMClient) -> None:
    """Create each demo user if missing (idempotent).

    Normally the banking-redshift ingest seeds ``david.kim`` / ``sara.johnson``;
    this makes the demo self-contained. Only ``name`` + ``email`` are required.
    It does NOT generate access tokens — do that per user (see README).
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


# ---------------------------------------------------------------------------
# Axis B — persona context definitions
# ---------------------------------------------------------------------------


def existing_rule_names(client: OMClient, persona_id: str) -> set[str]:
    response = client.get(f"/v1/personas/{persona_id}/aiContext")
    if response.status_code != 200:
        return set()
    rules = response.json().get("rules", []) or []
    return {rule.get("name") for rule in rules if isinstance(rule, dict)}


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
        logger.warning("Persona '%s' not resolvable (dry-run?) — skipping AI context.", name)
        return

    logger.info("Persona '%s' (%s): enabling AI context", name, persona_id)
    client.put(f"/v1/personas/{persona_id}/aiContext", config["settings"])

    present = existing_rule_names(client, persona_id)
    for rule in config["rules"]:
        if rule["name"] in present:
            logger.info("  rule '%s' already present — skipping", rule["name"])
            continue
        # queryFilter must be a JSON-ENCODED STRING, not a nested object.
        body = dict(rule)
        body["queryFilter"] = json.dumps(rule["queryFilter"])
        logger.info("  adding rule '%s' (sections: %s)", rule["name"], ", ".join(rule["sections"]))
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
        logger.info("  %s default persona already '%s' — skipping", username, persona_ref.get("name"))
        return
    logger.info("  setting %s default persona -> '%s'", username, persona_ref.get("name"))
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
            logger.warning("  persona '%s' not found — skipping for %s", entry["persona"], username)
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
        logger.warning("  table '%s' not found (HTTP %s) — skipping", fqn, response.status_code)
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
        logger.error("Cannot assign ownership — user '%s' not found.", PII_OWNER_USERNAME)
        return
    logger.info("Assigning %s as owner of %d PII table(s)", PII_OWNER_USERNAME, len(table_fqns))
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
                    "operations": ["ViewAll", "ViewDataProfile", "ViewSampleData", "ViewTests"],
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
            [{"op": "add", "path": "/roles/0", "value": {"id": role_id, "type": "role"}}],
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
        client.send("DELETE", f"/v1/contextCenter/memories/{memory['id']}?hardDelete=true", None)


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
            logger.warning("  user '%s' not found — skipping operating rule", rule["username"])
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
            "  upserting operating-rule memory '%s' for %s", rule["name"], rule["username"]
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
        if get_entity(client, "contextCenter/pages", KNOWLEDGE_ARTICLE["name"]) is not None
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


def enrich_governance_context(client: OMClient, table_fqns: list[str]) -> None:
    """Glossary terms + one knowledge article, both attached to the demo PII table."""
    ensure_glossary(client)
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


def _acquire_user_token(client: OMClient, entry: dict[str, str], password: str) -> str | None:
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
        logger.warning("  login failed for '%s' (HTTP %s) — generate a token manually", username, code)
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


def _resolve_pii_tables(client: OMClient, explicit: list[str], limit: int) -> list[str]:
    if explicit:
        return explicit
    env_fqn = os.environ.get("DEMO_TABLE_FQN")
    if env_fqn:
        return [env_fqn]
    discovered = discover_pii_tables(client, limit)
    if discovered:
        logger.info("Discovered %d PII table(s) via search", len(discovered))
    return discovered


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Configure the Persona-aware Context demo")
    parser.add_argument("--host", default=os.environ.get("AI_SDK_HOST"))
    parser.add_argument("--token", default=os.environ.get("AI_SDK_TOKEN"))
    parser.add_argument(
        "--pii-table-fqn",
        action="append",
        default=[],
        help="FQN of a PII table to own (repeatable). Defaults to search discovery.",
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
    parser.add_argument("--skip-personas", action="store_true", help="Skip Axis B persona config.")
    parser.add_argument(
        "--skip-default-persona",
        action="store_true",
        help="Skip assigning each demo user's default persona (and membership).",
    )
    parser.add_argument("--skip-ownership", action="store_true", help="Skip Axis A ownership.")
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
    parser.add_argument("--dry-run", action="store_true", help="Print changes without applying.")
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

        if not args.skip_personas:
            logger.info("\n=== Axis B — persona context definitions ===")
            for config in PERSONA_CONFIGS:
                configure_persona(client, config)

        if not args.skip_default_persona:
            logger.info("\n=== Axis B — default persona per user ===")
            assign_default_personas(client)

        needs_tables = not (
            args.skip_ownership and args.skip_ground_rules and args.skip_knowledge
        )
        table_fqns = (
            _resolve_pii_tables(client, args.pii_table_fqn, args.max_owned_tables)
            if needs_tables
            else []
        )
        if needs_tables and not table_fqns:
            logger.warning(
                "No PII tables resolved. Pass --pii-table-fqn <fqn> or set DEMO_TABLE_FQN "
                "so get_asset_context and the ground-rules memories can attach to an asset."
            )

        if not args.skip_knowledge:
            logger.info("\n=== Axis B enrichment — glossary terms + knowledge article ===")
            enrich_governance_context(client, table_fqns)

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
