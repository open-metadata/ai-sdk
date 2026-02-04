# MCP Tools Integration Design

**Date:** 2026-02-04
**Status:** Draft
**Scope:** Python SDK only (TypeScript/Java future work)

## Problem

Users with self-hosted OpenMetadata have access to the MCP server (`/mcp` endpoint) but no way to integrate these tools with their own AI systems. The SDK currently only supports Collate Agents.

## Goal

Extend the Python SDK to expose OpenMetadata's MCP tools for use with AI frameworks (LangChain, OpenAI function calling), enabling users to build custom AI applications using OpenMetadata tools.

## Non-Goals

- Building a full MCP protocol implementation (we only need tools/list and tools/call)
- Supporting MCP resources or prompts (tools only)
- TypeScript/Java support (future work)

## Architecture

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   LLM Provider   │     │   User's App     │     │  OpenMetadata    │
│ (Claude, GPT...) │◄───►│ (LangChain etc)  │◄───►│   MCP Server     │
└──────────────────┘     └──────────────────┘     └──────────────────┘
                                 │
                                 │ uses
                                 ▼
                         ┌──────────────────┐
                         │  metadata-ai SDK │
                         │  client.mcp.*    │
                         └──────────────────┘
```

The SDK provides tool definitions and execution functions that AI frameworks use. The LLM decides when to call tools; the SDK handles communication with OpenMetadata's MCP server.

## API Design

### Basic Usage

```python
from metadata_ai import MetadataAI
from metadata_ai.mcp import MCPTool

client = MetadataAI(host="https://openmetadata.example.com", token="...")

# List available tools
tools_info = client.mcp.list_tools()

# Get tools for LangChain
langchain_tools = client.mcp.as_langchain_tools()

# Get tools for OpenAI function calling
openai_tools = client.mcp.as_openai_tools()
```

### Filtering Tools

```python
# Include only specific tools (allowlist)
tools = client.mcp.as_langchain_tools(
    include=[MCPTool.SEARCH_METADATA, MCPTool.GET_ENTITY_DETAILS],
)

# Exclude mutation tools (blocklist)
tools = client.mcp.as_langchain_tools(
    exclude=[MCPTool.PATCH_ENTITY, MCPTool.CREATE_GLOSSARY, MCPTool.CREATE_GLOSSARY_TERM],
)
```

### LangChain Integration

```python
from langchain.chat_models import init_chat_model
from langchain.agents import create_tool_calling_agent, AgentExecutor
from metadata_ai import MetadataAI

client = MetadataAI(host="...", token="...")
tools = client.mcp.as_langchain_tools()

llm = init_chat_model("claude-sonnet-4-20250514")
agent = create_tool_calling_agent(llm, tools)
executor = AgentExecutor(agent=agent, tools=tools)

result = executor.invoke({"input": "Find tables with customer PII and show their lineage"})
```

### OpenAI Integration

```python
from openai import OpenAI
from metadata_ai import MetadataAI
import json

om_client = MetadataAI(host="...", token="...")
openai_client = OpenAI()

tools = om_client.mcp.as_openai_tools()
executor = om_client.mcp.create_tool_executor()

response = openai_client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Find customer tables"}],
    tools=tools,
)

# Execute tool calls from response
for tool_call in response.choices[0].message.tool_calls:
    result = executor(tool_call.function.name, json.loads(tool_call.function.arguments))
```

## Data Models

### MCPTool Enum

```python
from enum import StrEnum

class MCPTool(StrEnum):
    """Available MCP tools from OpenMetadata."""
    SEARCH_METADATA = "search_metadata"
    GET_ENTITY_DETAILS = "get_entity_details"
    GET_ENTITY_LINEAGE = "get_entity_lineage"
    CREATE_GLOSSARY = "create_glossary"
    CREATE_GLOSSARY_TERM = "create_glossary_term"
    PATCH_ENTITY = "patch_entity"
```

### Tool Metadata

```python
from dataclasses import dataclass

@dataclass
class ToolParameter:
    """Schema for a tool parameter."""
    name: str
    type: str  # "string", "integer", "boolean", "array", "object"
    description: str
    required: bool

@dataclass
class ToolInfo:
    """Metadata about an MCP tool."""
    name: MCPTool
    description: str
    parameters: list[ToolParameter]

@dataclass
class ToolCallResult:
    """Result from calling an MCP tool."""
    success: bool
    data: dict | None
    error: str | None
```

## MCP Client Implementation

### Core Client

```python
class MCPClient:
    """Client for OpenMetadata's MCP server."""

    def __init__(self, http_client: HTTPClient) -> None:
        self._http = http_client
        self._tools_cache: list[ToolInfo] | None = None

    def list_tools(self) -> list[ToolInfo]:
        """Fetch available tools from MCP server."""
        response = self._http.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": str(uuid4()),
            "method": "tools/list",
            "params": {}
        })
        return [self._parse_tool_info(t) for t in response["result"]["tools"]]

    def call_tool(self, name: MCPTool, arguments: dict) -> ToolCallResult:
        """Execute a tool via MCP protocol."""
        response = self._http.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": str(uuid4()),
            "method": "tools/call",
            "params": {"name": name.value, "arguments": arguments}
        })
        return self._parse_tool_result(response)

    async def acall_tool(self, name: MCPTool, arguments: dict) -> ToolCallResult:
        """Async version of call_tool."""
        ...

    def as_langchain_tools(
        self,
        include: list[MCPTool] | None = None,
        exclude: list[MCPTool] | None = None,
    ) -> list[BaseTool]:
        """Convert MCP tools to LangChain format."""
        from metadata_ai.mcp._langchain import build_langchain_tools
        return build_langchain_tools(self, include=include, exclude=exclude)

    def as_openai_tools(
        self,
        include: list[MCPTool] | None = None,
        exclude: list[MCPTool] | None = None,
    ) -> list[dict]:
        """Convert MCP tools to OpenAI function calling format."""
        from metadata_ai.mcp._openai import build_openai_tools
        return build_openai_tools(self, include=include, exclude=exclude)

    def create_tool_executor(self) -> Callable[[str, dict], dict]:
        """Create executor function for OpenAI tool calls."""
        from metadata_ai.mcp._openai import create_tool_executor
        return create_tool_executor(self)
```

### LangChain Adapter

```python
# metadata_ai/mcp/_langchain.py
def build_langchain_tools(
    mcp_client: MCPClient,
    include: list[MCPTool] | None,
    exclude: list[MCPTool] | None,
) -> list[BaseTool]:
    """Build LangChain tools from MCP tool definitions."""
    tools_info = mcp_client.list_tools()
    filtered = _filter_tools(tools_info, include, exclude)
    return [_create_langchain_tool(mcp_client, info) for info in filtered]

def _create_langchain_tool(mcp_client: MCPClient, info: ToolInfo) -> BaseTool:
    """Create a LangChain tool that calls the MCP server."""
    args_schema = _build_args_schema(info)

    class MCPToolWrapper(BaseTool):
        name: str = info.name.value
        description: str = info.description
        args_schema: type[BaseModel] = args_schema

        def _run(self, **kwargs) -> str:
            result = mcp_client.call_tool(info.name, kwargs)
            if not result.success:
                raise ToolException(result.error)
            return json.dumps(result.data)

        async def _arun(self, **kwargs) -> str:
            result = await mcp_client.acall_tool(info.name, kwargs)
            if not result.success:
                raise ToolException(result.error)
            return json.dumps(result.data)

    return MCPToolWrapper()
```

### OpenAI Adapter

```python
# metadata_ai/mcp/_openai.py
def build_openai_tools(
    mcp_client: MCPClient,
    include: list[MCPTool] | None,
    exclude: list[MCPTool] | None,
) -> list[dict]:
    """Build OpenAI function calling schemas from MCP tool definitions."""
    tools_info = mcp_client.list_tools()
    filtered = _filter_tools(tools_info, include, exclude)
    return [_to_openai_schema(info) for info in filtered]

def _to_openai_schema(info: ToolInfo) -> dict:
    """Convert ToolInfo to OpenAI function calling format."""
    properties = {}
    required = []

    for param in info.parameters:
        properties[param.name] = {
            "type": _mcp_type_to_json_schema(param.type),
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

def create_tool_executor(mcp_client: MCPClient) -> Callable[[str, dict], dict]:
    """Create a function that executes tool calls from OpenAI responses."""
    def execute(tool_name: str, arguments: dict) -> dict:
        tool = MCPTool(tool_name)
        result = mcp_client.call_tool(tool, arguments)
        if not result.success:
            return {"error": result.error}
        return result.data
    return execute
```

## File Structure

```
python/src/metadata_ai/
├── __init__.py              # Exports MetadataAI (unchanged)
├── client.py                # Add `mcp` property returning MCPClient
├── mcp/
│   ├── __init__.py          # Empty (no re-exports per dignified-python)
│   ├── _models.py           # MCPTool, ToolInfo, ToolParameter, ToolCallResult
│   ├── _client.py           # MCPClient class
│   ├── _langchain.py        # LangChain adapter (optional dep)
│   └── _openai.py           # OpenAI adapter (no deps)
```

## Dependencies

In `pyproject.toml`:

```toml
[project.optional-dependencies]
langchain = ["langchain-core>=0.2.0"]
```

Installation:
```bash
pip install metadata-ai              # Base package
pip install metadata-ai[langchain]   # With LangChain support
```

## Error Handling

```python
class MCPError(MetadataError):
    """Base error for MCP operations."""
    pass

class MCPToolNotFoundError(MCPError):
    """Tool not found on MCP server."""
    pass

class MCPToolExecutionError(MCPError):
    """Tool execution failed."""
    def __init__(self, tool: MCPTool, message: str) -> None:
        self.tool = tool
        super().__init__(f"Tool '{tool.value}' failed: {message}")
```

## Testing Strategy

### Unit Tests
- Mock HTTP responses for MCP protocol
- Test tool filtering logic (include/exclude)
- Test schema conversion (LangChain, OpenAI formats)
- Test error handling

### Integration Tests
- Require `METADATA_HOST` and `METADATA_TOKEN`
- Test `list_tools()` against real MCP server
- Test `call_tool()` with `search_metadata`
- Test full LangChain agent flow

## Implementation Plan

1. **Models** - Create `_models.py` with `MCPTool`, `ToolInfo`, `ToolParameter`, `ToolCallResult`
2. **MCP Client** - Create `_client.py` with JSON-RPC communication
3. **Client Integration** - Add `mcp` property to `MetadataAI` class
4. **OpenAI Adapter** - Create `_openai.py` (no deps, simpler)
5. **LangChain Adapter** - Create `_langchain.py` (optional dep)
6. **Error Classes** - Add MCP errors to `exceptions.py`
7. **Tests** - Unit tests for each component
8. **Documentation** - Usage examples in docs/

## Open Questions

None - design is complete.

## References

- OpenMetadata MCP Server: `/Users/pmbrull/github/OpenMetadata/openmetadata-mcp`
- MCP Protocol: https://modelcontextprotocol.io/
- DataHub approach: https://github.com/datahub-project/datahub/tree/master/datahub-agent-context
