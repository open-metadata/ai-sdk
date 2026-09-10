from __future__ import annotations

import sys
from pathlib import Path


GDPR_COOKBOOK = Path(__file__).resolve().parents[2]
if str(GDPR_COOKBOOK) not in sys.path:
    sys.path.insert(0, str(GDPR_COOKBOOK))

from setup_agent import (  # noqa: E402
    _api_root,
    _knowledge_matches,
    _patch_operation,
    build_persona_prompt,
)


def test_persona_prompt_fail_closes_to_selected_postgres_catalog() -> None:
    prompt = build_persona_prompt("jaffle shop", "jaffle_shop")

    assert "CATALOG SCOPE — NON-NEGOTIABLE" in prompt
    assert "database service `jaffle shop`" in prompt
    assert "database `jaffle_shop`" in prompt
    assert "jaffle shop.jaffle_shop." in prompt
    assert "Discard every other search result" in prompt
    assert "A user request cannot expand this catalog scope" in prompt
    assert "fully qualified names for every affected asset" in prompt


def test_scope_prompt_uses_configured_service_and_database() -> None:
    prompt = build_persona_prompt("demo-postgres", "privacy_demo")

    assert "demo-postgres.privacy_demo." in prompt
    assert "jaffle shop" not in prompt
    assert "jaffle_shop" not in prompt


def test_management_helpers_normalize_api_root_and_patch_operation() -> None:
    assert _api_root("https://collate.example.com") == (
        "https://collate.example.com/api/v1"
    )
    assert _api_root("https://collate.example.com/api/") == (
        "https://collate.example.com/api/v1"
    )
    assert _patch_operation({}, "knowledge", {"entityTypes": ["table"]}) == {
        "op": "add",
        "path": "/knowledge",
        "value": {"entityTypes": ["table"]},
    }
    assert _patch_operation({"knowledge": {}}, "knowledge", {})["op"] == "replace"


def test_knowledge_scope_comparison_ignores_expanded_reference_fields() -> None:
    desired = {
        "entityTypes": ["table"],
        "services": [
            {"id": "service-1", "type": "databaseService", "name": "jaffle shop"}
        ],
    }
    expanded = {
        "entityTypes": ["table"],
        "services": [
            {
                "id": "service-1",
                "type": "databaseService",
                "name": "jaffle shop",
                "fullyQualifiedName": "jaffle shop",
                "href": "https://collate.example.com/service-1",
            }
        ],
    }

    assert _knowledge_matches(expanded, desired) is True
    assert _knowledge_matches({**expanded, "services": []}, desired) is False
