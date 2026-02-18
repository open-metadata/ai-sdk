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


class TestMCPClientCallNewTools:
    """Tests for calling the newer MCP tools."""

    def test_call_semantic_search(self, client, httpx_mock: HTTPXMock):
        """call_tool works with semantic_search tool."""
        httpx_mock.add_response(
            url="https://metadata.example.com/mcp",
            method="POST",
            json={
                "jsonrpc": "2.0",
                "id": "test-id",
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": '{"query": "revenue metrics", "results": [{"name": "monthly_revenue"}], "totalFound": 1}',
                        }
                    ]
                },
            },
        )

        mcp = MCPClient(client._host, client._auth, client._http)
        result = mcp.call_tool(MCPTool.SEMANTIC_SEARCH, {"query": "revenue metrics", "size": 5})

        assert result.success is True
        assert result.data["totalFound"] == 1
        assert result.data["results"][0]["name"] == "monthly_revenue"

    def test_call_get_test_definitions(self, client, httpx_mock: HTTPXMock):
        """call_tool works with get_test_definitions tool."""
        httpx_mock.add_response(
            url="https://metadata.example.com/mcp",
            method="POST",
            json={
                "jsonrpc": "2.0",
                "id": "test-id",
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": '{"data": [{"name": "columnValuesToBeNotNull"}], "paging": {}}',
                        }
                    ]
                },
            },
        )

        mcp = MCPClient(client._host, client._auth, client._http)
        result = mcp.call_tool(
            MCPTool.GET_TEST_DEFINITIONS,
            {"entityType": "COLUMN", "testPlatform": "OpenMetadata"},
        )

        assert result.success is True
        assert result.data["data"][0]["name"] == "columnValuesToBeNotNull"

    def test_call_create_test_case(self, client, httpx_mock: HTTPXMock):
        """call_tool works with create_test_case tool."""
        httpx_mock.add_response(
            url="https://metadata.example.com/mcp",
            method="POST",
            json={
                "jsonrpc": "2.0",
                "id": "test-id",
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": '{"id": "abc-123", "name": "test_not_null_email"}',
                        }
                    ]
                },
            },
        )

        mcp = MCPClient(client._host, client._auth, client._http)
        result = mcp.call_tool(
            MCPTool.CREATE_TEST_CASE,
            {
                "name": "test_not_null_email",
                "fqn": "db.schema.users",
                "columnName": "email",
                "testDefinitionName": "columnValuesToBeNotNull",
                "parameterValues": [],
            },
        )

        assert result.success is True
        assert result.data["name"] == "test_not_null_email"

    def test_call_root_cause_analysis(self, client, httpx_mock: HTTPXMock):
        """call_tool works with root_cause_analysis tool."""
        httpx_mock.add_response(
            url="https://metadata.example.com/mcp",
            method="POST",
            json={
                "jsonrpc": "2.0",
                "id": "test-id",
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": '{"fqn": "db.schema.orders", "status": "failed", "summary": "Upstream failure detected"}',
                        }
                    ]
                },
            },
        )

        mcp = MCPClient(client._host, client._auth, client._http)
        result = mcp.call_tool(
            MCPTool.ROOT_CAUSE_ANALYSIS,
            {
                "fqn": "db.schema.orders",
                "entityType": "table",
                "upstreamDepth": 3,
                "downstreamDepth": 3,
            },
        )

        assert result.success is True
        assert result.data["status"] == "failed"
        assert "Upstream failure" in result.data["summary"]

    def test_list_tools_includes_new_tools(self, client, httpx_mock: HTTPXMock):
        """list_tools recognizes the new tool types."""
        httpx_mock.add_response(
            url="https://metadata.example.com/mcp",
            method="POST",
            json={
                "jsonrpc": "2.0",
                "id": "test-id",
                "result": {
                    "tools": [
                        {
                            "name": "semantic_search",
                            "description": "Semantic search for metadata",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string", "description": "Search query"},
                                },
                                "required": ["query"],
                            },
                        },
                        {
                            "name": "get_test_definitions",
                            "description": "Get test definitions",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "entityType": {
                                        "type": "string",
                                        "description": "TABLE or COLUMN",
                                    },
                                },
                                "required": ["entityType"],
                            },
                        },
                        {
                            "name": "create_test_case",
                            "description": "Create a test case",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "description": "Test case name"},
                                    "fqn": {"type": "string", "description": "Table FQN"},
                                },
                                "required": ["name", "fqn"],
                            },
                        },
                        {
                            "name": "root_cause_analysis",
                            "description": "Analyze root cause",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "fqn": {"type": "string", "description": "Entity FQN"},
                                    "entityType": {"type": "string", "description": "Entity type"},
                                },
                                "required": ["fqn", "entityType"],
                            },
                        },
                    ]
                },
            },
        )

        mcp = MCPClient(client._host, client._auth, client._http)
        tools = mcp.list_tools()

        assert len(tools) == 4
        tool_names = {t.name for t in tools}
        assert MCPTool.SEMANTIC_SEARCH in tool_names
        assert MCPTool.GET_TEST_DEFINITIONS in tool_names
        assert MCPTool.CREATE_TEST_CASE in tool_names
        assert MCPTool.ROOT_CAUSE_ANALYSIS in tool_names


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
