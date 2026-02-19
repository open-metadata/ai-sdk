# MCP Tools Integration

This guide covers using OpenMetadata's MCP (Model Context Protocol) tools directly with AI frameworks like LangChain and OpenAI.

**Prerequisites:** You need `METADATA_HOST` and `METADATA_TOKEN` configured. See [Getting Your Credentials](README.md#getting-your-credentials) if you haven't set these up.

## What are MCP Tools?

OpenMetadata exposes an MCP server at the `/mcp` endpoint that provides tools for interacting with your metadata catalog:

| Tool | Description |
|------|-------------|
| `search_metadata` | Search across your metadata catalog |
| `get_entity_details` | Get detailed information about an entity |
| `get_entity_lineage` | Get lineage information for an entity |
| `create_glossary` | Create a new glossary |
| `create_glossary_term` | Create a new glossary term |
| `create_lineage` | Create lineage between entities |
| `patch_entity` | Update an entity's metadata |

**When to use MCP tools vs Dynamic Agents:**

- **Dynamic Agents** (via `client.agent(...)`) - Pre-built AI agents that combine multiple tools with specific personas and prompts. Use when you want a ready-to-use assistant.
- **MCP Tools** (via `client.mcp`) - Direct access to individual tools. Use when building custom AI applications with your own LLM and prompts.

## Installation

```bash
# Core SDK
pip install ai-sdk

# With LangChain support
pip install ai-sdk[langchain]
```

## Set Environment Variables

```bash
# Your OpenMetadata server URL
export METADATA_HOST="https://your-openmetadata.com"

# Your bot's JWT token (from Settings > Bots in your instance)
export METADATA_TOKEN="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## Quick Start

### List Available Tools

```python
from ai_sdk import MetadataAI, MetadataConfig

# Create client from environment
config = MetadataConfig.from_env()
client = MetadataAI.from_config(config)

# List available MCP tools
tools = client.mcp.list_tools()
for tool in tools:
    print(f"{tool.name}: {tool.description}")

client.close()
```

### Call a Tool Directly

```python
from ai_sdk import MetadataAI, MetadataConfig
from ai_sdk.mcp.models import MCPTool

config = MetadataConfig.from_env()
client = MetadataAI.from_config(config)

# Search for tables
result = client.mcp.call_tool(
    MCPTool.SEARCH_METADATA,
    {"query": "customers", "index": "table"}
)

if result.success:
    print(result.data)
else:
    print(f"Error: {result.error}")

client.close()
```

## LangChain Integration

Convert MCP tools to LangChain format for use with LangChain agents.

### Basic Usage

```python
from ai_sdk import MetadataAI, MetadataConfig
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

# Create Metadata client
config = MetadataConfig.from_env()
client = MetadataAI.from_config(config)

# Convert MCP tools to LangChain format
tools = client.mcp.as_langchain_tools()

# Set up LangChain agent
llm = ChatOpenAI(model="gpt-4")
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a data catalog assistant. Use the available tools to help users explore metadata."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_tool_calling_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Run
result = executor.invoke({
    "input": "Find tables related to customers and show their lineage"
})
print(result["output"])

client.close()
```

### Filtering Tools

Include only specific tools:

```python
from ai_sdk.mcp.models import MCPTool

# Only include read-only tools
tools = client.mcp.as_langchain_tools(
    include=[MCPTool.SEARCH_METADATA, MCPTool.GET_ENTITY_DETAILS, MCPTool.GET_ENTITY_LINEAGE]
)
```

Exclude mutation tools:

```python
# Exclude tools that modify data
tools = client.mcp.as_langchain_tools(
    exclude=[MCPTool.PATCH_ENTITY, MCPTool.CREATE_GLOSSARY, MCPTool.CREATE_GLOSSARY_TERM]
)
```

## OpenAI Integration

Convert MCP tools to OpenAI function calling format for direct use with OpenAI's API.

### Basic Usage

```python
import json
from openai import OpenAI
from ai_sdk import MetadataAI, MetadataConfig

# Create clients
config = MetadataConfig.from_env()
om_client = MetadataAI.from_config(config)
openai_client = OpenAI()

# Get tools in OpenAI format
tools = om_client.mcp.as_openai_tools()

# Create tool executor
executor = om_client.mcp.create_tool_executor()

# Make a request with tool calling
response = openai_client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Find customer tables"}],
    tools=tools,
)

# Execute tool calls from response
message = response.choices[0].message
if message.tool_calls:
    for tool_call in message.tool_calls:
        result = executor(
            tool_call.function.name,
            json.loads(tool_call.function.arguments)
        )
        print(f"Tool: {tool_call.function.name}")
        print(f"Result: {result}")

om_client.close()
```

### Filtering Tools

Same filtering works for OpenAI format:

```python
from ai_sdk.mcp.models import MCPTool

# Only read-only tools
tools = om_client.mcp.as_openai_tools(
    include=[MCPTool.SEARCH_METADATA, MCPTool.GET_ENTITY_DETAILS]
)

# Exclude mutation tools
tools = om_client.mcp.as_openai_tools(
    exclude=[MCPTool.PATCH_ENTITY]
)
```

## Complete Example: Metadata Explorer

A complete example building a metadata exploration assistant:

```python
from ai_sdk import MetadataAI, MetadataConfig
from ai_sdk.mcp.models import MCPTool
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

# Setup
config = MetadataConfig.from_env()
client = MetadataAI.from_config(config)

# Use only read-only tools for safety
tools = client.mcp.as_langchain_tools(
    include=[
        MCPTool.SEARCH_METADATA,
        MCPTool.GET_ENTITY_DETAILS,
        MCPTool.GET_ENTITY_LINEAGE,
    ]
)

llm = ChatOpenAI(model="gpt-4", temperature=0)

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a metadata catalog assistant. Help users:
1. Search for tables, dashboards, and other data assets
2. Understand entity details and schemas
3. Explore data lineage

Use the available tools to answer questions about the data catalog."""),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_tool_calling_agent(llm, tools, prompt)
executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    max_iterations=5
)

# Interactive loop
print("Metadata Explorer (type 'quit' to exit)")
print("-" * 40)

while True:
    user_input = input("\nYou: ").strip()
    if user_input.lower() in ("quit", "exit", "q"):
        break

    result = executor.invoke({"input": user_input})
    print(f"\nAssistant: {result['output']}")

client.close()
```

## API Reference

### MCPTool Enum

```python
from ai_sdk.mcp.models import MCPTool

class MCPTool(StrEnum):
    SEARCH_METADATA = "search_metadata"
    GET_ENTITY_DETAILS = "get_entity_details"
    GET_ENTITY_LINEAGE = "get_entity_lineage"
    CREATE_GLOSSARY = "create_glossary"
    CREATE_GLOSSARY_TERM = "create_glossary_term"
    CREATE_LINEAGE = "create_lineage"
    PATCH_ENTITY = "patch_entity"
```

### MCPClient Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `list_tools()` | `list[ToolInfo]` | Fetch available tools from MCP server |
| `call_tool(name, arguments)` | `ToolCallResult` | Execute a tool directly |
| `as_langchain_tools(include, exclude)` | `list[BaseTool]` | Convert to LangChain format |
| `as_openai_tools(include, exclude)` | `list[dict]` | Convert to OpenAI function calling format |
| `create_tool_executor()` | `Callable` | Create executor for OpenAI tool calls |

### ToolInfo

```python
@dataclass
class ToolInfo:
    name: MCPTool           # Tool identifier
    description: str        # Human-readable description
    parameters: list[ToolParameter]  # Input parameters
```

### ToolCallResult

```python
@dataclass
class ToolCallResult:
    success: bool           # Whether the call succeeded
    data: dict | None       # Result data (if success)
    error: str | None       # Error message (if failed)
```

## Error Handling

```python
from ai_sdk.exceptions import MCPError, MCPToolExecutionError

try:
    result = client.mcp.call_tool(MCPTool.SEARCH_METADATA, {"query": "test"})
except MCPToolExecutionError as e:
    # Raised when a tool executes but reports an error (isError=True)
    print(f"Tool '{e.tool}' failed: {e}")
except MCPError as e:
    # Raised for protocol-level errors (network, auth, server)
    print(f"MCP error: {e}")
    if e.status_code:
        print(f"Status code: {e.status_code}")
```

## Troubleshooting

### "MCP request failed" with 401 error

Your JWT token is invalid or expired:
1. Go to Settings > Bots in your OpenMetadata instance
2. Regenerate the token for your bot
3. Update your `METADATA_TOKEN` environment variable

### "MCP request failed" with 404 error

The MCP endpoint may not be available:
1. Verify your OpenMetadata version supports MCP (1.4+)
2. Check the MCP server is enabled in your deployment
3. Verify the host URL is correct

### LangChain tools not working

Ensure you have LangChain installed:

```bash
pip install ai-sdk[langchain]
```

If you see "langchain-core is required", the optional dependency is missing.

### Tool returns empty results

1. Check your search query syntax
2. Verify data exists in your catalog
3. Ensure the bot has permissions to access the data

### Rate limiting

If you see 429 errors, you're hitting rate limits:

```python
import time
from ai_sdk.exceptions import MCPError

try:
    result = client.mcp.call_tool(...)
except MCPError as e:
    if e.status_code == 429:
        time.sleep(5)  # Wait and retry
        result = client.mcp.call_tool(...)
```

## Next Steps

- [Quick Start](quickstart.md) - Get started with Dynamic Agents
- [LangChain Integration](langchain.md) - Use Dynamic Agents with LangChain
- [Error Handling](error-handling.md) - Exception handling patterns
