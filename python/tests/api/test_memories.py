"""Unit tests for MemoriesAPI."""

from __future__ import annotations

import json as json_module
from unittest.mock import AsyncMock, MagicMock

import pytest

from ai_sdk.api.memories import MemoriesAPI
from ai_sdk.models import (
    ContextMemory,
    CreateContextMemoryRequest,
    EntityReference,
    MemorySearchResults,
    MemoryType,
    MemoryVisibility,
)


def _memory_payload(name: str = "m1", primary_fqn: str | None = None) -> dict:
    return {
        "id": "11111111-1111-1111-1111-111111111111",
        "name": name,
        "fullyQualifiedName": name,
        "title": "T",
        "question": "q",
        "answer": "a",
        "summary": None,
        "memoryType": "Note",
        "memoryScope": "EntityScoped",
        "shareConfig": {"visibility": "Private"},
        "primaryEntity": (
            {"id": "abc", "type": "table", "fullyQualifiedName": primary_fqn}
            if primary_fqn
            else None
        ),
        "usageCount": 0,
        "lastUsedAt": None,
        "deleted": False,
    }


@pytest.fixture
def mock_http() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_search_http() -> MagicMock:
    return MagicMock()


@pytest.fixture
def memories(mock_http: MagicMock, mock_search_http: MagicMock) -> MemoriesAPI:
    return MemoriesAPI(
        http=mock_http,
        async_http=None,
        search_http=mock_search_http,
        search_async_http=None,
    )


class TestList:
    def test_list_no_filter(self, memories: MemoriesAPI, mock_http: MagicMock) -> None:
        mock_http.get.return_value = {
            "data": [_memory_payload("m1"), _memory_payload("m2")],
            "paging": {},
        }
        result = memories.list()
        assert len(result) == 2
        assert all(isinstance(m, ContextMemory) for m in result)
        mock_http.get.assert_called_once()
        path, kwargs = mock_http.get.call_args.args[0], mock_http.get.call_args.kwargs
        assert path == "/"
        assert "primaryEntityFqn" not in kwargs.get("params", {})

    def test_list_with_primary_entity_fqn_filter(
        self, memories: MemoriesAPI, mock_http: MagicMock
    ) -> None:
        mock_http.get.return_value = {
            "data": [_memory_payload("m1", primary_fqn="db.tbl")],
            "paging": {},
        }
        result = memories.list(primary_entity_fqn="db.tbl")
        assert len(result) == 1
        params = mock_http.get.call_args.kwargs.get("params", {})
        assert params.get("primaryEntityFqn") == "db.tbl"

    def test_list_respects_limit(self, memories: MemoriesAPI, mock_http: MagicMock) -> None:
        mock_http.get.return_value = {
            "data": [_memory_payload(f"m{i}") for i in range(5)],
            "paging": {},
        }
        result = memories.list(limit=3)
        assert len(result) == 3

    def test_list_paginates_via_after_token(
        self, memories: MemoriesAPI, mock_http: MagicMock
    ) -> None:
        mock_http.get.side_effect = [
            {"data": [_memory_payload("m1")], "paging": {"after": "page2"}},
            {"data": [_memory_payload("m2")], "paging": {}},
        ]
        result = memories.list()
        assert len(result) == 2
        assert mock_http.get.call_count == 2
        # second call should pass after=page2
        second_params = mock_http.get.call_args_list[1].kwargs.get("params", {})
        assert second_params.get("after") == "page2"


class TestGet:
    def test_get_calls_id_endpoint(self, memories: MemoriesAPI, mock_http: MagicMock) -> None:
        mock_http.get.return_value = _memory_payload("m1")
        result = memories.get("11111111-1111-1111-1111-111111111111")
        assert result.id == "11111111-1111-1111-1111-111111111111"
        assert result.name == "m1"
        mock_http.get.assert_called_once_with("/11111111-1111-1111-1111-111111111111")


class TestCreate:
    def test_create_posts_serialized_request(
        self, memories: MemoriesAPI, mock_http: MagicMock
    ) -> None:
        mock_http.post.return_value = _memory_payload("m1")
        req = CreateContextMemoryRequest(
            name="m1",
            question="q",
            answer="a",
            primary_entity=EntityReference(id="abc", type="table"),
            tags=["PII.Sensitive"],
            visibility=MemoryVisibility.SHARED,
            memory_type=MemoryType.PREFERENCE,
        )
        result = memories.create(req)
        assert isinstance(result, ContextMemory)
        assert result.name == "m1"

        path = mock_http.post.call_args.args[0]
        body = mock_http.post.call_args.kwargs["json"]
        assert path == "/"
        assert body["name"] == "m1"
        assert body["question"] == "q"
        assert body["answer"] == "a"
        assert body["memoryType"] == "Preference"
        assert body["shareConfig"] == {"visibility": "Shared"}
        assert body["primaryEntity"] == {"id": "abc", "type": "table"}
        assert body["tags"][0]["tagFQN"] == "PII.Sensitive"


class TestDelete:
    def test_delete_soft_default(self, memories: MemoriesAPI, mock_http: MagicMock) -> None:
        memories.delete("11111111-1111-1111-1111-111111111111")
        path = mock_http.delete.call_args.args[0]
        params = mock_http.delete.call_args.kwargs.get("params", {})
        assert path == "/11111111-1111-1111-1111-111111111111"
        assert params.get("hardDelete") is False

    def test_delete_hard(self, memories: MemoriesAPI, mock_http: MagicMock) -> None:
        memories.delete("xyz", hard_delete=True)
        params = mock_http.delete.call_args.kwargs.get("params", {})
        assert params.get("hardDelete") is True


class TestSearch:
    @staticmethod
    def _search_response() -> dict:
        return {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_score": 0.95,
                        "_source": _memory_payload("m1"),
                    }
                ],
            }
        }

    def test_search_minimal(
        self, memories: MemoriesAPI, mock_search_http: MagicMock
    ) -> None:
        mock_search_http.get.return_value = self._search_response()
        result = memories.search("explain customer churn")
        assert isinstance(result, MemorySearchResults)
        assert result.total == 1
        assert result.hits[0].score == 0.95
        assert result.hits[0].memory.name == "m1"

        path = mock_search_http.get.call_args.args[0]
        params = mock_search_http.get.call_args.kwargs.get("params", {})
        assert path == "/hybrid/nlq/search"
        assert params["q"] == "explain customer churn"
        assert params["index"] == "contextMemory"
        assert params["size"] == 15
        assert params["from"] == 0
        assert "filters" not in params

    def test_search_with_filters_serializes_to_json(
        self, memories: MemoriesAPI, mock_search_http: MagicMock
    ) -> None:
        mock_search_http.get.return_value = self._search_response()
        memories.search(
            "x",
            filters={"primaryEntityId": ["abc"], "visibility": ["Entity", "Shared"]},
            size=5,
            from_=10,
        )
        params = mock_search_http.get.call_args.kwargs.get("params", {})
        assert json_module.loads(params["filters"]) == {
            "primaryEntityId": ["abc"],
            "visibility": ["Entity", "Shared"],
        }
        assert params["size"] == 5
        assert params["from"] == 10


class TestAsyncRaisesWhenAsyncDisabled:
    def test_alist_raises_runtime_error(
        self, mock_http: MagicMock, mock_search_http: MagicMock
    ) -> None:
        api = MemoriesAPI(
            http=mock_http, async_http=None,
            search_http=mock_search_http, search_async_http=None,
        )

        async def call() -> None:
            await api.alist()

        import asyncio
        with pytest.raises(RuntimeError, match="Async HTTP client not available"):
            asyncio.run(call())


class TestAsyncMethods:
    @pytest.fixture
    def mock_async_http(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def mock_async_search_http(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def async_memories(
        self,
        mock_http: MagicMock,
        mock_search_http: MagicMock,
        mock_async_http: AsyncMock,
        mock_async_search_http: AsyncMock,
    ) -> MemoriesAPI:
        return MemoriesAPI(
            http=mock_http,
            async_http=mock_async_http,
            search_http=mock_search_http,
            search_async_http=mock_async_search_http,
        )

    @pytest.mark.asyncio
    async def test_alist(
        self, async_memories: MemoriesAPI, mock_async_http: AsyncMock
    ) -> None:
        mock_async_http.get.return_value = {"data": [_memory_payload("m1")], "paging": {}}
        result = await async_memories.alist()
        assert len(result) == 1
        assert result[0].name == "m1"

    @pytest.mark.asyncio
    async def test_acreate(
        self, async_memories: MemoriesAPI, mock_async_http: AsyncMock
    ) -> None:
        mock_async_http.post.return_value = _memory_payload("m1")
        req = CreateContextMemoryRequest(name="m1", question="q", answer="a")
        result = await async_memories.acreate(req)
        assert result.name == "m1"

    @pytest.mark.asyncio
    async def test_adelete(
        self, async_memories: MemoriesAPI, mock_async_http: AsyncMock
    ) -> None:
        await async_memories.adelete("xyz", hard_delete=True)
        params = mock_async_http.delete.call_args.kwargs.get("params", {})
        assert params.get("hardDelete") is True

    @pytest.mark.asyncio
    async def test_asearch(
        self, async_memories: MemoriesAPI, mock_async_search_http: AsyncMock
    ) -> None:
        mock_async_search_http.get.return_value = {
            "hits": {"total": {"value": 0}, "hits": []}
        }
        result = await async_memories.asearch("q")
        assert result.total == 0
