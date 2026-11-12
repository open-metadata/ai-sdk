"""OpenAI function calling adapter for MCP tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_sdk.mcp._client import MCPClient

from ai_sdk.exceptions import MCPToolExecutionError
from ai_sdk.mcp.models import ToolInfo


def build_openai_tools(tools: list[ToolInfo]) -> list[dict]:
    """Convert ToolInfo list to OpenAI function calling format."""
    return [_to_openai_schema(info) for info in tools]


def _to_openai_schema(info: ToolInfo) -> dict:
    """Convert single ToolInfo to OpenAI function schema."""
    return {
        "type": "function",
        "function": {
            "name": info.name,
            "description": info.description,
            "parameters": info.input_schema,
        },
    }


def create_tool_executor(mcp_client: MCPClient):
    """Create executor function for OpenAI tool calls."""

    def execute(tool_name: str, arguments: dict) -> dict:
        cleaned = {k: v for k, v in arguments.items() if v is not None}
        try:
            result = mcp_client.call_tool(tool_name, cleaned)
        except MCPToolExecutionError as exc:
            return {"error": str(exc)}
        return result.data or {}

    return execute
