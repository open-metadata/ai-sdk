# Metadata AI SDK Documentation

Python SDK for Metadata AI Agents - Semantic Intelligence for AI builders.

## Overview

The Metadata AI SDK provides a simple, Pythonic interface to invoke Metadata Dynamic Agents from your AI applications. Use it standalone or integrate with frameworks like LangChain.

## Guides

| Guide | Description |
|-------|-------------|
| [Quick Start](quickstart.md) | Get started in 5 minutes |
| [Standalone Usage](standalone.md) | Complete standalone documentation |
| [Async Usage](async.md) | Async patterns and best practices |
| [Error Handling](error-handling.md) | Exception handling patterns |
| [LangChain Integration](langchain.md) | Use with LangChain |

## Installation

```bash
# Core SDK (standalone)
pip install metadata-ai

# With LangChain support
pip install metadata-ai[langchain]

# All optional dependencies
pip install metadata-ai[all]
```

## Quick Example

```python
from metadata_ai import MetadataAI, MetadataConfig, Conversation

# Create client
config = MetadataConfig.from_env()
client = MetadataAI.from_config(config)

# Simple call
response = client.agent("DataQualityPlannerAgent").call(
    "What tests should I add?"
)
print(response.response)

# Multi-turn conversation
conv = Conversation(client.agent("DataQualityPlannerAgent"))
print(conv.send("Analyze the customers table"))
print(conv.send("Create tests for the issues"))

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

- [Examples](../examples/)
- [API Reference](https://docs.open-metadata.org/sdk)
- [GitHub](https://github.com/open-metadata/metadata-ai-sdk)
- [PyPI](https://pypi.org/project/metadata-ai/)
