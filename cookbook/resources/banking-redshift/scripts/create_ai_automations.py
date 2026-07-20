"""
Seed banking-demo AI Automation TEMPLATES into OpenMetadata.

Loads each JSON file in ``../ai_automations/`` and POSTs it to
``/v1/ai/automations`` as a system-provided TEMPLATE (``isTemplate: true``,
``provider: system``). Templates are read-only blueprints surfaced in the
UI; users instantiate concrete automations from them.

Re-runs are idempotent: existing templates with the same name are skipped
(the API rejects PUT/PATCH/DELETE on templates).

Requires:
    pip install requests

Usage:
    export AI_SDK_HOST=http://localhost:8585
    export AI_SDK_TOKEN=<your-jwt-token>
    python create_ai_automations.py

    # Override template directory:
    python create_ai_automations.py --templates-dir ../ai_automations
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)


DEFAULT_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "ai_automations"


# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------


@dataclass
class CreationResult:
    created: list[str] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)

    @property
    def has_failures(self) -> bool:
        return bool(self.failed)

    def print_summary(self) -> None:
        logger.info("--- Summary ---")
        logger.info("  Created : %d", len(self.created))
        for name in self.created:
            logger.info("    + %s", name)
        logger.info("  Skipped : %d", len(self.skipped))
        for name, reason in self.skipped:
            logger.info("    - %s (%s)", name, reason)
        logger.info("  Failed  : %d", len(self.failed))
        for name, reason in self.failed:
            logger.error("    ! %s (%s)", name, reason)


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------


class CollateClient:
    """Thin wrapper around ``requests`` for the OpenMetadata REST API."""

    def __init__(self, host: str, token: str) -> None:
        host = host.rstrip("/")
        if not host.endswith("/api"):
            host = f"{host}/api"
        self.base = host
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def health(self) -> None:
        url = f"{self.base}/v1/system/version"
        response = self.session.get(url, timeout=15)
        response.raise_for_status()
        logger.info("Connected to OpenMetadata at %s", self.base)

    def get_entity_reference(self, path: str, name: str) -> dict[str, Any] | None:
        url = f"{self.base}{path}/name/{name}"
        response = self.session.get(url, timeout=15)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        entity = response.json()
        return {
            "id": entity["id"],
            "type": entity.get("type") or path.rsplit("/", 1)[-1].rstrip("s"),
            "name": entity["name"],
            "fullyQualifiedName": entity.get("fullyQualifiedName", entity["name"]),
        }

    def automation_exists(self, fqn: str) -> bool:
        url = f"{self.base}/v1/ai/automations/name/{fqn}"
        response = self.session.get(url, timeout=15)
        if response.status_code == 404:
            return False
        response.raise_for_status()
        return True

    def post_automation(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base}/v1/ai/automations"
        response = self.session.post(url, json=payload, timeout=30)
        if response.status_code >= 400:
            raise RuntimeError(
                f"POST {url} -> {response.status_code}: {response.text}"
            )
        return response.json()


# ---------------------------------------------------------------------------
# Template loading + payload building
# ---------------------------------------------------------------------------


def load_templates(templates_dir: Path) -> list[dict[str, Any]]:
    if not templates_dir.is_dir():
        raise FileNotFoundError(f"Templates directory not found: {templates_dir}")
    files = sorted(templates_dir.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No JSON templates in {templates_dir}")
    templates: list[dict[str, Any]] = []
    for path in files:
        with path.open() as fp:
            templates.append(json.load(fp))
        logger.debug("Loaded %s", path.name)
    return templates


def build_payload(
    template: dict[str, Any],
    *,
    agent_ref: dict[str, Any],
) -> dict[str, Any]:
    """Build a CreateAIAutomation payload that preserves the template flag."""
    payload: dict[str, Any] = {
        "name": template["name"],
        "displayName": template.get("displayName", template["name"]),
        "description": template["description"],
        "provider": template.get("provider", "system"),
        "isTemplate": True,
        "prompt": template["prompt"],
        "promptVariables": template.get("promptVariables", []),
        "agent": agent_ref,
        "sourceFilter": template.get(
            "sourceFilter",
            {"entityType": "table", "esQuery": "", "batchSize": 100},
        ),
        "airflowConfig": template.get("airflowConfig", {}),
        "destinations": template.get("destinations", []),
        "enabled": template.get("enabled", False),
        "entityStatus": template.get("entityStatus", "Approved"),
    }
    if "targetType" in template:
        payload["targetType"] = template["targetType"]
    return payload


# ---------------------------------------------------------------------------
# Main workflow
# ---------------------------------------------------------------------------


def seed_templates(
    client: CollateClient,
    templates: list[dict[str, Any]],
) -> CreationResult:
    result = CreationResult()

    # Resolve every distinct agent name up-front so we surface errors early
    # and avoid duplicate round-trips when templates share an agent.
    agent_refs: dict[str, dict[str, Any]] = {}
    for template in templates:
        agent_name = template.get("agent", {}).get("name")
        if not agent_name or agent_name in agent_refs:
            continue
        ref = client.get_entity_reference("/v1/agents/dynamic", agent_name)
        if ref is None:
            logger.error("Dynamic Agent '%s' not found in platform", agent_name)
        else:
            ref["type"] = "dynamicAgent"
            agent_refs[agent_name] = ref

    for template in templates:
        name = template["name"]
        agent_name = template.get("agent", {}).get("name")
        if not agent_name:
            result.skipped.append((name, "template has no agent reference"))
            continue
        agent_ref = agent_refs.get(agent_name)
        if agent_ref is None:
            result.skipped.append(
                (name, f"agent '{agent_name}' not found in platform")
            )
            continue

        if client.automation_exists(name):
            result.skipped.append((name, "already exists (templates are immutable)"))
            continue

        payload = build_payload(template, agent_ref=agent_ref)

        try:
            client.post_automation(payload)
        except Exception as exc:  # noqa: BLE001 — report to summary, keep going
            result.failed.append((name, str(exc)))
            continue

        result.created.append(name)

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Seed banking-demo AI Automation TEMPLATES (isTemplate=true) into "
            "OpenMetadata via /v1/ai/automations."
        )
    )
    parser.add_argument(
        "--host",
        default=os.getenv("AI_SDK_HOST", "http://localhost:8585"),
        help="OpenMetadata host (default: $AI_SDK_HOST or http://localhost:8585)",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("AI_SDK_TOKEN", ""),
        help="JWT token (default: $AI_SDK_TOKEN)",
    )
    parser.add_argument(
        "--templates-dir",
        type=Path,
        default=DEFAULT_TEMPLATES_DIR,
        help=f"Directory containing template JSONs (default: {DEFAULT_TEMPLATES_DIR})",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()

    if not args.token:
        logger.error("No token provided. Set AI_SDK_TOKEN or pass --token.")
        sys.exit(1)

    client = CollateClient(args.host, args.token)
    client.health()

    templates = load_templates(args.templates_dir)
    logger.info("Loaded %d template(s) from %s", len(templates), args.templates_dir)

    result = seed_templates(client, templates)

    result.print_summary()

    if result.has_failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
