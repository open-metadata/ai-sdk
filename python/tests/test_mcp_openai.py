"""Tests for MCP OpenAI adapter."""

import pytest
from pytest_httpx import HTTPXMock

from metadata_ai.client import MetadataAI
from metadata_ai.mcp._models import MCPTool


@pytest.fixture
def client():
    """MetadataAI client fixture."""
    c = MetadataAI(
        host="https://metadata.example.com",
        token="test-token",
        max_retries=0,
    )
    yield c
    c.close()


@pytest.fixture
def mock_list_tools(httpx_mock: HTTPXMock):
    """Mock list_tools response."""
    httpx_mock.add_response(
        url="https://metadata.example.com/mcp",
        method="POST",
        json={
            "jsonrpc": "2.0",
            "id": "test",
            "result": {
                "tools": [
                    {
                        "name": "search_metadata",
                        "description": "Search for metadata in the catalog",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Search query"},
                                "size": {"type": "integer", "description": "Result count"},
                            },
                            "required": ["query"],
                        },
                    },
                ]
            },
        },
    )


class TestAsOpenAITools:
    """Tests for MCPClient.as_openai_tools()."""

    def test_returns_openai_function_schema(self, client, mock_list_tools):
        """as_openai_tools returns OpenAI function calling format."""
        tools = client.mcp.as_openai_tools()

        assert len(tools) == 1
        tool = tools[0]

        assert tool["type"] == "function"
        assert tool["function"]["name"] == "search_metadata"
        assert tool["function"]["description"] == "Search for metadata in the catalog"
        assert tool["function"]["parameters"]["type"] == "object"
        assert "query" in tool["function"]["parameters"]["properties"]
        assert "query" in tool["function"]["parameters"]["required"]

    def test_filters_tools_with_include(self, client, httpx_mock: HTTPXMock):
        """as_openai_tools filters with include parameter."""
        httpx_mock.add_response(
            url="https://metadata.example.com/mcp",
            method="POST",
            json={
                "jsonrpc": "2.0",
                "id": "test",
                "result": {
                    "tools": [
                        {
                            "name": "search_metadata",
                            "description": "Search",
                            "inputSchema": {"type": "object", "properties": {}},
                        },
                        {
                            "name": "patch_entity",
                            "description": "Patch",
                            "inputSchema": {"type": "object", "properties": {}},
                        },
                    ]
                },
            },
        )

        tools = client.mcp.as_openai_tools(include=[MCPTool.SEARCH_METADATA])

        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "search_metadata"
