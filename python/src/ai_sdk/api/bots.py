"""Bots namespace."""

from __future__ import annotations

from ai_sdk._http import AsyncHTTPClient, HTTPClient


class BotsAPI:
    def __init__(self, http: HTTPClient, async_http: AsyncHTTPClient | None) -> None:
        self._http = http
        self._async_http = async_http
