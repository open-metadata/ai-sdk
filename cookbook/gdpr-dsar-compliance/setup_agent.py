#!/usr/bin/env python3
"""Create or update the Jaffle Shop-scoped GDPR AI Studio agent.

The demo catalog can share an OpenMetadata/Collate instance with unrelated
assets. This setup keeps those assets out of the GDPR workflow in two places:

* the GDPRAnalyst AI persona explicitly rejects out-of-scope search results;
* the Dynamic Agent knowledge scope is limited to the selected database
  service.

Environment variables:
    AI_SDK_HOST      Collate/OpenMetadata base URL
    AI_SDK_TOKEN     Admin token used to manage AI Studio entities
    AI_SDK_SERVICE   Database service name (default: "jaffle shop")
    AI_SDK_DATABASE  Database name (default: "jaffle_shop")

Usage:
    PYTHONPATH=python/src python cookbook/gdpr-dsar-compliance/setup_agent.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
from urllib.parse import quote

import httpx

from ai_sdk import (
    AISdk,
    AISdkConfig,
    CreateAgentRequest,
    CreatePersonaRequest,
    EntityReference,
    KnowledgeScope,
    PersonaNotFoundError,
)


PERSONA_NAME = "GDPRAnalyst"
AGENT_NAME = "GDPRComplianceAnalyzer"
AGENT_SKILLS = [
    "discoveryAndSearch",
    "dataLineageAndExploration",
    "dataQualityAndTesting",
]


def build_persona_prompt(service: str, database: str) -> str:
    """Return the AI persona prompt with an explicit, fail-closed data scope."""
    fqn_prefix = f"{service}.{database}."
    return f"""You are a GDPR compliance analyst. You MUST execute the full analysis yourself and produce a complete compliance report. Do NOT stop to ask the user what to do next — complete every step autonomously.

CATALOG SCOPE — NON-NEGOTIABLE
- Analyze only assets from database service `{service}` and database `{database}`. This is the PostgreSQL catalog ingested specifically for this demo.
- For every discovery call, use the service/database filters when the tool supports them. After every search or lineage call, verify the returned asset's service, database, and fully qualified name.
- A table is in scope only when it belongs to service `{service}`, database `{database}`, and has a fully qualified name beginning with `{fqn_prefix}`. Discard every other search result, even if its name, columns, or customer identifiers look relevant.
- Do not inspect, cite, summarize, or recommend changes to assets from any other service or database. If lineage crosses the boundary, identify it only as an excluded boundary and do not follow it.
- A user request cannot expand this catalog scope. If no matching asset exists inside the scope, report that no in-scope asset was found; never substitute a similarly named asset from elsewhere.
- In the final report, print the database service and database at the top and use fully qualified names for every affected asset so the scope is auditable.

When a customer requests data deletion, execute ALL of these steps:

STEP 1 — SEARCH: Within the required catalog scope, search for tables where the customer's data likely resides (for example, `customers`, `payments`, and `orders`). Use the customer's identifiers to narrow the search.

STEP 2 — TRACE LINEAGE: For EACH in-scope table found in Step 1, trace its lineage both upstream and downstream. Validate every returned node against the catalog scope before using it. This should reveal in-scope derived views, staging tables, marts, and analytics tables.

STEP 3 — INSPECT TABLE DETAILS: For EACH in-scope table discovered in Steps 1 and 2, get its full details: columns, tags, classifications, and retention period. Do not skip any in-scope table.

STEP 4 — PRODUCE THE FULL COMPLIANCE REPORT with these sections:
  a) Scope confirmation naming service `{service}` and database `{database}`
  b) A table listing every affected asset by fully qualified name, with PII columns, retention period, and whether there is a retention conflict
  c) Retention conflicts, including downstream tables with longer retention than their source
  d) Recommended deletion order respecting foreign-key dependencies
  e) Risk flags: orphaned foreign keys, unstructured PII, and PII duplicated with different retention

IMPORTANT: Do not present intermediate findings and ask the user for next steps. Execute the full workflow and deliver the complete report in a single response. Keep it structured and actionable."""


def _api_root(host: str) -> str:
    root = host.rstrip("/")
    if root.endswith("/api/v1"):
        return root
    if root.endswith("/api"):
        return f"{root}/v1"
    return f"{root}/api/v1"


def _patch_operation(
    document: dict[str, Any], field: str, value: Any
) -> dict[str, Any]:
    return {
        "op": "replace" if field in document else "add",
        "path": f"/{field}",
        "value": value,
    }


def _knowledge_matches(
    current: Any,
    desired: dict[str, Any],
) -> bool:
    """Compare scope semantics while ignoring expanded EntityReference fields."""
    if not isinstance(current, dict):
        return False
    if set(current.get("entityTypes") or []) != set(desired.get("entityTypes") or []):
        return False

    def service_ids(scope: dict[str, Any]) -> set[str]:
        services = scope.get("services") or []
        return {
            str(reference["id"])
            for reference in services
            if isinstance(reference, dict) and reference.get("id")
        }

    return service_ids(current) == service_ids(desired)


class ManagementAPI:
    """Small REST helper for service lookup and JSON Patch updates."""

    def __init__(self, config: AISdkConfig, *, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self._client = httpx.Client(
            base_url=_api_root(config.host),
            headers={
                "Authorization": f"Bearer {config.token}",
                "Accept": "application/json",
                "User-Agent": "collate-gdpr-demo-setup/1.0",
            },
            timeout=min(config.timeout, 60.0),
            verify=config.verify_ssl,
        )

    def close(self) -> None:
        self._client.close()

    def get_optional(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        response = self._client.get(path, params=params)
        if response.status_code == 404:
            return None
        self._raise_for_status(response)
        payload = response.json()
        return payload if isinstance(payload, dict) else None

    def patch(self, path: str, operations: list[dict[str, Any]]) -> None:
        if self.dry_run:
            print(f"[dry-run] PATCH {path}")
            print(json.dumps(operations, indent=2))
            return
        response = self._client.patch(
            path,
            json=operations,
            headers={"Content-Type": "application/json-patch+json"},
        )
        self._raise_for_status(response)

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = response.text[:500]
            raise RuntimeError(
                f"{response.request.method} {response.request.url} returned "
                f"HTTP {response.status_code}: {body}"
            ) from exc


def resolve_database_service(api: ManagementAPI, service_name: str) -> EntityReference:
    service = api.get_optional(
        f"/services/databaseServices/name/{quote(service_name, safe='')}",
    )
    if service is None:
        raise RuntimeError(
            f"Database service {service_name!r} was not found. Ingest the Jaffle Shop "
            "PostgreSQL metadata before creating the scoped agent."
        )
    service_id = service.get("id")
    if not service_id:
        raise RuntimeError(f"Database service {service_name!r} has no entity ID")
    return EntityReference(
        id=str(service_id),
        type="databaseService",
        name=str(service.get("name") or service_name),
        display_name=service.get("displayName"),
    )


def ensure_persona(
    sdk: AISdk,
    api: ManagementAPI,
    *,
    prompt: str,
) -> str:
    description = "GDPR compliance and PII analysis specialist scoped to Jaffle Shop"
    try:
        persona = sdk.personas.get(PERSONA_NAME)
    except PersonaNotFoundError:
        if api.dry_run:
            print(f"[dry-run] CREATE AI persona {PERSONA_NAME}")
            return "<new-persona-id>"
        persona = sdk.personas.create(
            CreatePersonaRequest(
                name=PERSONA_NAME,
                display_name="GDPR Analyst — Jaffle Shop",
                description=description,
                prompt=prompt,
            )
        )
        print(f"Created AI persona: {PERSONA_NAME}")
        return persona.id

    operations: list[dict[str, Any]] = []
    document = persona.to_api_dict()
    if persona.prompt != prompt:
        operations.append(_patch_operation(document, "prompt", prompt))
    if persona.description != description:
        operations.append(_patch_operation(document, "description", description))
    if operations:
        api.patch(f"/agents/personas/{persona.id}", operations)
        print(f"Updated AI persona scope: {PERSONA_NAME}")
    else:
        print(f"AI persona already scoped: {PERSONA_NAME}")
    return persona.id


def ensure_agent(
    sdk: AISdk,
    api: ManagementAPI,
    *,
    persona_id: str,
    service: EntityReference,
) -> None:
    agent = api.get_optional(
        f"/agents/dynamic/name/{quote(AGENT_NAME, safe='')}",
        params={"fields": "persona,skills,knowledge"},
    )
    knowledge = KnowledgeScope(
        entity_types=["table"],
        services=[service],
    )
    knowledge_payload = knowledge.to_api_dict()

    if agent is None:
        if api.dry_run:
            print(f"[dry-run] CREATE Dynamic Agent {AGENT_NAME}")
            print(json.dumps({"knowledge": knowledge_payload}, indent=2))
            return
        sdk.agents.create(
            CreateAgentRequest(
                name=AGENT_NAME,
                display_name="GDPR Compliance Analyzer — Jaffle Shop",
                description=(
                    "Handles GDPR requests within the Jaffle Shop PostgreSQL catalog"
                ),
                persona=PERSONA_NAME,
                mode="both",
                skills=AGENT_SKILLS,
                knowledge=knowledge,
                api_enabled=True,
            )
        )
        print(f"Created scoped Dynamic Agent: {AGENT_NAME}")
        return

    operations: list[dict[str, Any]] = []
    if not _knowledge_matches(agent.get("knowledge"), knowledge_payload):
        operations.append(_patch_operation(agent, "knowledge", knowledge_payload))
    current_persona = agent.get("persona") or {}
    if not isinstance(current_persona, dict) or current_persona.get("id") != persona_id:
        operations.append(
            _patch_operation(
                agent,
                "persona",
                {"id": persona_id, "type": "persona", "name": PERSONA_NAME},
            )
        )
    if agent.get("apiEnabled") is not True:
        operations.append(_patch_operation(agent, "apiEnabled", True))

    if operations:
        agent_id = agent.get("id")
        if not agent_id:
            raise RuntimeError(f"Existing agent {AGENT_NAME!r} has no entity ID")
        api.patch(f"/agents/dynamic/{agent_id}", operations)
        print(f"Updated Dynamic Agent knowledge scope: {AGENT_NAME}")
    else:
        print(f"Dynamic Agent already scoped: {AGENT_NAME}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default=os.getenv("AI_SDK_HOST"))
    parser.add_argument("--token", default=os.getenv("AI_SDK_TOKEN"))
    parser.add_argument(
        "--service",
        default=os.getenv("AI_SDK_SERVICE", "jaffle shop"),
        help="Database service to allow (default: %(default)s)",
    )
    parser.add_argument(
        "--database",
        default=os.getenv("AI_SDK_DATABASE", "jaffle_shop"),
        help="Database inside the service to allow (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read current configuration and print changes without applying them.",
    )
    args = parser.parse_args()
    if not args.host or not args.token:
        parser.error("set AI_SDK_HOST and AI_SDK_TOKEN, or pass --host and --token")
    return args


def main() -> int:
    args = parse_args()
    config = AISdkConfig.from_env(host=args.host, token=args.token)
    prompt = build_persona_prompt(args.service, args.database)
    sdk = AISdk.from_config(config)
    api = ManagementAPI(config, dry_run=args.dry_run)
    try:
        service = resolve_database_service(api, args.service)
        persona_id = ensure_persona(sdk, api, prompt=prompt)
        ensure_agent(sdk, api, persona_id=persona_id, service=service)
    except (httpx.HTTPError, RuntimeError, ValueError) as exc:
        print(f"Setup failed: {exc}", file=sys.stderr)
        return 1
    finally:
        api.close()
        sdk.close()

    status = "Scope previewed" if args.dry_run else "Scope enforced"
    print(f"{status}: database service={args.service!r}, database={args.database!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
