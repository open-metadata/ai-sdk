"""MCP client for OpenMetadata's MCP server."""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from metadata_ai._http import HTTPClient
    from metadata_ai.auth import TokenAuth

from metadata_ai.exceptions import MCPError
from metadata_ai.mcp._models import MCPTool, ToolCallResult, ToolInfo, ToolParameter


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
    """Client for OpenMetadata's MCP server."""

    def __init__(
        self,
        host: str,
        auth: TokenAuth,
        http: HTTPClient,
    ) -> None:
        self._host = host.rstrip("/")
        self._auth = auth
        self._http = http
        self._mcp_endpoint = f"{self._host}/mcp"

    def _make_jsonrpc_request(self, method: str, params: dict | None = None) -> dict:
        """Make a JSON-RPC 2.0 request to the MCP server."""
        import httpx

        request_id = str(uuid.uuid4())[:8]
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }

        headers = {"Authorization": f"Bearer {self._auth.token}"}
        response = httpx.post(
            self._mcp_endpoint,
            json=payload,
            headers=headers,
            timeout=30.0,
        )

        if response.status_code != 200:
            raise MCPError(f"MCP request failed: {response.text}", status_code=response.status_code)

        result = response.json()
        if "error" in result:
            raise MCPError(f"MCP error: {result['error'].get('message', 'Unknown error')}")

        return result.get("result", {})

    def list_tools(self) -> list[ToolInfo]:
        """Fetch available tools from MCP server."""
        result = self._make_jsonrpc_request("tools/list")
        tools_data = result.get("tools", [])
        return [self._parse_tool_info(t) for t in tools_data]

    def call_tool(self, name: MCPTool, arguments: dict) -> ToolCallResult:
        """Execute a tool via MCP protocol."""
        result = self._make_jsonrpc_request(
            "tools/call",
            {"name": name.value, "arguments": arguments},
        )

        content = result.get("content", [])
        if content and len(content) > 0:
            first_content = content[0]
            if first_content.get("type") == "text":
                text = first_content.get("text", "{}")
                data = json.loads(text) if text.startswith("{") else {"text": text}
                return ToolCallResult(success=True, data=data, error=None)

        return ToolCallResult(success=True, data={}, error=None)

    def _parse_tool_info(self, data: dict) -> ToolInfo:
        """Parse tool info from MCP response."""
        name = MCPTool(data["name"])
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
