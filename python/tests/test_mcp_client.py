"""Tests for MCP client."""

import pytest
from pytest_httpx import HTTPXMock

from metadata_ai.client import MetadataAI
from metadata_ai.exceptions import MCPError
from metadata_ai.mcp._client import MCPClient
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


class TestMCPClientInit:
    """Tests for MCPClient initialization."""

    def test_mcp_client_created_from_metadata_client(self, client):
        """MCPClient can be created from MetadataAI client."""
        mcp = MCPClient(client._host, client._auth, client._http)
        assert mcp is not None


class TestMCPClientListTools:
    """Tests for MCPClient.list_tools()."""

    def test_list_tools_returns_tool_info_list(self, client, httpx_mock: HTTPXMock):
        """list_tools returns list of ToolInfo."""
        httpx_mock.add_response(
            url="https://metadata.example.com/mcp",
            method="POST",
            json={
                "jsonrpc": "2.0",
                "id": "test-id",
                "result": {
                    "tools": [
                        {
                            "name": "search_metadata",
                            "description": "Search for metadata",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "Search query",
                                    },
                                },
                                "required": ["query"],
                            },
                        },
                    ]
                },
            },
        )

        mcp = MCPClient(client._host, client._auth, client._http)
        tools = mcp.list_tools()

        assert len(tools) == 1
        assert tools[0].name == MCPTool.SEARCH_METADATA
        assert tools[0].description == "Search for metadata"
        assert len(tools[0].parameters) == 1
        assert tools[0].parameters[0].name == "query"
        assert tools[0].parameters[0].required is True


class TestMCPClientCallTool:
    """Tests for MCPClient.call_tool()."""

    def test_call_tool_returns_result(self, client, httpx_mock: HTTPXMock):
        """call_tool returns ToolCallResult on success."""
        httpx_mock.add_response(
            url="https://metadata.example.com/mcp",
            method="POST",
            json={
                "jsonrpc": "2.0",
                "id": "test-id",
                "result": {"content": [{"type": "text", "text": '{"tables": ["customers"]}'}]},
            },
        )

        mcp = MCPClient(client._host, client._auth, client._http)
        result = mcp.call_tool(MCPTool.SEARCH_METADATA, {"query": "customer"})

        assert result.success is True
        assert result.data is not None
        assert result.error is None

    def test_call_tool_handles_error(self, client, httpx_mock: HTTPXMock):
        """call_tool raises MCPError on failure."""
        httpx_mock.add_response(
            url="https://metadata.example.com/mcp",
            method="POST",
            json={
                "jsonrpc": "2.0",
                "id": "test-id",
                "error": {
                    "code": -32000,
                    "message": "Tool execution failed",
                },
            },
        )

        mcp = MCPClient(client._host, client._auth, client._http)

        with pytest.raises(MCPError) as exc_info:
            mcp.call_tool(MCPTool.SEARCH_METADATA, {"query": "test"})

        assert "Tool execution failed" in str(exc_info.value)
