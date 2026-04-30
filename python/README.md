# AI SDK for Python

Python SDK for invoking [Metadata](https://open-metadata.org) Dynamic Agents from your AI applications.

## Installation

```bash
pip install data-ai-sdk
```

With LangChain integration:

```bash
pip install data-ai-sdk[langchain]
```

## Quick Start

```python
from ai_sdk import AISdk

client = AISdk(
    host="https://your-metadata-instance.com",
    token="your-bot-jwt-token"
)

# default AskCollate agent
response = client.agent().call("What data quality tests should I add for the customers table?")
print(response.response)

# Named dynamic agent
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
from ai_sdk import AISdk

async def main():
    client = AISdk(
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

## Context Memories

The `client.memories` namespace manages reusable Context Center knowledge — preferences, use cases, runbooks, and FAQs that any AI agent can read.

```python
from ai_sdk import (
    AISdk,
    CreateContextMemoryRequest,
    EntityReference,
    MemoryType,
    MemoryVisibility,
)

# Create
created = client.memories.create(CreateContextMemoryRequest(
    name="orders-grain",
    title="Orders grain",
    question="What is the grain of the orders table?",
    answer="One row per order_id.",
    memory_type=MemoryType.NOTE,             # Preference | UseCase | Note | Runbook | Faq
    visibility=MemoryVisibility.SHARED,      # Private | Entity | Shared
    primary_entity=EntityReference(id="<table-uuid>", type="table"),
    tags=["Domain.Analytics"],
))

# Get / list (filter by entity FQN, optional limit)
client.memories.get(created.id)
client.memories.list(primary_entity_fqn="prod.warehouse.orders", limit=50)

# Hybrid NLQ search — combines vector + keyword ranking over the contextMemory index.
# Optional filters scope the search by indexed fields.
results = client.memories.search(
    "how do we measure order volume",
    filters={"visibility": ["Entity", "Shared"]},
    size=10,
    from_=0,
)
for hit in results.hits:
    print(f"[{hit.score:.2f}] {hit.memory.title}: {hit.memory.answer}")

# Soft delete by default; pass hard_delete=True to remove permanently
client.memories.delete(created.id)
client.memories.delete(created.id, hard_delete=True)
```

### Async

Every method has an `aXxx` counterpart when the client is constructed with `enable_async=True`:

```python
client = AISdk(host=..., token=..., enable_async=True)

await client.memories.acreate(req)
await client.memories.alist(primary_entity_fqn="prod.warehouse.orders")
await client.memories.aget(memory_id)
await client.memories.asearch("explain customer churn")
await client.memories.adelete(memory_id)
```

### What's stored

| Field | Notes |
|-------|-------|
| `name` | Stable system name (required) |
| `question` / `answer` | Canonical Q/A pair (required) — what an agent retrieves |
| `title`, `description`, `summary` | Human-facing text, optional |
| `memory_type` | `Preference`, `UseCase`, `Note`, `Runbook`, or `Faq` |
| `memory_scope` | `EntityScoped` (default) or `UserGlobal` |
| `visibility` | `Private`, `Entity`, or `Shared` (controls who can read it) |
| `primary_entity` | Attaches the memory to a specific asset for entity-scoped recall |
| `tags` | List of tag FQN strings (e.g. `"PII.Sensitive"`) |

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
- [Source & all SDKs](https://github.com/open-metadata/ai-sdk)

## License

Collate Community License 1.0
