"""Tests for the Metadata AI SDK async functionality."""

import json

import pytest
from pytest_httpx import HTTPXMock

from metadata_ai._http import AsyncHTTPClient
from metadata_ai._streaming import AsyncSSEIterator
from metadata_ai.auth import TokenAuth
from metadata_ai.client import MetadataAI
from metadata_ai.exceptions import AuthenticationError
from metadata_ai.models import AgentInfo, InvokeResponse


@pytest.fixture
def auth():
    """Token auth fixture."""
    return TokenAuth("test-jwt-token")


@pytest.fixture
def async_client():
    """Async MetadataAI client fixture."""
    c = MetadataAI(
        host="https://metadata.example.com",
        token="test-jwt-token",
        enable_async=True,
    )
    yield c
    c.close()


class TestAsyncHTTPClient:
    """Tests for AsyncHTTPClient."""

    @pytest.mark.asyncio
    async def test_get_returns_json(self, auth, httpx_mock: HTTPXMock):
        """Async GET returns JSON response."""
        httpx_mock.add_response(
            url="https://api.example.com/test",
            json={"name": "TestAgent"},
        )

        async with AsyncHTTPClient(base_url="https://api.example.com", auth=auth) as client:
            result = await client.get("/test")
            assert result["name"] == "TestAgent"

    @pytest.mark.asyncio
    async def test_post_returns_json(self, auth, httpx_mock: HTTPXMock):
        """Async POST returns JSON response."""
        httpx_mock.add_response(
            url="https://api.example.com/invoke",
            json={"conversationId": "conv-1", "response": "OK"},
        )

        async with AsyncHTTPClient(base_url="https://api.example.com", auth=auth) as client:
            result = await client.post("/invoke", json={"message": "test"})
            assert result["response"] == "OK"

    @pytest.mark.asyncio
    async def test_401_raises_authentication_error(self, auth, httpx_mock: HTTPXMock):
        """Async request raises AuthenticationError on 401."""
        httpx_mock.add_response(url="https://api.example.com/test", status_code=401)

        async with AsyncHTTPClient(base_url="https://api.example.com", auth=auth) as client:
            with pytest.raises(AuthenticationError):
                await client.get("/test")


class TestAsyncAgentCall:
    """Tests for async agent call."""

    @pytest.mark.asyncio
    async def test_acall_returns_invoke_response(
        self, async_client, httpx_mock: HTTPXMock, sample_invoke_response_dict
    ):
        """acall returns InvokeResponse."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/TestAgent/invoke",
            json=sample_invoke_response_dict,
        )

        agent = async_client.agent("TestAgent")
        response = await agent.acall("Test query")

        assert isinstance(response, InvokeResponse)
        assert response.conversation_id == "550e8400-e29b-41d4-a716-446655440000"

    @pytest.mark.asyncio
    async def test_acall_without_async_raises(self):
        """acall without async client raises RuntimeError."""
        client = MetadataAI(host="https://example.com", token="token", enable_async=False)
        try:
            agent = client.agent("TestAgent")
            with pytest.raises(RuntimeError, match="enable_async=True"):
                await agent.acall("Test")
        finally:
            client.close()

    @pytest.mark.asyncio
    async def test_acall_sends_conversation_id(self, async_client, httpx_mock: HTTPXMock):
        """acall sends conversation_id in request."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/TestAgent/invoke",
            json={"conversationId": "existing-conv", "response": "OK"},
        )

        agent = async_client.agent("TestAgent")
        await agent.acall("Continue", conversation_id="existing-conv")

        request = httpx_mock.get_request()
        body = json.loads(request.content)
        assert body["conversationId"] == "existing-conv"


class TestAsyncAgentGetInfo:
    """Tests for async agent get_info."""

    @pytest.mark.asyncio
    async def test_aget_info_returns_agent_info(
        self, async_client, httpx_mock: HTTPXMock, sample_agent_info_dict
    ):
        """aget_info returns AgentInfo."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/TestAgent",
            json=sample_agent_info_dict,
        )

        agent = async_client.agent("TestAgent")
        info = await agent.aget_info()

        assert isinstance(info, AgentInfo)
        assert info.name == "DataQualityPlannerAgent"


class TestAsyncListAgents:
    """Tests for async list_agents."""

    @pytest.mark.asyncio
    async def test_alist_agents_returns_list(
        self, async_client, httpx_mock: HTTPXMock, sample_agents_list_response
    ):
        """alist_agents returns list of AgentInfo."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/?apiEnabled=true&limit=100",
            json=sample_agents_list_response,
        )

        agents = await async_client.alist_agents()

        assert len(agents) == 2
        assert all(isinstance(a, AgentInfo) for a in agents)


class TestAsyncSSEIterator:
    """Tests for AsyncSSEIterator."""

    @pytest.mark.asyncio
    async def test_parses_events(self):
        """AsyncSSEIterator parses SSE events."""

        async def mock_stream():
            yield b'event: stream-start\ndata: {"conversationId": "conv-1"}\n\n'
            yield b'event: message\ndata: {"content": "Hello"}\n\n'
            yield b"event: stream-completed\ndata: {}\n\n"

        events = [event async for event in AsyncSSEIterator(mock_stream())]

        assert len(events) == 3
        assert events[0].type == "start"
        assert events[0].conversation_id == "conv-1"
        assert events[1].type == "content"
        assert events[1].content == "Hello"
        assert events[2].type == "end"

    @pytest.mark.asyncio
    async def test_handles_chunked_stream(self):
        """AsyncSSEIterator handles chunked data."""

        async def mock_stream():
            yield b"event: mes"
            yield b'sage\ndata: {"con'
            yield b'tent": "Chunked"}\n\n'

        events = [event async for event in AsyncSSEIterator(mock_stream())]

        assert len(events) == 1
        assert events[0].content == "Chunked"


langchain_core = pytest.importorskip("langchain_core")


class TestAsyncLangChainIntegration:
    """Tests for async LangChain integration."""

    @pytest.mark.asyncio
    async def test_arun_uses_acall(self, async_client, httpx_mock: HTTPXMock):
        """LangChain _arun uses acall with async client."""
        from metadata_ai.integrations.langchain import MetadataAgentTool

        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/TestAgent",
            json={
                "name": "TestAgent",
                "displayName": "Test Agent",
                "description": "Test agent",
                "abilities": [],
                "apiEnabled": True,
            },
        )
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/TestAgent/invoke",
            json={"conversationId": "conv-async", "response": "Async response"},
        )

        tool = MetadataAgentTool.from_client(async_client, "TestAgent")
        result = await tool._arun("Test query")

        assert result == "Async response"
        assert tool._conversation_id == "conv-async"
