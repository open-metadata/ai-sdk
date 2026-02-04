"""HTTP client internals for the Metadata AI SDK.

This module provides HTTP clients with:
- Automatic retry with exponential backoff
- Request correlation IDs for debugging
- Proper logging integration
- Error handling with specific exceptions
"""

from __future__ import annotations

import json as json_module
import time
import uuid
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx

from metadata_ai._logging import get_logger
from metadata_ai.auth import TokenAuth
from metadata_ai.exceptions import (
    AgentExecutionError,
    AgentNotEnabledError,
    AgentNotFoundError,
    AuthenticationError,
    BotNotFoundError,
    MetadataError,
    RateLimitError,
)

logger = get_logger(__name__)

# Status codes that should trigger retry
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def _generate_request_id() -> str:
    """Generate a unique request ID for correlation."""
    return str(uuid.uuid4())[:8]


def _handle_error(
    response: httpx.Response,
    agent_name: str | None = None,
    bot_name: str | None = None,
    request_id: str | None = None,
) -> None:
    """
    Handle HTTP error responses.

    Args:
        response: The HTTP response
        agent_name: Agent name for error context
        bot_name: Bot name for error context
        request_id: Request ID for correlation

    Raises:
        AuthenticationError: For 401 responses
        AgentNotEnabledError: For 403 responses with agent context
        AgentNotFoundError: For 404 responses with agent context
        BotNotFoundError: For 404 responses with bot context
        RateLimitError: For 429 responses
        AgentExecutionError: For other 4xx/5xx responses
    """
    context = f"[req:{request_id}]" if request_id else ""

    if response.status_code == 401:
        logger.warning("%s Authentication failed", context)
        raise AuthenticationError()

    if response.status_code == 403:
        if agent_name:
            logger.warning("%s Agent not enabled: %s", context, agent_name)
            raise AgentNotEnabledError(agent_name)
        raise MetadataError("Access forbidden", status_code=403)

    if response.status_code == 404:
        if agent_name:
            logger.warning("%s Agent not found: %s", context, agent_name)
            raise AgentNotFoundError(agent_name)
        if bot_name:
            logger.warning("%s Bot not found: %s", context, bot_name)
            raise BotNotFoundError(bot_name)
        raise MetadataError("Resource not found", status_code=404)

    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        retry_seconds = int(retry_after) if retry_after else None
        logger.warning("%s Rate limit exceeded, retry after: %s", context, retry_seconds)
        raise RateLimitError("Rate limit exceeded", retry_after=retry_seconds)

    if response.status_code >= 400:
        # LBYL: Check content-type before parsing JSON
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            error_data = response.json()
            message = error_data.get("message", response.text)
        else:
            message = response.text

        logger.error(
            "%s API error (%d): %s",
            context,
            response.status_code,
            message[:200],
        )
        raise AgentExecutionError(
            f"API error ({response.status_code}): {message}",
            agent_name=agent_name,
        )


class HTTPClient:
    """
    HTTP client for API communication with retry support.

    Features:
    - Automatic retry with exponential backoff
    - Request correlation IDs
    - Proper logging
    - Connection pooling via httpx
    """

    def __init__(
        self,
        base_url: str,
        auth: TokenAuth,
        timeout: float = 120.0,
        verify_ssl: bool = True,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        user_agent: str | None = None,
    ):
        """
        Initialize the HTTP client.

        Args:
            base_url: Base URL for API requests
            auth: Authentication handler
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries (exponential backoff)
            user_agent: Custom User-Agent string
        """
        self._base_url = base_url.rstrip("/")
        self._auth = auth
        self._timeout = timeout
        self._verify_ssl = verify_ssl
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._user_agent = user_agent or "metadata-ai-sdk/0.1.0"

        self._client = httpx.Client(
            base_url=self._base_url,
            timeout=timeout,
            verify=verify_ssl,
        )

        logger.debug("HTTPClient initialized for %s", self._base_url)

    def _headers(self, request_id: str | None = None) -> dict[str, str]:
        """Get request headers."""
        headers = self._auth.get_headers()
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"
        headers["User-Agent"] = self._user_agent
        if request_id:
            headers["X-Request-ID"] = request_id
        return headers

    def _should_retry(self, response: httpx.Response, attempt: int) -> bool:
        """Check if request should be retried."""
        if attempt >= self._max_retries:
            return False
        return response.status_code in RETRYABLE_STATUS_CODES

    def _wait_for_retry(self, attempt: int, response: httpx.Response) -> None:
        """Wait before retrying with exponential backoff."""
        # Check for Retry-After header
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            # LBYL: Check if it's a valid number before converting
            if retry_after.replace(".", "", 1).isdigit():
                delay = float(retry_after)
            else:
                delay = self._retry_delay * (2**attempt)
        else:
            delay = self._retry_delay * (2**attempt)

        logger.debug("Retry attempt %d, waiting %.2fs", attempt + 1, delay)
        time.sleep(delay)

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        agent_name: str | None = None,
        bot_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Make a GET request with retry support.

        Args:
            path: Request path
            params: Query parameters
            agent_name: Agent name for error context
            bot_name: Bot name for error context

        Returns:
            Response JSON data
        """
        request_id = _generate_request_id()
        logger.debug("[req:%s] GET %s%s", request_id, self._base_url, path)

        last_response = None
        for attempt in range(self._max_retries + 1):
            response = self._client.get(
                path,
                headers=self._headers(request_id),
                params=params,
            )
            last_response = response

            if response.status_code < 400:
                return response.json()

            if self._should_retry(response, attempt):
                self._wait_for_retry(attempt, response)
                continue

            break

        assert last_response is not None  # Loop always runs at least once
        _handle_error(last_response, agent_name=agent_name, bot_name=bot_name, request_id=request_id)
        return {}  # Never reached, _handle_error always raises

    def post(
        self,
        path: str,
        json: dict[str, Any],
        agent_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Make a POST request with retry support.

        Args:
            path: Request path
            json: Request body
            agent_name: Agent name for error context

        Returns:
            Response JSON data
        """
        request_id = _generate_request_id()
        logger.debug("[req:%s] POST %s%s", request_id, self._base_url, path)
        logger.debug("[req:%s] Request body: %s", request_id, json_module.dumps(json, indent=2))

        last_response = None
        for attempt in range(self._max_retries + 1):
            response = self._client.post(
                path,
                headers=self._headers(request_id),
                json=json,
            )
            last_response = response

            if response.status_code < 400:
                result = response.json()
                logger.debug(
                    "[req:%s] Response status: %d",
                    request_id,
                    response.status_code,
                )
                return result

            if self._should_retry(response, attempt):
                self._wait_for_retry(attempt, response)
                continue

            break

        assert last_response is not None  # Loop always runs at least once
        _handle_error(last_response, agent_name=agent_name, request_id=request_id)
        return {}  # Never reached

    def post_stream(
        self,
        path: str,
        json: dict[str, Any],
        agent_name: str | None = None,
    ) -> Iterator[bytes]:
        """
        Make a streaming POST request.

        Note: Streaming requests don't support automatic retry.

        Args:
            path: Request path
            json: Request body
            agent_name: Agent name for error context

        Yields:
            Response chunks as bytes
        """
        request_id = _generate_request_id()
        logger.debug("[req:%s] POST (stream) %s%s", request_id, self._base_url, path)

        headers = self._auth.get_headers()
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "text/event-stream"
        headers["User-Agent"] = self._user_agent
        headers["X-Request-ID"] = request_id

        with self._client.stream(
            "POST",
            path,
            headers=headers,
            json=json,
        ) as response:
            # Check for errors before streaming
            if response.status_code >= 400:
                response.read()
                _handle_error(response, agent_name=agent_name, request_id=request_id)

            yield from response.iter_bytes()

    def close(self) -> None:
        """Close the HTTP client."""
        logger.debug("Closing HTTPClient")
        self._client.close()

    def __enter__(self) -> HTTPClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class AsyncHTTPClient:
    """
    Async HTTP client for API communication with retry support.

    Features:
    - Automatic retry with exponential backoff
    - Request correlation IDs
    - Proper logging
    - Lazy client initialization
    """

    def __init__(
        self,
        base_url: str,
        auth: TokenAuth,
        timeout: float = 120.0,
        verify_ssl: bool = True,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        user_agent: str | None = None,
    ):
        """
        Initialize the async HTTP client.

        Args:
            base_url: Base URL for API requests
            auth: Authentication handler
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries
            user_agent: Custom User-Agent string
        """
        self._base_url = base_url.rstrip("/")
        self._auth = auth
        self._timeout = timeout
        self._verify_ssl = verify_ssl
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._user_agent = user_agent or "metadata-ai-sdk/0.1.0"
        self._client: httpx.AsyncClient | None = None

        logger.debug("AsyncHTTPClient initialized for %s", self._base_url)

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                verify=self._verify_ssl,
            )
        return self._client

    def _headers(self, request_id: str | None = None) -> dict[str, str]:
        """Get request headers."""
        headers = self._auth.get_headers()
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"
        headers["User-Agent"] = self._user_agent
        if request_id:
            headers["X-Request-ID"] = request_id
        return headers

    def _should_retry(self, response: httpx.Response, attempt: int) -> bool:
        """Check if request should be retried."""
        if attempt >= self._max_retries:
            return False
        return response.status_code in RETRYABLE_STATUS_CODES

    async def _wait_for_retry(self, attempt: int, response: httpx.Response) -> None:
        """Wait before retrying with exponential backoff."""
        import asyncio

        retry_after = response.headers.get("Retry-After")
        if retry_after:
            # LBYL: Check if it's a valid number before converting
            if retry_after.replace(".", "", 1).isdigit():
                delay = float(retry_after)
            else:
                delay = self._retry_delay * (2**attempt)
        else:
            delay = self._retry_delay * (2**attempt)

        logger.debug("Async retry attempt %d, waiting %.2fs", attempt + 1, delay)
        await asyncio.sleep(delay)

    async def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        agent_name: str | None = None,
        bot_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Make an async GET request with retry support.

        Args:
            path: Request path
            params: Query parameters
            agent_name: Agent name for error context
            bot_name: Bot name for error context

        Returns:
            Response JSON data
        """
        request_id = _generate_request_id()
        logger.debug("[req:%s] async GET %s%s", request_id, self._base_url, path)

        client = self._get_client()
        last_response = None

        for attempt in range(self._max_retries + 1):
            response = await client.get(
                path,
                headers=self._headers(request_id),
                params=params,
            )
            last_response = response

            if response.status_code < 400:
                return response.json()

            if self._should_retry(response, attempt):
                await self._wait_for_retry(attempt, response)
                continue

            break

        assert last_response is not None  # Loop always runs at least once
        _handle_error(last_response, agent_name=agent_name, bot_name=bot_name, request_id=request_id)
        return {}  # Never reached

    async def post(
        self,
        path: str,
        json: dict[str, Any],
        agent_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Make an async POST request with retry support.

        Args:
            path: Request path
            json: Request body
            agent_name: Agent name for error context

        Returns:
            Response JSON data
        """
        request_id = _generate_request_id()
        logger.debug("[req:%s] async POST %s%s", request_id, self._base_url, path)

        client = self._get_client()
        last_response = None

        for attempt in range(self._max_retries + 1):
            response = await client.post(
                path,
                headers=self._headers(request_id),
                json=json,
            )
            last_response = response

            if response.status_code < 400:
                return response.json()

            if self._should_retry(response, attempt):
                await self._wait_for_retry(attempt, response)
                continue

            break

        assert last_response is not None  # Loop always runs at least once
        _handle_error(last_response, agent_name=agent_name, request_id=request_id)
        return {}  # Never reached

    async def post_stream(
        self,
        path: str,
        json: dict[str, Any],
        agent_name: str | None = None,
    ) -> AsyncIterator[bytes]:
        """
        Make an async streaming POST request.

        Note: Streaming requests don't support automatic retry.

        Args:
            path: Request path
            json: Request body
            agent_name: Agent name for error context

        Yields:
            Response chunks as bytes
        """
        request_id = _generate_request_id()
        logger.debug("[req:%s] async POST (stream) %s%s", request_id, self._base_url, path)

        headers = self._auth.get_headers()
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "text/event-stream"
        headers["User-Agent"] = self._user_agent
        headers["X-Request-ID"] = request_id

        client = self._get_client()
        async with client.stream(
            "POST",
            path,
            headers=headers,
            json=json,
        ) as response:
            # Check for errors before streaming
            if response.status_code >= 400:
                await response.aread()
                _handle_error(response, agent_name=agent_name, request_id=request_id)

            async for chunk in response.aiter_bytes():
                yield chunk

    async def close(self) -> None:
        """Close the async HTTP client."""
        logger.debug("Closing AsyncHTTPClient")
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> AsyncHTTPClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
