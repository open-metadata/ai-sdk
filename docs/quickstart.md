# AI SDK - Quick Start

Get started with the AI SDK in under 5 minutes.

## Prerequisites

You need:
1. **An OpenMetadata or Collate instance** with Dynamic Agents enabled
2. **A Bot JWT token** for API authentication

If you don't have a token yet, see [Getting Your Credentials](README.md#getting-your-credentials) in the main documentation.

## Installation

```bash
pip install ai-sdk
```

## Set Environment Variables

```bash
# Your OpenMetadata/Collate server URL
# Examples:
#   Collate Cloud: https://your-org.getcollate.io
#   Self-hosted:   https://openmetadata.yourcompany.com
export AI_SDK_HOST="https://your-org.getcollate.io"

# Your bot's JWT token (from Settings > Bots in your instance)
# This is a long base64-encoded string starting with "eyJ..."
export AI_SDK_TOKEN="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Note:** Never commit tokens to version control. Use environment variables, `.env` files (with `.gitignore`), or secrets management.

## Basic Usage

```python
from ai_sdk import AiSdk, AiSdkConfig

# Create client from environment
config = AiSdkConfig.from_env()
client = AiSdk.from_config(config)

# Invoke an agent
response = client.agent("DataQualityPlannerAgent").call(
    "What data quality tests should I add?"
)

print(response.response)
client.close()
```

## Multi-Turn Conversation

```python
from ai_sdk import Conversation

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
    client = AiSdk.from_config(
        AiSdkConfig.from_env(enable_async=True)
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
from ai_sdk.models import CreatePersonaRequest
persona = client.create_persona(CreatePersonaRequest(
    name="MyPersona",
    description="A helpful analyst",
    prompt="You are a helpful data analyst..."
))

# Create an agent
from ai_sdk.models import CreateAgentRequest
agent = client.create_agent(CreateAgentRequest(
    name="MyAgent",
    description="Custom agent",
    persona="MyPersona",
    api_enabled=True,
))
```

## Next Steps

- [Standalone Usage Guide](standalone.md) - Complete standalone documentation
- [Async Usage](async.md) - Async patterns and best practices
- [Error Handling](error-handling.md) - Exception handling patterns
- [LangChain Integration](langchain.md) - Use with LangChain

## Troubleshooting

### "Missing AI_SDK_HOST environment variable"

You haven't set the required environment variables. Run:

```bash
export AI_SDK_HOST="https://your-org.getcollate.io"
export AI_SDK_TOKEN="your-jwt-token"
```

### "Authentication failed" or 401 error

Your JWT token is invalid or expired. Generate a new one:
1. Go to Settings > Bots in your OpenMetadata/Collate instance
2. Select your bot and regenerate the token
3. Update your `AI_SDK_TOKEN` environment variable

### "Agent not found" or 404 error

The agent name doesn't exist or isn't API-enabled:
1. Check the exact agent name (case-sensitive)
2. Verify the agent exists in your instance under AI Studio
3. Ensure "API Enabled" is turned on for the agent

### "Agent not enabled for API access" or 403 error

The agent exists but isn't enabled for API use:
1. Go to AI Studio in your OpenMetadata/Collate instance
2. Edit the agent
3. Enable the "API Enabled" toggle
4. Save the agent

### SSL certificate errors

If using self-hosted OpenMetadata with self-signed certificates:

```python
client = AiSdk(
    host="https://your-server.com",
    token="your-token",
    verify_ssl=False  # Disable SSL verification (not recommended for production)
)
```

Or set the environment variable:

```bash
export AI_SDK_VERIFY_SSL="false"
```

## Need Help?

- [OpenMetadata Documentation](https://docs.open-metadata.org/)
- [Collate Documentation](https://docs.getcollate.io/)
- [GitHub Issues](https://github.com/open-metadata/metadata-ai-sdk/issues)
