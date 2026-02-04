# Metadata AI SDK - Quick Start

Get started with the Metadata AI SDK in under 5 minutes.

## Installation

```bash
pip install metadata-ai
```

## Set Environment Variables

```bash
export METADATA_HOST="https://your-metadata-instance.com"
export METADATA_TOKEN="your-bot-jwt-token"
```

## Basic Usage

```python
from metadata_ai import MetadataAI, MetadataConfig

# Create client from environment
config = MetadataConfig.from_env()
client = MetadataAI.from_config(config)

# Invoke an agent
response = client.agent("DataQualityPlannerAgent").call(
    "What data quality tests should I add?"
)

print(response.response)
client.close()
```

## Multi-Turn Conversation

```python
from metadata_ai import Conversation

conv = Conversation(client.agent("DataQualityPlannerAgent"))

print(conv.send("Analyze the customers table"))
print(conv.send("Create tests for the issues you found"))
```

## Streaming

```python
for event in client.agent("SqlQueryAgent").stream("Generate a query"):
    if event.type == "content":
        print(event.content, end="", flush=True)
```

## Async

```python
import asyncio

async def main():
    client = MetadataAI.from_config(
        MetadataConfig.from_env(enable_async=True)
    )
    response = await client.agent("MyAgent").acall("Hello")
    print(response.response)
    await client.aclose()

asyncio.run(main())
```

## Management APIs

The SDK also supports creating and managing resources:

```python
# List bots, personas, and abilities
bots = client.list_bots()
personas = client.list_personas()
abilities = client.list_abilities()

# Create a persona
from metadata_ai.models import CreatePersonaRequest
persona = client.create_persona(CreatePersonaRequest(
    name="MyPersona",
    description="A helpful analyst",
    prompt="You are a helpful data analyst..."
))

# Create an agent
from metadata_ai.models import CreateAgentRequest
agent = client.create_agent(CreateAgentRequest(
    name="MyAgent",
    description="Custom agent",
    persona="MyPersona",
    api_enabled=True,
))
```

## Next Steps

- [Standalone Usage Guide](standalone.md) - Complete standalone documentation
- [LangChain Integration](langchain.md) - Use with LangChain
- [Examples](../examples/) - Code examples

## Need Help?

- [API Documentation](https://docs.open-metadata.org/sdk)
- [GitHub Issues](https://github.com/open-metadata/metadata-ai-sdk/issues)
