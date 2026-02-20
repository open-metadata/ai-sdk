"""Tests for the AI SDK client."""

import pytest
from pytest_httpx import HTTPXMock

from ai_sdk.agent import AgentHandle
from ai_sdk.client import AiSdk
from ai_sdk.models import AgentInfo


@pytest.fixture
def client():
    """AiSdk client fixture."""
    c = AiSdk(
        host="https://metadata.example.com",
        token="test-jwt-token",
    )
    yield c
    c.close()


class TestAiSdkInit:
    """Tests for AiSdk initialization."""

    def test_strips_trailing_slash(self):
        """Client strips trailing slash from host."""
        client = AiSdk(
            host="https://metadata.example.com/",
            token="jwt-token",
        )
        assert client.host == "https://metadata.example.com"
        client.close()


class TestAiSdkAgent:
    """Tests for AiSdk.agent() method."""

    def test_returns_agent_handle(self, client):
        """agent() returns AgentHandle with correct name."""
        handle = client.agent("DataQualityAgent")

        assert isinstance(handle, AgentHandle)
        assert handle.name == "DataQualityAgent"


class TestAiSdkListAgents:
    """Tests for AiSdk.list_agents() method."""

    def test_list_agents_returns_agent_info(
        self, client, httpx_mock: HTTPXMock, sample_agents_list_response
    ):
        """list_agents returns list of AgentInfo objects."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/?apiEnabled=true&limit=100",
            json=sample_agents_list_response,
        )

        agents = client.list_agents()

        assert len(agents) == 2
        assert all(isinstance(a, AgentInfo) for a in agents)
        assert agents[0].name == "DataQualityPlannerAgent"
        assert agents[1].name == "SqlQueryAgent"

    def test_list_agents_with_limit(
        self, client, httpx_mock: HTTPXMock, sample_agents_list_response
    ):
        """list_agents respects user limit parameter."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/?apiEnabled=true&limit=100",
            json=sample_agents_list_response,
        )

        # Request only 1 agent, even though API returns 2
        agents = client.list_agents(limit=1)

        assert len(agents) == 1
        assert agents[0].name == "DataQualityPlannerAgent"


class TestAiSdkContextManager:
    """Tests for AiSdk context manager."""

    def test_context_manager_works(self):
        """Client works as context manager."""
        with AiSdk(host="https://example.com", token="token") as client:
            assert isinstance(client, AiSdk)
