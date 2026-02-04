"""Tests for the Metadata AI SDK client."""

import pytest
from pytest_httpx import HTTPXMock

from metadata_ai.agent import AgentHandle
from metadata_ai.client import MetadataAI
from metadata_ai.models import AgentInfo


@pytest.fixture
def client():
    """MetadataAI client fixture."""
    c = MetadataAI(
        host="https://metadata.example.com",
        token="test-jwt-token",
    )
    yield c
    c.close()


class TestMetadataAIInit:
    """Tests for MetadataAI initialization."""

    def test_strips_trailing_slash(self):
        """Client strips trailing slash from host."""
        client = MetadataAI(
            host="https://metadata.example.com/",
            token="jwt-token",
        )
        assert client.host == "https://metadata.example.com"
        client.close()


class TestMetadataAIAgent:
    """Tests for MetadataAI.agent() method."""

    def test_returns_agent_handle(self, client):
        """agent() returns AgentHandle with correct name."""
        handle = client.agent("DataQualityAgent")

        assert isinstance(handle, AgentHandle)
        assert handle.name == "DataQualityAgent"


class TestMetadataAIListAgents:
    """Tests for MetadataAI.list_agents() method."""

    def test_list_agents_returns_agent_info(
        self, client, httpx_mock: HTTPXMock, sample_agents_list_response
    ):
        """list_agents returns list of AgentInfo objects."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/api/agents/?limit=10&offset=0",
            json=sample_agents_list_response,
        )

        agents = client.list_agents()

        assert len(agents) == 2
        assert all(isinstance(a, AgentInfo) for a in agents)
        assert agents[0].name == "DataQualityPlannerAgent"
        assert agents[1].name == "SqlQueryAgent"

    def test_list_agents_pagination(self, client, httpx_mock: HTTPXMock):
        """list_agents passes pagination params to API."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/api/agents/?limit=5&offset=10",
            json={"data": []},
        )

        client.list_agents(limit=5, offset=10)

        request = httpx_mock.get_request()
        assert "limit=5" in str(request.url)
        assert "offset=10" in str(request.url)


class TestMetadataAIContextManager:
    """Tests for MetadataAI context manager."""

    def test_context_manager_works(self):
        """Client works as context manager."""
        with MetadataAI(host="https://example.com", token="token") as client:
            assert isinstance(client, MetadataAI)
