# Standalone Usage Guide

This guide covers using the Metadata AI SDK directly without external frameworks like LangChain.

## Installation

Install the SDK with minimal dependencies:

```bash
pip install metadata-ai
```

Core dependencies are only `httpx` and `pydantic` - no framework lock-in.

## Quick Start

```python
from metadata_ai import MetadataAI

# Initialize client
client = MetadataAI(
    host="https://metadata.example.com",
    token="your-bot-jwt-token"
)

# Invoke an agent
response = client.agent("DataQualityPlannerAgent").call(
    "What data quality tests should I add for the customers table?"
)

print(response.response)

# Cleanup
client.close()
```

## Client Configuration

### Direct Initialization

```python
from metadata_ai import MetadataAI

client = MetadataAI(
    host="https://metadata.example.com",
    token="your-bot-jwt-token",
    timeout=120.0,         # Request timeout in seconds
    verify_ssl=True,       # SSL certificate verification
    enable_async=False,    # Enable async operations
    max_retries=3,         # Retry attempts for transient errors
    retry_delay=1.0,       # Base delay between retries
)
```

### From Environment Variables

```python
from metadata_ai import MetadataAI, MetadataConfig

# Load from environment
config = MetadataConfig.from_env()
client = MetadataAI.from_config(config)
```

Environment variables:
- `METADATA_HOST`: Server URL (required)
- `METADATA_TOKEN`: JWT bot token (required)
- `METADATA_TIMEOUT`: Request timeout in seconds
- `METADATA_VERIFY_SSL`: SSL verification (`true`/`false`)
- `METADATA_DEBUG`: Enable debug logging
- `METADATA_MAX_RETRIES`: Retry attempts
- `METADATA_RETRY_DELAY`: Base retry delay

### With Overrides

```python
# Start from environment, override specific values
config = MetadataConfig.from_env(
    timeout=30.0,
    enable_async=True,
)
client = MetadataAI.from_config(config)
```

### Context Manager

```python
with MetadataAI(host="...", token="...") as client:
    response = client.agent("MyAgent").call("Hello")
    print(response.response)
# Client automatically closed
```

## Agent Invocation

### Simple Call

```python
agent = client.agent("DataQualityPlannerAgent")

response = agent.call("Analyze the customers table")

print(response.response)           # Agent's response text
print(response.conversation_id)    # ID for multi-turn conversations
print(response.tools_used)         # Tools the agent used
print(response.usage)              # Token usage statistics
```

### With Parameters

```python
response = agent.call(
    "Analyze this table",
    parameters={
        "table_name": "customers",
        "schema": "public",
    }
)
```

## Multi-Turn Conversations

### Manual Conversation ID

```python
agent = client.agent("DataQualityPlannerAgent")

# First turn
response1 = agent.call("Analyze the orders table")

# Continue conversation
response2 = agent.call(
    "What specific tests would you recommend?",
    conversation_id=response1.conversation_id
)

# Third turn
response3 = agent.call(
    "Create those tests",
    conversation_id=response2.conversation_id
)
```

### Using Conversation Helper

The `Conversation` class automatically manages conversation context:

```python
from metadata_ai import MetadataAI, Conversation

client = MetadataAI(host="...", token="...")
agent = client.agent("DataQualityPlannerAgent")

# Create conversation
conv = Conversation(agent)

# Send messages - context is automatic
print(conv.send("Analyze the customers table"))
print(conv.send("Now create tests for the issues you found"))
print(conv.send("Show me the SQL for those tests"))

# Access conversation details
print(f"Turns: {len(conv)}")
print(f"Conversation ID: {conv.id}")
print(f"Tools used: {conv.tools_used}")

# Get history
for user_msg, assistant_msg in conv.history:
    print(f"User: {user_msg}")
    print(f"Assistant: {assistant_msg}")

# Start fresh
conv.reset()
```

### Conversation Properties

| Property | Type | Description |
|----------|------|-------------|
| `id` | `str \| None` | Current conversation ID |
| `history` | `list[tuple[str, str]]` | (user, assistant) message pairs |
| `messages` | `list[dict]` | Chat format with `role` and `content` |
| `responses` | `list[InvokeResponse]` | Raw response objects |
| `tools_used` | `list[str]` | All tools used across turns |

## Streaming Responses

Get real-time output as the agent generates:

```python
agent = client.agent("SqlQueryAgent")

for event in agent.stream("Generate SQL to find duplicate records"):
    match event.type:
        case "start":
            print("Agent started...")
        case "content":
            print(event.content, end="", flush=True)
        case "tool_use":
            print(f"\n[Using tool: {event.tool_name}]")
        case "end":
            print("\nDone!")
        case "error":
            print(f"\nError: {event.error}")
```

### Stream Event Types

| Type | Fields | Description |
|------|--------|-------------|
| `start` | `conversation_id` | Agent started processing |
| `content` | `content` | Text chunk from agent |
| `tool_use` | `tool_name` | Agent is using a tool |
| `end` | - | Agent finished |
| `error` | `error` | Error occurred |

### Streaming with Conversation

```python
conv = Conversation(agent)

# Stream first turn
for event in conv.stream("Analyze this table"):
    if event.type == "content":
        print(event.content, end="")

# Note: Streaming doesn't auto-update history
# Use send() for tracked multi-turn conversations
```

## Listing Agents

Discover available API-enabled agents:

```python
agents = client.list_agents(limit=20)

for agent in agents:
    print(f"Name: {agent.name}")
    print(f"Display: {agent.display_name}")
    print(f"Description: {agent.description}")
    print(f"Abilities: {agent.abilities}")
    print(f"API Enabled: {agent.api_enabled}")
    print()
```

### Get Single Agent Info

```python
agent = client.agent("DataQualityPlannerAgent")
info = agent.get_info()

print(info.name)
print(info.description)
print(info.abilities)
```

## Creating Agents

Create new dynamic agents programmatically:

```python
from metadata_ai.models import CreateAgentRequest

# Create a simple agent
agent = client.create_agent(CreateAgentRequest(
    name="MyDataAgent",
    description="An agent for data analysis tasks",
    persona="DataAnalyst",  # Name of an existing persona
    api_enabled=True,
))
print(f"Created agent: {agent.name}")

# Create an agent with full configuration
agent = client.create_agent(CreateAgentRequest(
    name="AdvancedAgent",
    description="An advanced agent with custom configuration",
    persona="DataAnalyst",
    display_name="Advanced Data Agent",
    api_enabled=True,
    abilities=["search", "query", "analyze"],
    prompt="Analyze user data and provide insights",
    provider="openai",
    bot_name="my-bot",  # Bot for executing actions
))
```

### CreateAgentRequest Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `str` | Yes | Unique identifier for the agent |
| `description` | `str` | Yes | Agent description |
| `persona` | `str` | Yes | Name of the persona to use |
| `display_name` | `str` | No | Human-readable name |
| `api_enabled` | `bool` | No | Enable API access (default: False) |
| `abilities` | `list[str]` | No | List of ability names |
| `prompt` | `str` | No | Default task/prompt |
| `provider` | `str` | No | LLM provider |
| `bot_name` | `str` | No | Bot for executing actions |
| `mode` | `str` | No | Agent mode |
| `icon` | `str` | No | Icon URL or name |
| `knowledge` | `list[str]` | No | Knowledge sources |
| `schedule` | `str` | No | Cron schedule |

## Bot Operations

Bots are service accounts used for API authentication and actions.

```python
# List all bots
bots = client.list_bots(limit=20)
for bot in bots:
    print(f"{bot.name}: {bot.display_name}")

# Get a specific bot
bot = client.get_bot("my-bot-name")
print(f"Bot: {bot.name}")
print(f"Display Name: {bot.display_name}")
```

### BotInfo Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Bot identifier |
| `display_name` | `str` | Human-readable name |
| `description` | `str` | Bot description |

### Bot Errors

```python
from metadata_ai.exceptions import BotNotFoundError

try:
    bot = client.get_bot("nonexistent-bot")
except BotNotFoundError as e:
    print(f"Bot not found: {e.bot_name}")
```

## Persona Operations

Personas define the behavior and personality of agents.

```python
from metadata_ai.models import CreatePersonaRequest

# List all personas
personas = client.list_personas(limit=20)
for persona in personas:
    print(f"{persona.name}: {persona.description}")

# Get a specific persona
persona = client.get_persona("DataAnalyst")
print(f"Persona: {persona.name}")
print(f"Prompt: {persona.prompt[:100]}...")

# Create a new persona
new_persona = client.create_persona(CreatePersonaRequest(
    name="CustomAnalyst",
    description="A specialized analyst for custom domains",
    prompt="You are an expert analyst who helps users understand complex data...",
))
print(f"Created persona: {new_persona.name}")
```

### CreatePersonaRequest Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `str` | Yes | Unique identifier |
| `description` | `str` | Yes | Persona description |
| `prompt` | `str` | Yes | System prompt defining behavior |
| `display_name` | `str` | No | Human-readable name |
| `provider` | `str` | No | LLM provider |

### PersonaInfo Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Persona identifier |
| `display_name` | `str` | Human-readable name |
| `description` | `str` | Persona description |
| `prompt` | `str` | System prompt |

### Persona Errors

```python
from metadata_ai.exceptions import PersonaNotFoundError

try:
    persona = client.get_persona("nonexistent")
except PersonaNotFoundError as e:
    print(f"Persona not found: {e.persona_name}")
```

## Ability Operations

Abilities are capabilities that can be assigned to agents.

```python
# List all abilities
abilities = client.list_abilities(limit=50)
for ability in abilities:
    print(f"{ability.name}: {ability.description}")

# Get a specific ability
ability = client.get_ability("search")
print(f"Ability: {ability.name}")
print(f"Description: {ability.description}")
```

### AbilityInfo Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Ability identifier |
| `display_name` | `str` | Human-readable name |
| `description` | `str` | Ability description |

### Ability Errors

```python
from metadata_ai.exceptions import AbilityNotFoundError

try:
    ability = client.get_ability("nonexistent")
except AbilityNotFoundError as e:
    print(f"Ability not found: {e.ability_name}")
```

## Async Operations

Enable async for concurrent operations:

```python
import asyncio
from metadata_ai import MetadataAI

async def main():
    client = MetadataAI(
        host="https://metadata.example.com",
        token="your-token",
        enable_async=True  # Required
    )

    agent = client.agent("DataQualityPlannerAgent")

    # Async call
    response = await agent.acall("Analyze the orders table")
    print(response.response)

    # Async streaming
    async for event in await agent.astream("Generate SQL query"):
        if event.type == "content":
            print(event.content, end="")

    # Async list
    agents = await client.alist_agents()

    # Cleanup
    await client.aclose()
    client.close()

asyncio.run(main())
```

### Async Conversation

```python
from metadata_ai import Conversation

async def chat():
    client = MetadataAI(host="...", token="...", enable_async=True)
    conv = Conversation(client.agent("MyAgent"))

    # Async send
    response1 = await conv.asend("First message")
    response2 = await conv.asend("Follow up")

    # Async stream
    async for event in await conv.astream("Stream this"):
        print(event.content, end="")
```

### Async Context Manager

```python
async with MetadataAI(host="...", token="...", enable_async=True) as client:
    response = await client.agent("MyAgent").acall("Hello")
```

## Error Handling

Handle specific error types:

```python
from metadata_ai import MetadataAI
from metadata_ai.exceptions import (
    MetadataError,
    AuthenticationError,
    AgentNotFoundError,
    AgentNotEnabledError,
    RateLimitError,
    AgentExecutionError,
)

client = MetadataAI(host="...", token="...")

try:
    response = client.agent("MyAgent").call("Hello")
    print(response.response)

except AuthenticationError:
    print("Invalid or expired token")
    print("Check your METADATA_TOKEN")

except AgentNotFoundError as e:
    print(f"Agent not found: {e.agent_name}")
    print("Verify the agent exists in your Metadata instance")

except AgentNotEnabledError as e:
    print(f"Agent '{e.agent_name}' is not API-enabled")
    print("Enable API access in AI Studio")

except RateLimitError as e:
    print(f"Rate limited. Retry after: {e.retry_after} seconds")
    if e.retry_after:
        time.sleep(e.retry_after)

except AgentExecutionError as e:
    print(f"Agent execution failed: {e.message}")

except MetadataError as e:
    print(f"Metadata error ({e.status_code}): {e.message}")
```

### Exception Hierarchy

```
MetadataError (base)
├── AuthenticationError (401)
├── AgentNotFoundError (404)
├── AgentNotEnabledError (403)
├── BotNotFoundError (404)
├── PersonaNotFoundError (404)
├── AbilityNotFoundError (404)
├── RateLimitError (429)
└── AgentExecutionError (500)
```

## Debug Logging

Enable verbose logging for debugging:

```python
from metadata_ai import MetadataConfig, MetadataAI
from metadata_ai._logging import set_debug

# Option 1: Via config
config = MetadataConfig.from_env(debug=True)
client = MetadataAI.from_config(config)

# Option 2: Direct toggle
set_debug(True)
```

### Custom Logging Configuration

```python
from metadata_ai._logging import configure_logging
import logging

# Custom format
configure_logging(
    level=logging.DEBUG,
    format_string="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Or use your own handler
handler = logging.FileHandler("metadata.log")
configure_logging(handler=handler)
```

## Testing with Mocks

Use the ABC interfaces for testing:

```python
from metadata_ai.protocols import AgentProtocol
from metadata_ai.models import InvokeResponse

class MockAgent(AgentProtocol):
    """Mock agent for testing."""

    def __init__(self, responses: list[str]):
        self._responses = iter(responses)

    @property
    def name(self) -> str:
        return "MockAgent"

    def call(self, message, **kwargs) -> InvokeResponse:
        return InvokeResponse(
            conversation_id="mock-123",
            response=next(self._responses),
            tools_used=[],
        )

    # Implement other abstract methods...

# Use in tests
def test_my_function():
    mock = MockAgent(["Response 1", "Response 2"])
    result = my_function(mock)
    assert result == expected
```

## Data Models

### InvokeResponse

```python
response = agent.call("...")

response.conversation_id  # str - For multi-turn
response.response         # str - Agent's response
response.tools_used       # list[str] - Tools used
response.usage            # Usage | None - Token stats
```

### Usage

```python
if response.usage:
    print(response.usage.prompt_tokens)
    print(response.usage.completion_tokens)
    print(response.usage.total_tokens)
```

### StreamEvent

```python
event.type            # str - Event type
event.content         # str | None - Text content
event.tool_name       # str | None - Tool being used
event.conversation_id # str | None - Conversation ID
event.error           # str | None - Error message
```

### AgentInfo

```python
info = agent.get_info()

info.name          # str - Agent identifier
info.display_name  # str - Human-readable name
info.description   # str - Agent description
info.abilities     # list[str] - Capabilities
info.api_enabled   # bool - API access enabled
```

## Complete Example

```python
#!/usr/bin/env python3
"""Complete standalone SDK usage example."""

import sys
from metadata_ai import MetadataAI, MetadataConfig, Conversation
from metadata_ai.models import CreatePersonaRequest, CreateAgentRequest
from metadata_ai.exceptions import MetadataError

def main():
    # Load configuration
    try:
        config = MetadataConfig.from_env()
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Set METADATA_HOST and METADATA_TOKEN environment variables")
        sys.exit(1)

    # Create client
    client = MetadataAI.from_config(config)

    try:
        # List available agents
        print("Available agents:")
        for agent in client.list_agents():
            print(f"  - {agent.name}: {agent.description[:50]}...")

        # List bots
        print("\n--- Bots ---")
        for bot in client.list_bots():
            print(f"  - {bot.name}: {bot.display_name}")

        # List personas
        print("\n--- Personas ---")
        for persona in client.list_personas():
            print(f"  - {persona.name}: {persona.description[:50]}...")

        # List abilities
        print("\n--- Abilities ---")
        for ability in client.list_abilities():
            print(f"  - {ability.name}: {ability.description[:50]}...")

        # Simple invocation
        print("\n--- Simple Invocation ---")
        agent = client.agent("DataQualityPlannerAgent")
        response = agent.call("What should I test for a customers table?")
        print(response.response[:500])

        # Multi-turn conversation
        print("\n--- Multi-turn Conversation ---")
        conv = Conversation(agent)
        print(conv.send("Analyze the orders table"))
        print(conv.send("Create tests for the top issue"))
        print(f"\nConversation had {len(conv)} turns")

        # Streaming
        print("\n--- Streaming ---")
        for event in agent.stream("Generate a simple SQL query"):
            if event.type == "content" and event.content:
                print(event.content, end="", flush=True)
        print()

        # Create a persona (uncomment to run)
        # print("\n--- Create Persona ---")
        # persona = client.create_persona(CreatePersonaRequest(
        #     name="MyCustomPersona",
        #     description="A custom persona for testing",
        #     prompt="You are a helpful assistant..."
        # ))
        # print(f"Created persona: {persona.name}")

        # Create an agent (uncomment to run)
        # print("\n--- Create Agent ---")
        # new_agent = client.create_agent(CreateAgentRequest(
        #     name="MyCustomAgent",
        #     description="A custom agent for testing",
        #     persona="DataAnalyst",
        #     api_enabled=True,
        # ))
        # print(f"Created agent: {new_agent.name}")

    except MetadataError as e:
        print(f"Error: {e}")
        sys.exit(1)

    finally:
        client.close()

if __name__ == "__main__":
    main()
```

## Best Practices

1. **Use context managers** - Ensure proper cleanup
2. **Handle specific exceptions** - Don't catch generic `Exception`
3. **Use Conversation for multi-turn** - Avoid manual ID tracking
4. **Enable async for concurrency** - Better throughput
5. **Configure logging in production** - Integrate with your logging
6. **Use environment config** - Keep secrets out of code

## API Reference

See the inline documentation for complete API details:

```python
from metadata_ai import MetadataAI
help(MetadataAI)

from metadata_ai import Conversation
help(Conversation)
```
