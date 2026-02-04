"""Tests for MCP LangChain adapter."""

import pytest
from pytest_httpx import HTTPXMock

pytest.importorskip("langchain_core")

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
                        "description": "Search for metadata",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Search query"},
                            },
                            "required": ["query"],
                        },
                    },
                ]
            },
        },
    )


class TestAsLangChainTools:
    """Tests for MCPClient.as_langchain_tools()."""

    def test_returns_langchain_base_tools(self, client, mock_list_tools):
        """as_langchain_tools returns list of BaseTool instances."""
        from langchain_core.tools import BaseTool

        tools = client.mcp.as_langchain_tools()

        assert len(tools) == 1
        assert isinstance(tools[0], BaseTool)
        assert tools[0].name == "search_metadata"
        assert "Search for metadata" in tools[0].description

    def test_tool_invocation_calls_mcp(self, client, httpx_mock: HTTPXMock):
        """LangChain tool invocation calls MCP server."""
        # Mock list_tools
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
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string", "description": "Query"},
                                },
                                "required": ["query"],
                            },
                        },
                    ]
                },
            },
        )
        # Mock tool call
        httpx_mock.add_response(
            url="https://metadata.example.com/mcp",
            method="POST",
            json={
                "jsonrpc": "2.0",
                "id": "test",
                "result": {"content": [{"type": "text", "text": '{"tables": ["customers"]}'}]},
            },
        )

        tools = client.mcp.as_langchain_tools()
        result = tools[0].invoke({"query": "customer"})

        assert "customers" in result

    def test_filters_with_exclude(self, client, httpx_mock: HTTPXMock):
        """as_langchain_tools filters with exclude parameter."""
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

        tools = client.mcp.as_langchain_tools(exclude=[MCPTool.PATCH_ENTITY])

        assert len(tools) == 1
        assert tools[0].name == "search_metadata"
