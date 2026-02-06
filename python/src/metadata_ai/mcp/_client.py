"""MCP client for OpenMetadata's MCP server."""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from metadata_ai.auth import TokenAuth

from metadata_ai._http import HTTPClient
from metadata_ai.exceptions import MCPError, MCPToolExecutionError
from metadata_ai.mcp.models import MCPTool, ToolCallResult, ToolInfo, ToolParameter


def _filter_tools(
    tools: list[ToolInfo],
    include: list[MCPTool] | None,
    exclude: list[MCPTool] | None,
) -> list[ToolInfo]:
    """
    Filter tools by include/exclude lists.

    Args:
        tools: List of ToolInfo to filter
        include: If provided, only include these tools
        exclude: If provided, exclude these tools

    Returns:
        Filtered list of ToolInfo
    """
    if include is not None:
        include_set = set(include)
        tools = [t for t in tools if t.name in include_set]

    if exclude is not None:
        exclude_set = set(exclude)
        tools = [t for t in tools if t.name not in exclude_set]

    return tools


class MCPClient:
    """Client for OpenMetadata's MCP server.

    Uses a dedicated HTTPClient to inherit the SDK's retry logic,
    SSL verification, timeout, and user agent settings.
    """

    def __init__(
        self,
        host: str,
        auth: TokenAuth,
        http: HTTPClient,
    ) -> None:
        self._host = host.rstrip("/")
        self._auth = auth

        # Create a dedicated HTTP client for MCP requests that inherits
        # timeout, SSL, retry, and user-agent settings from the parent.
        self._http = HTTPClient(
            base_url=f"{self._host}/mcp",
            auth=auth,
            timeout=http._timeout,
            verify_ssl=http._verify_ssl,
            max_retries=http._max_retries,
            retry_delay=http._retry_delay,
            user_agent=http._user_agent,
        )

    def _make_jsonrpc_request(self, method: str, params: dict | None = None) -> dict:
        """Make a JSON-RPC 2.0 request to the MCP server."""
        request_id = str(uuid.uuid4())[:8]
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }

        try:
            result = self._http.post("", json=payload)
        except Exception as exc:
            raise MCPError(f"MCP request failed: {exc}") from exc

        if "error" in result:
            raise MCPError(f"MCP error: {result['error'].get('message', 'Unknown error')}")

        return result.get("result", {})

    def list_tools(self) -> list[ToolInfo]:
        """Fetch available tools from MCP server."""
        result = self._make_jsonrpc_request("tools/list")
        tools_data = result.get("tools", [])
        parsed = [self._parse_tool_info(t) for t in tools_data]
        return [t for t in parsed if t is not None]

    def call_tool(self, name: MCPTool, arguments: dict) -> ToolCallResult:
        """Execute a tool via MCP protocol."""
        result = self._make_jsonrpc_request(
            "tools/call",
            {"name": name.value, "arguments": arguments},
        )

        is_error = result.get("isError", False)
        content = result.get("content", [])

        text = ""
        if content:
            first_content = content[0]
            if first_content.get("type") == "text":
                text = first_content.get("text", "")

        if is_error:
            raise MCPToolExecutionError(
                tool=name.value,
                message=text or "Tool execution failed",
            )

        if text:
            try:
                data = json.loads(text)
            except (json.JSONDecodeError, ValueError):
                data = {"text": text}
            return ToolCallResult(success=True, data=data, error=None)

        return ToolCallResult(success=True, data={}, error=None)

    def _parse_tool_info(self, data: dict) -> ToolInfo | None:
        """Parse tool info from MCP response.

        Returns None for tools not recognized by the SDK, allowing
        graceful handling of new server-side tools.
        """
        try:
            name = MCPTool(data["name"])
        except ValueError:
            return None
        description = data.get("description", "")
        parameters = self._parse_parameters(data.get("inputSchema", {}))
        return ToolInfo(name=name, description=description, parameters=parameters)

    def _parse_parameters(self, schema: dict) -> list[ToolParameter]:
        """Parse parameters from JSON schema."""
        if schema.get("type") != "object":
            return []

        properties = schema.get("properties", {})
        required = set(schema.get("required", []))
        parameters = []

        for name, prop in properties.items():
            parameters.append(
                ToolParameter(
                    name=name,
                    type=prop.get("type", "string"),
                    description=prop.get("description", ""),
                    required=name in required,
                )
            )

        return parameters

    def as_openai_tools(
        self,
        include: list[MCPTool] | None = None,
        exclude: list[MCPTool] | None = None,
    ) -> list[dict]:
        """
        Get tools formatted for OpenAI function calling.

        Args:
            include: Only include these tools (allowlist)
            exclude: Exclude these tools (blocklist)

        Returns:
            List of dicts in OpenAI function calling schema format
        """
        from metadata_ai.mcp._openai import build_openai_tools

        tools = self.list_tools()
        filtered = _filter_tools(tools, include, exclude)
        return build_openai_tools(filtered)

    def create_tool_executor(self):
        """
        Create executor function for OpenAI tool calls.

        Returns:
            Callable[[str, dict], dict] that executes tool calls
        """
        from metadata_ai.mcp._openai import create_tool_executor

        return create_tool_executor(self)

    def as_langchain_tools(
        self,
        include: list[MCPTool] | None = None,
        exclude: list[MCPTool] | None = None,
    ) -> list:
        """
        Get tools formatted for LangChain.

        Requires: pip install metadata-ai[langchain]

        Args:
            include: Only include these tools (allowlist)
            exclude: Exclude these tools (blocklist)

        Returns:
            List of LangChain BaseTool instances
        """
        from metadata_ai.mcp._langchain import build_langchain_tools

        tools = self.list_tools()
        filtered = _filter_tools(tools, include, exclude)
        return build_langchain_tools(self, filtered)
