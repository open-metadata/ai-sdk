"""OpenAI function calling adapter for MCP tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from metadata_ai.mcp._client import MCPClient

from metadata_ai.exceptions import MCPToolExecutionError
from metadata_ai.mcp.models import MCPTool, ToolInfo


def build_openai_tools(tools: list[ToolInfo]) -> list[dict]:
    """Convert ToolInfo list to OpenAI function calling format."""
    return [_to_openai_schema(info) for info in tools]


def _to_openai_schema(info: ToolInfo) -> dict:
    """Convert single ToolInfo to OpenAI function schema."""
    properties = {}
    required = []

    for param in info.parameters:
        properties[param.name] = {
            "type": param.type,
            "description": param.description,
        }
        if param.required:
            required.append(param.name)

    return {
        "type": "function",
        "function": {
            "name": info.name.value,
            "description": info.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


def create_tool_executor(mcp_client: MCPClient):
    """Create executor function for OpenAI tool calls."""

    def execute(tool_name: str, arguments: dict) -> dict:
        tool = MCPTool(tool_name)
        cleaned = {k: v for k, v in arguments.items() if v is not None}
        try:
            result = mcp_client.call_tool(tool, cleaned)
        except MCPToolExecutionError as exc:
            return {"error": str(exc)}
        return result.data or {}

    return execute
