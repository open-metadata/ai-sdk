"""Tests for MCP client."""

import pytest
from pytest_httpx import HTTPXMock

from metadata_ai.client import MetadataAI
from metadata_ai.exceptions import MCPError, MCPToolExecutionError
from metadata_ai.mcp._client import MCPClient
from metadata_ai.mcp.models import MCPTool, ToolInfo


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

    def test_list_tools_skips_unknown_tools(self, client, httpx_mock: HTTPXMock):
        """list_tools gracefully skips tools not in MCPTool enum."""
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
                        {
                            "name": "some_future_tool",
                            "description": "A tool the SDK does not know about yet",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
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

    def test_call_tool_raises_on_is_error(self, client, httpx_mock: HTTPXMock):
        """call_tool raises MCPToolExecutionError when server sets isError."""
        httpx_mock.add_response(
            url="https://metadata.example.com/mcp",
            method="POST",
            json={
                "jsonrpc": "2.0",
                "id": "test-id",
                "result": {
                    "content": [{"type": "text", "text": 'argument "content" is null'}],
                    "isError": True,
                },
            },
        )

        mcp = MCPClient(client._host, client._auth, client._http)

        with pytest.raises(MCPToolExecutionError) as exc_info:
            mcp.call_tool(MCPTool.SEARCH_METADATA, {"query": "customer"})

        assert exc_info.value.tool == "search_metadata"
        assert 'argument "content" is null' in str(exc_info.value)

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


class TestMetadataAIMCPProperty:
    """Tests for MetadataAI.mcp property."""

    def test_mcp_property_returns_mcp_client(self, client):
        """MetadataAI.mcp returns MCPClient instance."""
        mcp = client.mcp
        assert isinstance(mcp, MCPClient)

    def test_mcp_property_is_cached(self, client):
        """MetadataAI.mcp returns same instance on repeated access."""
        mcp1 = client.mcp
        mcp2 = client.mcp
        assert mcp1 is mcp2


class TestMCPClientFiltering:
    """Tests for tool filtering."""

    @pytest.fixture
    def sample_tools(self):
        """Sample ToolInfo list."""
        return [
            ToolInfo(
                name=MCPTool.SEARCH_METADATA,
                description="Search",
                parameters=[],
            ),
            ToolInfo(
                name=MCPTool.GET_ENTITY_DETAILS,
                description="Get entity",
                parameters=[],
            ),
            ToolInfo(
                name=MCPTool.PATCH_ENTITY,
                description="Patch entity",
                parameters=[],
            ),
        ]

    def test_filter_tools_include(self, sample_tools):
        """filter_tools with include returns only specified tools."""
        from metadata_ai.mcp._client import _filter_tools

        filtered = _filter_tools(
            sample_tools,
            include=[MCPTool.SEARCH_METADATA],
            exclude=None,
        )

        assert len(filtered) == 1
        assert filtered[0].name == MCPTool.SEARCH_METADATA

    def test_filter_tools_exclude(self, sample_tools):
        """filter_tools with exclude removes specified tools."""
        from metadata_ai.mcp._client import _filter_tools

        filtered = _filter_tools(
            sample_tools,
            include=None,
            exclude=[MCPTool.PATCH_ENTITY],
        )

        assert len(filtered) == 2
        tool_names = [t.name for t in filtered]
        assert MCPTool.PATCH_ENTITY not in tool_names

    def test_filter_tools_none_returns_all(self, sample_tools):
        """filter_tools with no filters returns all tools."""
        from metadata_ai.mcp._client import _filter_tools

        filtered = _filter_tools(sample_tools, include=None, exclude=None)

        assert len(filtered) == 3
