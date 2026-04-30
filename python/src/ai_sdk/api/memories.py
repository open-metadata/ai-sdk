"""Memories namespace — CRUD + hybrid search for Context Center memories."""

from __future__ import annotations

import builtins
import json
from typing import Any

from ai_sdk._http import AsyncHTTPClient, HTTPClient
from ai_sdk.models import (
    ContextMemory,
    CreateContextMemoryRequest,
    MemorySearchResults,
)

# Alias `list` so type annotations on methods named `list` don't shadow the builtin.
_MemoryList = builtins.list[ContextMemory]


class MemoriesAPI:
    """Namespace for Context Center memory operations.

    Backed by two HTTP clients: one rooted at /api/v1/contextCenter/memories
    for CRUD, and one rooted at /api/v1 for the hybrid search endpoint at
    /hybrid/nlq/search.
    """

    def __init__(
        self,
        http: HTTPClient,
        async_http: AsyncHTTPClient | None,
        search_http: HTTPClient,
        search_async_http: AsyncHTTPClient | None,
    ) -> None:
        self._http = http
        self._async_http = async_http
        self._search_http = search_http
        self._search_async_http = search_async_http

    # ------------------------------------------------------------------
    # list / alist
    # ------------------------------------------------------------------

    def list(
        self,
        primary_entity_fqn: str | None = None,
        limit: int | None = None,
    ) -> _MemoryList:
        """List Context Center memories.

        Args:
            primary_entity_fqn: Filter to memories attached to this entity FQN.
            limit: Maximum number of memories to return; None returns all.
        """
        return _paginate(self._http, primary_entity_fqn=primary_entity_fqn, limit=limit)

    async def alist(
        self,
        primary_entity_fqn: str | None = None,
        limit: int | None = None,
    ) -> _MemoryList:
        if self._async_http is None:
            raise RuntimeError(
                "Async HTTP client not available. "
                "Use AISdk with enable_async=True for async operations."
            )
        return await _apaginate(
            self._async_http, primary_entity_fqn=primary_entity_fqn, limit=limit
        )

    # ------------------------------------------------------------------
    # get / aget
    # ------------------------------------------------------------------

    def get(self, memory_id: str) -> ContextMemory:
        """Get a memory by ID."""
        response = self._http.get(f"/{memory_id}")
        return ContextMemory.from_dict(response)

    async def aget(self, memory_id: str) -> ContextMemory:
        if self._async_http is None:
            raise RuntimeError(
                "Async HTTP client not available. "
                "Use AISdk with enable_async=True for async operations."
            )
        response = await self._async_http.get(f"/{memory_id}")
        return ContextMemory.from_dict(response)

    # ------------------------------------------------------------------
    # create / acreate
    # ------------------------------------------------------------------

    def create(self, request: CreateContextMemoryRequest) -> ContextMemory:
        """Create a new Context Center memory."""
        response = self._http.post("/", json=request.to_api_dict())
        return ContextMemory.from_dict(response)

    async def acreate(self, request: CreateContextMemoryRequest) -> ContextMemory:
        if self._async_http is None:
            raise RuntimeError(
                "Async HTTP client not available. "
                "Use AISdk with enable_async=True for async operations."
            )
        response = await self._async_http.post("/", json=request.to_api_dict())
        return ContextMemory.from_dict(response)

    # ------------------------------------------------------------------
    # delete / adelete
    # ------------------------------------------------------------------

    def delete(self, memory_id: str, hard_delete: bool = False) -> None:
        """Delete a memory by ID. Soft delete by default."""
        self._http.delete(f"/{memory_id}", params={"hardDelete": hard_delete})

    async def adelete(self, memory_id: str, hard_delete: bool = False) -> None:
        if self._async_http is None:
            raise RuntimeError(
                "Async HTTP client not available. "
                "Use AISdk with enable_async=True for async operations."
            )
        await self._async_http.delete(f"/{memory_id}", params={"hardDelete": hard_delete})

    # ------------------------------------------------------------------
    # search / asearch — hybrid NLQ search over the contextMemory index
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        filters: dict[str, builtins.list[str]] | None = None,
        size: int = 15,
        from_: int = 0,
    ) -> MemorySearchResults:
        """Hybrid NLQ search over Context Center memories.

        Args:
            query: Natural-language query string.
            filters: Optional map of field name -> list of values
                (e.g. {"primaryEntityId": ["abc"], "visibility": ["Shared"]}).
            size: Number of results (1-100, default 15).
            from_: Pagination offset.
        """
        params = _build_search_params(query, filters, size, from_)
        response = self._search_http.get("/hybrid/nlq/search", params=params)
        return MemorySearchResults.from_dict(response)

    async def asearch(
        self,
        query: str,
        filters: dict[str, builtins.list[str]] | None = None,
        size: int = 15,
        from_: int = 0,
    ) -> MemorySearchResults:
        if self._search_async_http is None:
            raise RuntimeError(
                "Async HTTP client not available. "
                "Use AISdk with enable_async=True for async operations."
            )
        params = _build_search_params(query, filters, size, from_)
        response = await self._search_async_http.get("/hybrid/nlq/search", params=params)
        return MemorySearchResults.from_dict(response)


# ----------------------------------------------------------------------
# Internal helpers (module-private)
# ----------------------------------------------------------------------


def _build_list_params(
    primary_entity_fqn: str | None,
    after: str | None,
    page_size: int,
) -> dict[str, Any]:
    params: dict[str, Any] = {"limit": page_size}
    if primary_entity_fqn is not None:
        params["primaryEntityFqn"] = primary_entity_fqn
    if after is not None:
        params["after"] = after
    return params


def _build_search_params(
    query: str,
    filters: dict[str, list[str]] | None,
    size: int,
    from_: int,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "q": query,
        "index": "contextMemory",
        "size": size,
        "from": from_,
    }
    if filters:
        params["filters"] = json.dumps(filters)
    return params


def _paginate(
    http: HTTPClient,
    primary_entity_fqn: str | None,
    limit: int | None,
    page_size: int = 100,
) -> list[ContextMemory]:
    results: list[ContextMemory] = []
    after: str | None = None
    while True:
        params = _build_list_params(primary_entity_fqn, after, page_size)
        response = http.get("/", params=params)
        for item in response.get("data", []):
            results.append(ContextMemory.from_dict(item))
            if limit is not None and len(results) >= limit:
                return results[:limit]
        paging = response.get("paging") or {}
        after = paging.get("after")
        if not after:
            break
    return results


async def _apaginate(
    http: AsyncHTTPClient,
    primary_entity_fqn: str | None,
    limit: int | None,
    page_size: int = 100,
) -> list[ContextMemory]:
    results: list[ContextMemory] = []
    after: str | None = None
    while True:
        params = _build_list_params(primary_entity_fqn, after, page_size)
        response = await http.get("/", params=params)
        for item in response.get("data", []):
            results.append(ContextMemory.from_dict(item))
            if limit is not None and len(results) >= limit:
                return results[:limit]
        paging = response.get("paging") or {}
        after = paging.get("after")
        if not after:
            break
    return results
