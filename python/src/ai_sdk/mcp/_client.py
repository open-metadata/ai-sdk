"""MCP client for OpenMetadata's MCP server."""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from ai_sdk.auth import TokenAuth

from ai_sdk._http import HTTPClient
from ai_sdk.exceptions import AISdkError, MCPError, MCPToolExecutionError
from ai_sdk.mcp.models import MCPTool, ToolCallResult, ToolInfo


def _filter_tools(
    tools: list[ToolInfo],
    include: list[MCPTool | str] | None,
    exclude: list[MCPTool | str] | None,
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
        # base_url is the host root (not /mcp) so we can POST to "/mcp"
        # directly — avoids httpx appending a trailing slash which the
        # Java MCP transport rejects with 405.
        self._http = HTTPClient(
            base_url=self._host,
            auth=auth,
            timeout=http.timeout,
            verify_ssl=http.verify_ssl,
            max_retries=http.max_retries,
            retry_delay=http.retry_delay,
            user_agent=http.user_agent,
            extra_headers={"Accept": "application/json, text/event-stream"},
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
            result = self._http.post("/mcp", json=payload)
        except (AISdkError, httpx.HTTPError) as exc:
            raise MCPError(f"MCP request failed: {exc}") from exc

        if "error" in result:
            raise MCPError(f"MCP error: {result['error'].get('message', 'Unknown error')}")

        return result.get("result", {})

    def list_tools(self) -> list[ToolInfo]:
        """Fetch available tools from MCP server."""
        result = self._make_jsonrpc_request("tools/list")
        tools_data = result.get("tools", [])
        return [self._parse_tool_info(t) for t in tools_data]

    def call_tool(self, name: MCPTool | str, arguments: dict) -> ToolCallResult:
        """Execute a tool via MCP protocol."""
        tool_name = name.value if isinstance(name, MCPTool) else name
        result = self._make_jsonrpc_request(
            "tools/call",
            {"name": tool_name, "arguments": arguments},
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
                tool=tool_name,
                message=text or "Tool execution failed",
            )

        if text:
            try:
                data = json.loads(text)
            except (json.JSONDecodeError, ValueError):
                data = {"text": text}
            return ToolCallResult(success=True, data=data, error=None)

        return ToolCallResult(success=True, data={}, error=None)

    def _parse_tool_info(self, data: dict) -> ToolInfo:
        """Preserve the server's tool name and complete JSON Schema."""
        return ToolInfo(
            name=data["name"],
            description=data.get("description", ""),
            input_schema=data.get("inputSchema", {"type": "object", "properties": {}}),
        )

    def as_openai_tools(
        self,
        include: list[MCPTool | str] | None = None,
        exclude: list[MCPTool | str] | None = None,
    ) -> list[dict]:
        """
        Get tools formatted for OpenAI function calling.

        Args:
            include: Only include these tools (allowlist)
            exclude: Exclude these tools (blocklist)

        Returns:
            List of dicts in OpenAI function calling schema format
        """
        from ai_sdk.mcp._openai import build_openai_tools

        tools = self.list_tools()
        filtered = _filter_tools(tools, include, exclude)
        return build_openai_tools(filtered)

    def create_tool_executor(self):
        """
        Create executor function for OpenAI tool calls.

        Returns:
            Callable[[str, dict], dict] that executes tool calls
        """
        from ai_sdk.mcp._openai import create_tool_executor

        return create_tool_executor(self)

    def as_langchain_tools(
        self,
        include: list[MCPTool | str] | None = None,
        exclude: list[MCPTool | str] | None = None,
    ) -> list:
        """
        Get tools formatted for LangChain.

        Requires: pip install data-ai-sdk[langchain]

        Args:
            include: Only include these tools (allowlist)
            exclude: Exclude these tools (blocklist)

        Returns:
            List of LangChain BaseTool instances
        """
        from ai_sdk.mcp._langchain import build_langchain_tools

        tools = self.list_tools()
        filtered = _filter_tools(tools, include, exclude)
        return build_langchain_tools(self, filtered)
