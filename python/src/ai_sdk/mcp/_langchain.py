"""LangChain adapter for MCP tools.

Requires: pip install data-ai-sdk[langchain]
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ai_sdk.mcp._client import MCPClient

try:
    from langchain_core.tools import BaseTool, ToolException
except ImportError as e:
    raise ImportError(
        "LangChain integration requires langchain-core. Install with: pip install data-ai-sdk[langchain]"
    ) from e

from ai_sdk.exceptions import MCPToolExecutionError
from ai_sdk.mcp.models import ToolInfo


def build_langchain_tools(
    mcp_client: MCPClient,
    tools: list[ToolInfo],
) -> list[BaseTool]:
    """Convert ToolInfo list to LangChain BaseTool instances."""
    return [_create_langchain_tool(mcp_client, info) for info in tools]


def _create_langchain_tool(mcp_client: MCPClient, info: ToolInfo) -> BaseTool:
    """Create a LangChain tool that calls the MCP server."""

    class MCPToolWrapper(BaseTool):
        name: str = info.name
        description: str = info.description
        args_schema: dict[str, Any] = info.input_schema  # ty: ignore[invalid-mutable-override]
        handle_tool_error: bool = True  # ty: ignore[invalid-mutable-override]

        def _run(self, **kwargs: Any) -> str:
            arguments = {k: v for k, v in kwargs.items() if v is not None}
            try:
                result = mcp_client.call_tool(info.name, arguments)
            except MCPToolExecutionError as exc:
                raise ToolException(str(exc)) from exc
            return json.dumps(result.data)

    return MCPToolWrapper()
