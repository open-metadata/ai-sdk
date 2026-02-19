# LangChain Integration

This guide covers using Metadata AI agents as tools in LangChain pipelines.

**Prerequisites:** You need `METADATA_HOST` and `METADATA_TOKEN` configured. See [Getting Your Credentials](README.md#getting-your-credentials) if you haven't set these up.

## Installation

Install the SDK with LangChain support:

```bash
pip install ai-sdk[langchain]
```

This installs `langchain-core` as a dependency.

## Quick Start

```python
from ai_sdk import MetadataAI
from ai_sdk.integrations.langchain import MetadataAgentTool
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate

# Create Metadata client
client = MetadataAI(
    host="https://metadata.example.com",
    token="your-bot-jwt-token"
)

# Create a tool from a Metadata agent
tool = MetadataAgentTool.from_client(client, "DataQualityPlannerAgent")

# Set up LangChain agent
llm = ChatOpenAI(model="gpt-4")
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a data analyst. Use available tools for data tasks."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_openai_functions_agent(llm, [tool], prompt)
executor = AgentExecutor(agent=agent, tools=[tool], verbose=True)

# Run
result = executor.invoke({
    "input": "Check data quality of the customers table"
})
print(result["output"])
```

## Creating Tools

### From Client and Agent Name

The simplest way to create a tool:

```python
from ai_sdk import MetadataAI
from ai_sdk.integrations.langchain import MetadataAgentTool

client = MetadataAI(host="...", token="...")
tool = MetadataAgentTool.from_client(client, "DataQualityPlannerAgent")
```

### From Agent Handle

If you already have an agent handle:

```python
agent_handle = client.agent("DataQualityPlannerAgent")
tool = MetadataAgentTool.from_agent(agent_handle)
```

### Custom Tool Name and Description

Override the auto-generated name and description:

```python
tool = MetadataAgentTool.from_client(
    client,
    "DataQualityPlannerAgent",
    name="data_quality_analyzer",
    description="Analyzes tables for data quality issues and recommends tests"
)
```

By default:
- **Name**: `metadata_{agent_name}` (e.g., `metadata_DataQualityPlannerAgent`)
- **Description**: Built from agent's description and abilities

### Create Multiple Tools

Create tools for specific agents:

```python
from ai_sdk.integrations.langchain import create_metadata_tools

tools = create_metadata_tools(client, [
    "DataQualityPlannerAgent",
    "SqlQueryAgent",
    "LineageExplorerAgent",
])
```

Or create tools for all API-enabled agents:

```python
# Fetches all agents with apiEnabled=true
tools = create_metadata_tools(client)
```

## Tool Properties

Each `MetadataAgentTool` has:

| Property | Type | Description |
|----------|------|-------------|
| `name` | `str` | Tool name used by LangChain |
| `description` | `str` | Description shown to the LLM |
| `args_schema` | `BaseModel` | Pydantic schema for input validation |

```python
tool = MetadataAgentTool.from_client(client, "DataQualityPlannerAgent")

print(tool.name)         # metadata_DataQualityPlannerAgent
print(tool.description)  # Analyzes data quality... Capabilities: search_metadata, analyze_quality.
```

## Multi-Turn Conversations

The tool automatically maintains conversation context:

```python
tool = MetadataAgentTool.from_client(client, "DataQualityPlannerAgent")

# First invocation
result1 = tool.invoke({"query": "Analyze the orders table"})

# Second invocation continues the conversation
result2 = tool.invoke({"query": "Now create tests for the issues you found"})

# Reset to start fresh
tool.reset_conversation()
```

### How It Works

1. First call returns a `conversation_id`
2. Subsequent calls automatically include this ID
3. The Metadata agent uses the ID to maintain context
4. Call `reset_conversation()` to start a new conversation

## Using with Different Agent Types

### OpenAI Functions Agent

```python
from langchain.agents import create_openai_functions_agent

agent = create_openai_functions_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools)
```

### ReAct Agent

```python
from langchain.agents import create_react_agent
from langchain import hub

prompt = hub.pull("hwchase17/react")
agent = create_react_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools)
```

### Tool Calling Agent

```python
from langchain.agents import create_tool_calling_agent

agent = create_tool_calling_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools)
```

## Async Support

For async LangChain pipelines, enable async on the Metadata client:

```python
# Create client with async enabled
client = MetadataAI(
    host="https://metadata.example.com",
    token="your-token",
    enable_async=True  # Required for true async
)

tool = MetadataAgentTool.from_client(client, "DataQualityPlannerAgent")

# Now _arun uses true async
result = await tool._arun("Analyze data quality")
```

### Async with AgentExecutor

```python
import asyncio

async def main():
    client = MetadataAI(host="...", token="...", enable_async=True)
    tools = [MetadataAgentTool.from_client(client, "DataQualityPlannerAgent")]

    llm = ChatOpenAI(model="gpt-4")
    prompt = ChatPromptTemplate.from_messages([...])

    agent = create_openai_functions_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools)

    # Async invoke
    result = await executor.ainvoke({
        "input": "Check data quality"
    })
    print(result["output"])

    # Cleanup
    await client.aclose()
    client.close()

asyncio.run(main())
```

### Fallback Behavior

If `enable_async=False` (default), `_arun` falls back to synchronous execution. This ensures compatibility but won't provide true async benefits.

## Error Handling

Handle Metadata-specific errors in your LangChain pipeline:

```python
from ai_sdk.exceptions import (
    AgentNotFoundError,
    AgentNotEnabledError,
    AuthenticationError,
    RateLimitError,
    AgentExecutionError,
)

try:
    result = executor.invoke({"input": "Analyze data"})
except AuthenticationError:
    print("Invalid token - check your bot JWT")
except AgentNotFoundError as e:
    print(f"Agent '{e.agent_name}' not found")
except AgentNotEnabledError as e:
    print(f"Agent '{e.agent_name}' is not API-enabled")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
except AgentExecutionError as e:
    print(f"Agent execution failed: {e}")
```

## Complete Examples

### Data Quality Analysis Pipeline

```python
from ai_sdk import MetadataAI
from ai_sdk.integrations.langchain import MetadataAgentTool
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate

# Setup
client = MetadataAI(
    host="https://metadata.example.com",
    token="your-bot-jwt-token"
)

tools = [
    MetadataAgentTool.from_client(
        client,
        "DataQualityPlannerAgent",
        description="Analyzes tables for data quality issues"
    ),
    MetadataAgentTool.from_client(
        client,
        "SqlQueryAgent",
        description="Generates and explains SQL queries"
    ),
]

llm = ChatOpenAI(model="gpt-4", temperature=0)

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a data quality analyst. Your job is to:
1. Analyze tables for data quality issues
2. Generate SQL queries to investigate problems
3. Recommend data quality tests

Use the available tools to accomplish these tasks."""),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_openai_functions_agent(llm, tools, prompt)
executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    max_iterations=5
)

# Run analysis
result = executor.invoke({
    "input": "Analyze the customers and orders tables. Find any data quality issues and suggest SQL queries to investigate them."
})

print("Analysis complete:")
print(result["output"])
```

### Multi-Agent Collaboration

```python
from ai_sdk import MetadataAI
from ai_sdk.integrations.langchain import create_metadata_tools
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate

client = MetadataAI(host="...", token="...")

# Get all API-enabled agents as tools
tools = create_metadata_tools(client)

print(f"Available tools: {[t.name for t in tools]}")

llm = ChatOpenAI(model="gpt-4")
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a data platform assistant with access to multiple specialized agents. Use them as needed."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_openai_functions_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

result = executor.invoke({
    "input": "I need to understand the lineage of the revenue table and check its data quality"
})
```

## API Reference

### MetadataAgentTool

```python
class MetadataAgentTool(BaseTool):
    """LangChain tool wrapping a Metadata Dynamic Agent."""

    @classmethod
    def from_client(
        cls,
        client: MetadataAI,
        agent_name: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> "MetadataAgentTool":
        """Create tool from client and agent name."""

    @classmethod
    def from_agent(
        cls,
        agent_handle: AgentHandle,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> "MetadataAgentTool":
        """Create tool from agent handle."""

    def reset_conversation(self) -> None:
        """Reset conversation context for fresh interactions."""
```

### create_metadata_tools

```python
def create_metadata_tools(
    client: MetadataAI,
    agent_names: Optional[list[str]] = None,
) -> list[MetadataAgentTool]:
    """
    Create LangChain tools for multiple Metadata agents.

    Args:
        client: MetadataAI client instance
        agent_names: List of agent names. If None, creates tools
            for all API-enabled agents.

    Returns:
        List of MetadataAgentTool instances
    """
```

## Best Practices

1. **Use descriptive custom names** when the auto-generated name is too long
2. **Provide clear descriptions** to help the LLM choose the right tool
3. **Enable async** for high-throughput applications
4. **Handle rate limits** with retry logic in production
5. **Reset conversations** when starting unrelated tasks
6. **Limit tool count** - too many tools can confuse the LLM

## Troubleshooting

### Tool not being selected

- Check the tool description is clear and relevant
- Ensure the prompt mentions when to use tools
- Try a more capable model (e.g., GPT-4 vs GPT-3.5)

### "Agent not enabled for API access" error

- Enable API access in AI Studio for the agent
- Set `apiEnabled=true` on the agent configuration

### Async not working

- Ensure `enable_async=True` on the MetadataAI client
- Check you're using `await` with async methods
- Verify you're calling `ainvoke` not `invoke` on the executor

### Rate limiting

```python
import time
from ai_sdk.exceptions import RateLimitError

try:
    result = executor.invoke({"input": "..."})
except RateLimitError as e:
    if e.retry_after:
        time.sleep(e.retry_after)
        result = executor.invoke({"input": "..."})
```
