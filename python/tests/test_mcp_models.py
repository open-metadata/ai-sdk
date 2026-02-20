"""Tests for MCP models."""

from ai_sdk.mcp.models import MCPTool, ToolCallResult, ToolInfo, ToolParameter


class TestMCPToolEnum:
    """Tests for MCPTool enum."""

    def test_enum_has_all_tools(self):
        """MCPTool enum contains all expected tools."""
        assert MCPTool.SEARCH_METADATA == "search_metadata"
        assert MCPTool.SEMANTIC_SEARCH == "semantic_search"
        assert MCPTool.GET_ENTITY_DETAILS == "get_entity_details"
        assert MCPTool.GET_ENTITY_LINEAGE == "get_entity_lineage"
        assert MCPTool.CREATE_GLOSSARY == "create_glossary"
        assert MCPTool.CREATE_GLOSSARY_TERM == "create_glossary_term"
        assert MCPTool.CREATE_LINEAGE == "create_lineage"
        assert MCPTool.PATCH_ENTITY == "patch_entity"
        assert MCPTool.GET_TEST_DEFINITIONS == "get_test_definitions"
        assert MCPTool.CREATE_TEST_CASE == "create_test_case"
        assert MCPTool.ROOT_CAUSE_ANALYSIS == "root_cause_analysis"

    def test_enum_is_str_enum(self):
        """MCPTool values are strings."""
        for tool in MCPTool:
            assert isinstance(tool.value, str)
            assert isinstance(tool, str)


class TestToolParameter:
    """Tests for ToolParameter dataclass."""

    def test_create_tool_parameter(self):
        """ToolParameter can be created with all fields."""
        param = ToolParameter(
            name="query",
            type="string",
            description="Search query",
            required=True,
        )
        assert param.name == "query"
        assert param.type == "string"
        assert param.description == "Search query"
        assert param.required is True

    def test_optional_parameter(self):
        """ToolParameter handles optional parameters."""
        param = ToolParameter(
            name="size",
            type="integer",
            description="Page size",
            required=False,
        )
        assert param.required is False


class TestToolInfo:
    """Tests for ToolInfo dataclass."""

    def test_create_tool_info(self):
        """ToolInfo can be created with all fields."""
        params = [
            ToolParameter(name="query", type="string", description="Search", required=True),
        ]
        info = ToolInfo(
            name=MCPTool.SEARCH_METADATA,
            description="Search metadata catalog",
            parameters=params,
        )
        assert info.name == MCPTool.SEARCH_METADATA
        assert info.description == "Search metadata catalog"
        assert len(info.parameters) == 1


class TestToolCallResult:
    """Tests for ToolCallResult dataclass."""

    def test_successful_result(self):
        """ToolCallResult represents success."""
        result = ToolCallResult(
            success=True,
            data={"tables": [{"name": "customers"}]},
            error=None,
        )
        assert result.success is True
        assert result.data == {"tables": [{"name": "customers"}]}
        assert result.error is None

    def test_error_result(self):
        """ToolCallResult represents error."""
        result = ToolCallResult(
            success=False,
            data=None,
            error="Tool execution failed",
        )
        assert result.success is False
        assert result.data is None
        assert result.error == "Tool execution failed"


class TestMCPExceptions:
    """Tests for MCP-specific exceptions."""

    def test_mcp_error_base(self):
        """MCPError is base exception."""
        from ai_sdk.exceptions import MCPError

        error = MCPError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.status_code is None

    def test_mcp_tool_execution_error(self):
        """MCPToolExecutionError includes tool name."""
        from ai_sdk.exceptions import MCPToolExecutionError

        error = MCPToolExecutionError(MCPTool.SEARCH_METADATA, "Connection failed")
        assert "search_metadata" in str(error)
        assert "Connection failed" in str(error)
        assert error.tool == MCPTool.SEARCH_METADATA
