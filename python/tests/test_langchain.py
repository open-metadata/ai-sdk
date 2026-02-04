"""Tests for the Metadata AI SDK LangChain integration."""

import json

import pytest
from pytest_httpx import HTTPXMock

from metadata_ai.client import MetadataAI

pytest.importorskip("langchain_core")

from metadata_ai.integrations.langchain import (
    MetadataAgentTool,
    create_metadata_tools,
)


@pytest.fixture
def client():
    """MetadataAI client fixture with retries disabled for testing."""
    c = MetadataAI(
        host="https://metadata.example.com",
        token="test-jwt-token",
        max_retries=0,
    )
    yield c
    c.close()


@pytest.fixture
def mock_agent_info(httpx_mock: HTTPXMock):
    """Mock agent info endpoint."""
    httpx_mock.add_response(
        url="https://metadata.example.com/api/v1/api/agents/DataQualityAgent",
        json={
            "name": "DataQualityAgent",
            "displayName": "Data Quality Agent",
            "description": "Analyzes data quality issues in tables",
            "abilities": ["search_metadata", "analyze_quality"],
            "apiEnabled": True,
        },
    )


@pytest.fixture
def mock_agent_invoke(httpx_mock: HTTPXMock):
    """Mock agent invoke endpoint."""
    httpx_mock.add_response(
        url="https://metadata.example.com/api/v1/api/agents/DataQualityAgent/invoke",
        json={
            "conversationId": "conv-123",
            "response": "Found 3 data quality issues in the customers table.",
            "toolsUsed": ["search_metadata"],
        },
    )


class TestMetadataAgentToolInit:
    """Tests for MetadataAgentTool initialization."""

    def test_from_client_creates_tool_with_auto_description(self, client, mock_agent_info):
        """from_client creates tool with name and auto-generated description."""
        tool = MetadataAgentTool.from_client(client, "DataQualityAgent")

        assert tool.name == "metadata_DataQualityAgent"
        assert "data quality" in tool.description.lower()
        assert "search_metadata" in tool.description
        assert "analyze_quality" in tool.description

    def test_from_client_accepts_custom_name_and_description(self, client, mock_agent_info):
        """from_client accepts custom name and description."""
        tool = MetadataAgentTool.from_client(
            client,
            "DataQualityAgent",
            name="my_custom_tool",
            description="My custom description",
        )

        assert tool.name == "my_custom_tool"
        assert tool.description == "My custom description"

    def test_fallback_when_get_info_fails(self, client, httpx_mock: HTTPXMock):
        """Tool uses fallback when get_info fails."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/api/agents/UnknownAgent",
            status_code=500,
        )

        tool = MetadataAgentTool.from_client(client, "UnknownAgent")

        assert tool.name == "metadata_UnknownAgent"
        assert "UnknownAgent" in tool.description


class TestMetadataAgentToolRun:
    """Tests for MetadataAgentTool._run() method."""

    def test_run_invokes_agent_and_returns_response(
        self, client, mock_agent_info, mock_agent_invoke
    ):
        """_run invokes agent and returns response text."""
        tool = MetadataAgentTool.from_client(client, "DataQualityAgent")

        result = tool._run("Check data quality of customers table")

        assert "3 data quality issues" in result

    def test_run_preserves_conversation_id(self, client, mock_agent_info, httpx_mock):
        """_run stores and uses conversation_id for multi-turn."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/api/agents/DataQualityAgent/invoke",
            json={"conversationId": "conv-first", "response": "First response"},
        )
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/api/agents/DataQualityAgent/invoke",
            json={"conversationId": "conv-first", "response": "Second response"},
        )

        tool = MetadataAgentTool.from_client(client, "DataQualityAgent")
        tool._run("First query")
        tool._run("Second query")

        requests = [r for r in httpx_mock.get_requests() if "/invoke" in str(r.url)]
        first_body = json.loads(requests[0].content)
        second_body = json.loads(requests[1].content)

        assert "conversationId" not in first_body
        assert second_body["conversationId"] == "conv-first"

    def test_reset_conversation_clears_id(self, client, mock_agent_info, httpx_mock):
        """reset_conversation clears stored conversation_id."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/api/agents/DataQualityAgent/invoke",
            json={"conversationId": "conv-to-reset", "response": "OK"},
        )

        tool = MetadataAgentTool.from_client(client, "DataQualityAgent")
        tool._run("Query")
        assert tool._conversation_id == "conv-to-reset"

        tool.reset_conversation()
        assert tool._conversation_id is None


class TestMetadataAgentToolLangChainInterface:
    """Tests for LangChain BaseTool interface compliance."""

    def test_invoke_method_works(self, client, mock_agent_info, mock_agent_invoke):
        """Tool works with LangChain invoke() method."""
        tool = MetadataAgentTool.from_client(client, "DataQualityAgent")

        result = tool.invoke({"query": "Test query"})

        assert isinstance(result, str)
        assert "data quality" in result.lower()


class TestCreateMetadataTools:
    """Tests for create_metadata_tools helper function."""

    def test_creates_tools_for_specific_agents(self, client, httpx_mock: HTTPXMock):
        """create_metadata_tools creates tools for specified agent names."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/api/agents/Agent1",
            json={
                "name": "Agent1",
                "displayName": "Agent 1",
                "description": "First",
                "abilities": [],
                "apiEnabled": True,
            },
        )
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/api/agents/Agent2",
            json={
                "name": "Agent2",
                "displayName": "Agent 2",
                "description": "Second",
                "abilities": [],
                "apiEnabled": True,
            },
        )

        tools = create_metadata_tools(client, agent_names=["Agent1", "Agent2"])

        assert len(tools) == 2
        assert tools[0].name == "metadata_Agent1"
        assert tools[1].name == "metadata_Agent2"

    def test_creates_tools_for_api_enabled_agents_only(self, client, httpx_mock: HTTPXMock):
        """create_metadata_tools with None fetches only API-enabled agents."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/api/agents/?limit=100&offset=0",
            json={
                "data": [
                    {"name": "EnabledAgent", "apiEnabled": True},
                    {"name": "DisabledAgent", "apiEnabled": False},
                ]
            },
        )
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/api/agents/EnabledAgent",
            json={
                "name": "EnabledAgent",
                "displayName": "Enabled",
                "description": "",
                "abilities": [],
                "apiEnabled": True,
            },
        )

        tools = create_metadata_tools(client)

        assert len(tools) == 1
        assert tools[0].name == "metadata_EnabledAgent"
