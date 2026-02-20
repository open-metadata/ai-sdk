"""Tests for the AI SDK HTTP client."""

import pytest
from pytest_httpx import HTTPXMock

from ai_sdk._http import HTTPClient
from ai_sdk.auth import TokenAuth
from ai_sdk.exceptions import (
    AgentExecutionError,
    AgentNotEnabledError,
    AgentNotFoundError,
    AuthenticationError,
    RateLimitError,
)


@pytest.fixture
def auth():
    """Token auth fixture."""
    return TokenAuth("test-jwt-token")


@pytest.fixture
def http_client(auth):
    """HTTP client fixture with retries disabled for predictable error testing."""
    client = HTTPClient(
        base_url="https://api.example.com/v1/api/agents",
        auth=auth,
        timeout=30.0,
        max_retries=0,
    )
    yield client
    client.close()


@pytest.fixture
def http_client_with_retries(auth):
    """HTTP client fixture with retries enabled."""
    client = HTTPClient(
        base_url="https://api.example.com/v1/api/agents",
        auth=auth,
        timeout=30.0,
        max_retries=2,
        retry_delay=0.01,
    )
    yield client
    client.close()


class TestHTTPClientRequests:
    """Tests for HTTPClient GET and POST requests."""

    def test_get_returns_json(self, http_client, httpx_mock: HTTPXMock):
        """GET returns JSON response."""
        httpx_mock.add_response(
            url="https://api.example.com/v1/api/agents/TestAgent",
            json={"name": "TestAgent", "apiEnabled": True},
        )

        result = http_client.get("/TestAgent")

        assert result["name"] == "TestAgent"

    def test_get_sends_auth_header(self, http_client, httpx_mock: HTTPXMock):
        """GET includes Authorization header."""
        httpx_mock.add_response(url="https://api.example.com/v1/api/agents/test", json={})

        http_client.get("/test")

        request = httpx_mock.get_request()
        assert request.headers["Authorization"] == "Bearer test-jwt-token"

    def test_post_returns_json(self, http_client, httpx_mock: HTTPXMock):
        """POST returns JSON response."""
        httpx_mock.add_response(
            url="https://api.example.com/v1/api/agents/TestAgent/invoke",
            json={"conversationId": "conv-123", "response": "Hello!"},
        )

        result = http_client.post(
            "/TestAgent/invoke", json={"message": "Hi"}, agent_name="TestAgent"
        )

        assert result["response"] == "Hello!"


class TestHTTPClientErrorHandling:
    """Tests for HTTPClient error handling."""

    def test_401_raises_authentication_error(self, http_client, httpx_mock: HTTPXMock):
        """401 raises AuthenticationError."""
        httpx_mock.add_response(
            url="https://api.example.com/v1/api/agents/test/invoke",
            status_code=401,
        )

        with pytest.raises(AuthenticationError):
            http_client.post("/test/invoke", json={})

    def test_403_with_agent_raises_not_enabled_error(self, http_client, httpx_mock: HTTPXMock):
        """403 with agent_name raises AgentNotEnabledError."""
        httpx_mock.add_response(
            url="https://api.example.com/v1/api/agents/InternalAgent/invoke",
            status_code=403,
        )

        with pytest.raises(AgentNotEnabledError) as exc_info:
            http_client.post("/InternalAgent/invoke", json={}, agent_name="InternalAgent")

        assert exc_info.value.agent_name == "InternalAgent"

    def test_404_with_agent_raises_not_found_error(self, http_client, httpx_mock: HTTPXMock):
        """404 with agent_name raises AgentNotFoundError."""
        httpx_mock.add_response(
            url="https://api.example.com/v1/api/agents/MissingAgent/invoke",
            status_code=404,
        )

        with pytest.raises(AgentNotFoundError) as exc_info:
            http_client.post("/MissingAgent/invoke", json={}, agent_name="MissingAgent")

        assert exc_info.value.agent_name == "MissingAgent"

    def test_429_raises_rate_limit_error_with_retry_after(self, http_client, httpx_mock: HTTPXMock):
        """429 raises RateLimitError with retry_after from header."""
        httpx_mock.add_response(
            url="https://api.example.com/v1/api/agents/test/invoke",
            status_code=429,
            headers={"Retry-After": "60"},
        )

        with pytest.raises(RateLimitError) as exc_info:
            http_client.post("/test/invoke", json={})

        assert exc_info.value.retry_after == 60

    def test_500_raises_execution_error(self, http_client, httpx_mock: HTTPXMock):
        """500 raises AgentExecutionError with message from response."""
        httpx_mock.add_response(
            url="https://api.example.com/v1/api/agents/test/invoke",
            status_code=500,
            json={"message": "Internal error"},
        )

        with pytest.raises(AgentExecutionError) as exc_info:
            http_client.post("/test/invoke", json={})

        assert "Internal error" in str(exc_info.value)

    def test_500_plain_text_error(self, http_client, httpx_mock: HTTPXMock):
        """500 with non-JSON response includes response text."""
        httpx_mock.add_response(
            url="https://api.example.com/v1/api/agents/test/invoke",
            status_code=500,
            text="Server Error",
        )

        with pytest.raises(AgentExecutionError) as exc_info:
            http_client.post("/test/invoke", json={})

        assert "Server Error" in str(exc_info.value)


class TestHTTPClientStreaming:
    """Tests for HTTPClient streaming."""

    def test_post_stream_yields_chunks(self, http_client, httpx_mock: HTTPXMock):
        """post_stream yields response chunks with correct Accept header."""
        httpx_mock.add_response(
            url="https://api.example.com/v1/api/agents/test/stream",
            content=b'event: message\ndata: {"content": "Hello"}\n\n',
        )

        chunks = list(http_client.post_stream("/test/stream", json={}))

        assert b"Hello" in b"".join(chunks)
        request = httpx_mock.get_request()
        assert request.headers["Accept"] == "text/event-stream"


class TestHTTPClientRetry:
    """Tests for HTTPClient retry behavior."""

    def test_retries_on_transient_errors(self, http_client_with_retries, httpx_mock: HTTPXMock):
        """Retries on 429, 500, 502, 503, 504 and succeeds."""
        httpx_mock.add_response(
            url="https://api.example.com/v1/api/agents/test/invoke",
            status_code=500,
        )
        httpx_mock.add_response(
            url="https://api.example.com/v1/api/agents/test/invoke",
            json={"response": "Success after retry"},
        )

        result = http_client_with_retries.post("/test/invoke", json={})

        assert result["response"] == "Success after retry"
        assert len(httpx_mock.get_requests()) == 2

    def test_no_retry_on_client_errors(self, http_client_with_retries, httpx_mock: HTTPXMock):
        """Does not retry on 401, 403, 404 (client errors)."""
        httpx_mock.add_response(
            url="https://api.example.com/v1/api/agents/test/invoke",
            status_code=401,
        )

        with pytest.raises(AuthenticationError):
            http_client_with_retries.post("/test/invoke", json={})

        assert len(httpx_mock.get_requests()) == 1

    def test_exhausts_retries_then_raises(self, http_client_with_retries, httpx_mock: HTTPXMock):
        """Raises after exhausting all retries."""
        for _ in range(3):
            httpx_mock.add_response(
                url="https://api.example.com/v1/api/agents/test/invoke",
                status_code=500,
                json={"message": "Persistent error"},
            )

        with pytest.raises(AgentExecutionError) as exc_info:
            http_client_with_retries.post("/test/invoke", json={})

        assert "Persistent error" in str(exc_info.value)
        assert len(httpx_mock.get_requests()) == 3

    def test_includes_request_id_header(self, http_client_with_retries, httpx_mock: HTTPXMock):
        """Requests include X-Request-ID header for correlation."""
        httpx_mock.add_response(url="https://api.example.com/v1/api/agents/test", json={})

        http_client_with_retries.get("/test")

        request = httpx_mock.get_request()
        assert "X-Request-ID" in request.headers
        assert len(request.headers["X-Request-ID"]) == 8
