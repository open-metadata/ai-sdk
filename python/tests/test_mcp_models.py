"""Tests for MCP models."""

from ai_sdk.mcp.models import MCPTool, ToolCallResult, ToolInfo


class TestMCPToolEnum:
    def test_matches_reviewed_server_catalog(self):
        import json
        from pathlib import Path

        fixture = Path(__file__).parent / "fixtures/mcp_tool_names_2_1.json"
        expected = json.loads(fixture.read_text(encoding="utf-8"))["tools"]
        assert {tool.value for tool in MCPTool} == set(expected)


class TestToolInfo:
    def test_retains_nested_input_schema(self):
        schema = {
            "type": "object",
            "properties": {"tags": {"type": "array", "items": {"type": "string"}}},
        }
        info = ToolInfo(name="create_entity", description="Create an entity", input_schema=schema)
        assert info.input_schema == schema


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
