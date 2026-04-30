"""Agents namespace — CRUD for dynamic agents."""

from __future__ import annotations

import builtins
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from ai_sdk._http import AsyncHTTPClient, HTTPClient
from ai_sdk.models import AgentInfo, CreateAgentRequest

if TYPE_CHECKING:
    from ai_sdk.client import AISdk


_AgentInfoList = builtins.list[AgentInfo]


class AgentsAPI:
    """Namespace for dynamic agent CRUD operations.

    Holds a back-reference to AISdk so that create() can resolve the
    persona/ability names to entity references via the personas/abilities
    namespaces.
    """

    def __init__(
        self,
        http: HTTPClient,
        async_http: AsyncHTTPClient | None,
        client: AISdk,
    ) -> None:
        self._http = http
        self._async_http = async_http
        self._client = client

    def list(self, limit: int | None = None) -> _AgentInfoList:
        """List all API-enabled dynamic agents."""
        return _paginate(
            self._http,
            "/",
            AgentInfo.from_dict,
            limit=limit,
            extra_params={"apiEnabled": "true"},
        )

    async def alist(self, limit: int | None = None) -> _AgentInfoList:
        if self._async_http is None:
            raise RuntimeError(
                "Async HTTP client not available. "
                "Use AISdk with enable_async=True for async operations."
            )
        return await _apaginate(
            self._async_http,
            "/",
            AgentInfo.from_dict,
            limit=limit,
            extra_params={"apiEnabled": "true"},
        )

    def create(self, request: CreateAgentRequest) -> AgentInfo:
        """Create a new dynamic agent."""
        persona = self._client.personas.get(request.persona)
        api_dict = request.to_api_dict()
        api_dict["persona"] = {"id": persona.id, "type": "persona"}
        if request.abilities:
            ability_refs = []
            for ability_name in request.abilities:
                ability_info = self._client.abilities.get(ability_name)
                ability_refs.append({"id": ability_info.id, "type": "ability"})
            api_dict["abilities"] = ability_refs
        response = self._http.post("/", json=api_dict)
        return AgentInfo.from_dict(response)

    async def acreate(self, request: CreateAgentRequest) -> AgentInfo:
        if self._async_http is None:
            raise RuntimeError(
                "Async HTTP client not available. "
                "Use AISdk with enable_async=True for async operations."
            )
        persona = await self._client.personas.aget(request.persona)
        api_dict = request.to_api_dict()
        api_dict["persona"] = {"id": persona.id, "type": "persona"}
        if request.abilities:
            ability_refs = []
            for ability_name in request.abilities:
                ability_info = await self._client.abilities.aget(ability_name)
                ability_refs.append({"id": ability_info.id, "type": "ability"})
            api_dict["abilities"] = ability_refs
        response = await self._async_http.post("/", json=api_dict)
        return AgentInfo.from_dict(response)


def _paginate(
    http: HTTPClient,
    path: str,
    mapper: Callable[[dict[str, Any]], Any],
    limit: int | None = None,
    page_size: int = 100,
    extra_params: dict[str, Any] | None = None,
) -> builtins.list:
    results: builtins.list = []
    after: str | None = None
    while True:
        params: dict[str, Any] = {"limit": page_size}
        if extra_params:
            params.update(extra_params)
        if after:
            params["after"] = after
        response = http.get(path, params=params)
        for item in response.get("data", []):
            results.append(mapper(item))
            if limit is not None and len(results) >= limit:
                return results[:limit]
        paging = response.get("paging") or {}
        after = paging.get("after")
        if not after:
            break
    return results


async def _apaginate(
    http: AsyncHTTPClient,
    path: str,
    mapper: Callable[[dict[str, Any]], Any],
    limit: int | None = None,
    page_size: int = 100,
    extra_params: dict[str, Any] | None = None,
) -> builtins.list:
    results: builtins.list = []
    after: str | None = None
    while True:
        params: dict[str, Any] = {"limit": page_size}
        if extra_params:
            params.update(extra_params)
        if after:
            params["after"] = after
        response = await http.get(path, params=params)
        for item in response.get("data", []):
            results.append(mapper(item))
            if limit is not None and len(results) >= limit:
                return results[:limit]
        paging = response.get("paging") or {}
        after = paging.get("after")
        if not after:
            break
    return results
