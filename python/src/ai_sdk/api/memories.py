"""Memories namespace — CRUD + hybrid search for Context Center memories."""

from __future__ import annotations

from ai_sdk._http import AsyncHTTPClient, HTTPClient


class MemoriesAPI:
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
