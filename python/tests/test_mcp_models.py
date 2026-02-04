"""Tests for MCP models."""

from metadata_ai.mcp._models import MCPTool, ToolCallResult, ToolInfo, ToolParameter


class TestMCPToolEnum:
    """Tests for MCPTool enum."""

    def test_enum_has_all_tools(self):
        """MCPTool enum contains all expected tools."""
        assert MCPTool.SEARCH_METADATA == "search_metadata"
        assert MCPTool.GET_ENTITY_DETAILS == "get_entity_details"
        assert MCPTool.GET_ENTITY_LINEAGE == "get_entity_lineage"
        assert MCPTool.CREATE_GLOSSARY == "create_glossary"
        assert MCPTool.CREATE_GLOSSARY_TERM == "create_glossary_term"
        assert MCPTool.PATCH_ENTITY == "patch_entity"

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
