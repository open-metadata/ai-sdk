# Metadata AI Python SDK

Python SDK for invoking [Metadata](https://open-metadata.org) Dynamic Agents from your AI applications.

## Installation

```bash
pip install metadata-ai
```

With LangChain integration:

```bash
pip install metadata-ai[langchain]
```

## Quick Start

```python
from metadata_ai import MetadataAI

client = MetadataAI(
    host="https://your-metadata-instance.com",
    token="your-bot-jwt-token"
)

response = client.agent("DataQualityPlannerAgent").call(
    "What data quality tests should I add for the customers table?"
)
print(response.response)
```

## Streaming

```python
for event in client.agent("DataQualityPlannerAgent").stream("Analyze the customers table"):
    if event.event_type == "message":
        print(event.content, end="", flush=True)
```

## Async Support

```python
import asyncio
from metadata_ai import MetadataAI

async def main():
    client = MetadataAI(
        host="https://your-metadata-instance.com",
        token="your-bot-jwt-token",
        enable_async=True,
    )
    response = await client.agent("DataQualityPlannerAgent").acall(
        "Analyze the customers table"
    )
    print(response.response)

asyncio.run(main())
```

## MCP Tools

Access [Model Context Protocol](https://modelcontextprotocol.io/) tools from your Metadata instance:

```python
tools = client.mcp.list_tools()

result = client.mcp.call_tool(
    tool=MCPTool.SEARCH_ENTITIES,
    arguments={"query": "customers", "limit": 5},
)
```

## Documentation

- [Full SDK docs](https://docs.open-metadata.org/sdk)
- [Source & all SDKs](https://github.com/open-metadata/metadata-ai-sdk)

## License

Collate Community License 1.0
