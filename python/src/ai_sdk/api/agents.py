"""Agents namespace — CRUD for dynamic agents."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_sdk._http import AsyncHTTPClient, HTTPClient

if TYPE_CHECKING:
    from ai_sdk.client import AISdk


class AgentsAPI:
    """Namespace for dynamic agent CRUD operations."""

    def __init__(
        self,
        http: HTTPClient,
        async_http: AsyncHTTPClient | None,
        client: AISdk,
    ) -> None:
        self._http = http
        self._async_http = async_http
        self._client = client
