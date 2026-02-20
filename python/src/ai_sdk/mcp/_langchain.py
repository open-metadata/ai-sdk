"""LangChain adapter for MCP tools.

Requires: pip install ai-sdk[langchain]
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ai_sdk.mcp._client import MCPClient

try:
    from langchain_core.callbacks import CallbackManagerForToolRun
    from langchain_core.tools import BaseTool, ToolException
    from pydantic import BaseModel, Field, create_model
except ImportError as e:
    raise ImportError(
        "LangChain integration requires langchain-core. Install with: pip install ai-sdk[langchain]"
    ) from e

from ai_sdk.exceptions import MCPToolExecutionError
from ai_sdk.mcp.models import MCPTool, ToolInfo


def build_langchain_tools(
    mcp_client: MCPClient,
    tools: list[ToolInfo],
) -> list[BaseTool]:
    """Convert ToolInfo list to LangChain BaseTool instances."""
    return [_create_langchain_tool(mcp_client, info) for info in tools]


def _create_langchain_tool(mcp_client: MCPClient, info: ToolInfo) -> BaseTool:
    """Create a LangChain tool that calls the MCP server."""
    tool_args_schema = _build_args_schema(info)
    tool_name_str = info.name.value
    tool_description = info.description
    tool_name_enum = info.name

    class MCPToolWrapper(BaseTool):
        name: str = tool_name_str
        description: str = tool_description
        args_schema: type[BaseModel] = tool_args_schema
        handle_tool_error: bool = True

        _mcp_client: MCPClient
        _tool_name: MCPTool

        def __init__(self, mcp_client: MCPClient, tool_name: MCPTool, **kwargs: Any):
            super().__init__(**kwargs)
            self._mcp_client = mcp_client
            self._tool_name = tool_name

        def _run(
            self,
            run_manager: CallbackManagerForToolRun | None = None,
            **kwargs: Any,
        ) -> str:
            arguments = {k: v for k, v in kwargs.items() if v is not None}
            try:
                result = self._mcp_client.call_tool(self._tool_name, arguments)
            except MCPToolExecutionError as exc:
                raise ToolException(str(exc)) from exc
            return json.dumps(result.data)

    return MCPToolWrapper(mcp_client=mcp_client, tool_name=tool_name_enum)


def _build_args_schema(info: ToolInfo) -> type[BaseModel]:
    """Dynamically create Pydantic model from tool parameters."""
    fields: dict[str, Any] = {}

    for param in info.parameters:
        python_type = _mcp_type_to_python(param.type)
        if param.required:
            fields[param.name] = (python_type, Field(description=param.description))
        else:
            fields[param.name] = (
                python_type | None,
                Field(default=None, description=param.description),
            )

    if not fields:
        fields["placeholder_"] = (str | None, Field(default=None, description=""))

    return create_model(f"{info.name.value}_args", **fields)


def _mcp_type_to_python(mcp_type: str) -> type:
    """Convert MCP type string to Python type."""
    type_map = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    return type_map.get(mcp_type, str)
