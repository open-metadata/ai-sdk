"""Integration tests for memories namespace.

Requires AI_SDK_HOST and AI_SDK_TOKEN environment variables.
"""

from __future__ import annotations

import os
import time
import uuid
from collections.abc import Iterator

import pytest

from ai_sdk import (
    AISdk,
    AISdkConfig,
    ContextMemory,
    CreateContextMemoryRequest,
    MemorySearchResults,
    MemoryType,
)

pytestmark = pytest.mark.skipif(
    not (os.getenv("AI_SDK_HOST") and os.getenv("AI_SDK_TOKEN")),
    reason="Integration tests require AI_SDK_HOST and AI_SDK_TOKEN",
)


@pytest.fixture(scope="module")
def client() -> Iterator[AISdk]:
    cfg = AISdkConfig.from_env()
    sdk = AISdk.from_config(cfg)
    try:
        yield sdk
    finally:
        sdk.close()


def _unique_name() -> str:
    return f"sdk-int-{uuid.uuid4().hex[:8]}-{int(time.time())}"


class TestMemoryRoundTrip:
    """End-to-end create -> get -> list -> search -> delete cycle."""

    def test_full_round_trip(self, client: AISdk) -> None:
        name = _unique_name()
        req = CreateContextMemoryRequest(
            name=name,
            title="Integration test memory",
            question="What is the integration test asking about?",
            answer="A throwaway memory created by the SDK integration test.",
            memory_type=MemoryType.NOTE,
        )

        created = client.memories.create(req)
        assert isinstance(created, ContextMemory)
        assert created.name == name
        memory_id = created.id

        try:
            fetched = client.memories.get(memory_id)
            assert fetched.id == memory_id
            assert fetched.name == name

            listed = client.memories.list(limit=200)
            assert any(m.id == memory_id for m in listed)

            # Search may need indexing time — best-effort assertion
            results = client.memories.search("integration test memory", size=20)
            assert isinstance(results, MemorySearchResults)
        finally:
            client.memories.delete(memory_id, hard_delete=True)
