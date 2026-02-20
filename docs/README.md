# AI SDK Documentation

Python SDK for invoking Dynamic Agents from [OpenMetadata](https://open-metadata.org/) / [Collate](https://www.getcollate.io/).

## What is this SDK?

The AI SDK lets you programmatically invoke **Dynamic Agents** - AI-powered assistants that can analyze your data catalog, generate SQL queries, plan data quality tests, explore lineage, and more. These agents run on your OpenMetadata or Collate instance and have full access to your metadata context.

**Use cases:**
- Automate data quality test generation
- Build chatbots that understand your data catalog
- Integrate metadata intelligence into your data pipelines
- Create LangChain tools backed by your metadata context

## Prerequisites

Before using this SDK, you need:

1. **An OpenMetadata or Collate instance** with Dynamic Agents enabled
2. **A Bot with a JWT token** for API authentication

### Getting Your Credentials

#### 1. Find your host URL

Your `AI_SDK_HOST` is your OpenMetadata/Collate server URL:
- **Collate Cloud**: `https://your-org.getcollate.io`
- **Self-hosted OpenMetadata**: `https://your-openmetadata-server.com`

#### 2. Create a Bot and get the JWT token

1. Log into your OpenMetadata/Collate instance as an admin
2. Go to **Settings** > **Bots**
3. Click **Add Bot** (or use an existing bot)
4. Give it a name (e.g., `sdk-bot`) and appropriate permissions
5. Under **Token**, click **Generate Token** or copy the existing JWT token
6. This JWT token is your `AI_SDK_TOKEN`

**Security tip:** Treat this token like a password. Don't commit it to version control.

## Guides

| Guide | Description |
|-------|-------------|
| [Quick Start](quickstart.md) | Get started in 5 minutes |
| [Standalone Usage](standalone.md) | Complete standalone documentation |
| [Async Usage](async.md) | Async patterns and best practices |
| [Error Handling](error-handling.md) | Exception handling patterns |
| [LangChain Integration](langchain.md) | Use Dynamic Agents with LangChain |
| [MCP Tools](mcp.md) | Use MCP tools with LangChain/OpenAI |
| [Releasing](releasing.md) | How to publish a new SDK release |

## Installation

```bash
# Core SDK (standalone)
pip install ai-sdk

# With LangChain support
pip install ai-sdk[langchain]

# All optional dependencies
pip install ai-sdk[all]
```

## Quick Example

First, set your environment variables:

```bash
# Your OpenMetadata/Collate server URL
export AI_SDK_HOST="https://your-org.getcollate.io"

# Your bot's JWT token (from Settings > Bots)
export AI_SDK_TOKEN="eyJhbGciOiJSUzI1NiIs..."
```

Then use the SDK:

```python
from ai_sdk import AiSdk, AiSdkConfig, Conversation

# Create client (reads AI_SDK_HOST and AI_SDK_TOKEN from environment)
config = AiSdkConfig.from_env()
client = AiSdk.from_config(config)

# Invoke an agent
response = client.agent("DataQualityPlannerAgent").call(
    "What tests should I add for the customers table?"
)
print(response.response)

# Multi-turn conversation (agent remembers context)
conv = Conversation(client.agent("DataQualityPlannerAgent"))
print(conv.send("Analyze the customers table"))
print(conv.send("Create tests for the issues you found"))

client.close()
```

## Features

- **Standalone usage** - No framework dependencies required
- **Multi-turn conversations** - Automatic context tracking
- **Streaming responses** - Real-time output
- **Async support** - Full async/await API
- **Framework integrations** - LangChain (more coming)
- **Type hints** - Full type coverage
- **Error handling** - Structured exception hierarchy
- **Management APIs** - Create and manage agents, personas, bots, and abilities

## Requirements

- Python 3.9+
- httpx
- pydantic

## Links

- [GitHub](https://github.com/open-metadata/metadata-ai-sdk)
- [PyPI](https://pypi.org/project/ai-sdk/)
- [OpenMetadata Documentation](https://docs.open-metadata.org/)
- [Collate Documentation](https://docs.getcollate.io/)
