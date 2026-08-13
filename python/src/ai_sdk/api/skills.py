"""Skills namespace."""

from __future__ import annotations

import builtins
from collections.abc import Callable
from typing import Any
from urllib.parse import quote

from ai_sdk._http import AsyncHTTPClient, HTTPClient
from ai_sdk.exceptions import AISdkError, SkillNotFoundError
from ai_sdk.models import SkillInfo

_SkillInfoList = builtins.list[SkillInfo]


class SkillsAPI:
    """Namespace for skill operations."""

    def __init__(self, http: HTTPClient, async_http: AsyncHTTPClient | None) -> None:
        self._http = http
        self._async_http = async_http

    def list(self, limit: int | None = None) -> _SkillInfoList:
        return _paginate(self._http, "/", SkillInfo.from_dict, limit=limit)

    async def alist(self, limit: int | None = None) -> _SkillInfoList:
        if self._async_http is None:
            raise RuntimeError(
                "Async HTTP client not available. "
                "Use AISdk with enable_async=True for async operations."
            )
        return await _apaginate(self._async_http, "/", SkillInfo.from_dict, limit=limit)

    def get(self, name: str) -> SkillInfo:
        try:
            encoded_name = quote(name, safe="")
            response = self._http.get(f"/name/{encoded_name}")
            return SkillInfo.from_dict(response)
        except AISdkError as e:
            if e.status_code == 404:
                raise SkillNotFoundError(name) from e
            raise

    async def aget(self, name: str) -> SkillInfo:
        if self._async_http is None:
            raise RuntimeError(
                "Async HTTP client not available. "
                "Use AISdk with enable_async=True for async operations."
            )
        try:
            encoded_name = quote(name, safe="")
            response = await self._async_http.get(f"/name/{encoded_name}")
            return SkillInfo.from_dict(response)
        except AISdkError as e:
            if e.status_code == 404:
                raise SkillNotFoundError(name) from e
            raise


def _paginate(
    http: HTTPClient,
    path: str,
    mapper: Callable[[dict[str, Any]], Any],
    limit: int | None = None,
    page_size: int = 100,
) -> builtins.list:
    results: builtins.list = []
    after: str | None = None
    while True:
        params: dict[str, Any] = {"limit": page_size}
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
) -> builtins.list:
    results: builtins.list = []
    after: str | None = None
    while True:
        params: dict[str, Any] = {"limit": page_size}
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
