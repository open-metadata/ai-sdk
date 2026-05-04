# AI SDK

Bring AI to your metadata. The OpenMetadata AI SDK gives you programmatic access to your data catalog through two complementary paths: **MCP tools** for building custom AI applications with any LLM, and **Dynamic Agents** for invoking ready-to-use AI assistants from [Collate's AI Studio](https://www.getcollate.io).

| SDK | Package | Install |
|-----|---------|---------|
| Python | [`data-ai-sdk`](https://pypi.org/project/data-ai-sdk/) | `pip install data-ai-sdk` |
| TypeScript | [`@openmetadata/ai-sdk`](https://www.npmjs.com/package/@openmetadata/ai-sdk) | `npm install @openmetadata/ai-sdk` |
| Java | [`org.open-metadata:ai-sdk`](https://central.sonatype.com/artifact/org.open-metadata/ai-sdk) | Maven / Gradle |
| CLI | [`ai-sdk`](https://github.com/open-metadata/ai-sdk/releases) | [Install script](#cli-1) |
| n8n | [`n8n-nodes-metadata`](n8n-nodes-metadata/) | n8n community node |

## Why This SDK?

### MCP Tools — Your catalog as an AI toolkit

OpenMetadata exposes an [MCP server](https://modelcontextprotocol.io/) at `/mcp` that turns your catalog into a set of tools any LLM can use. Unlike generic MCP connectors that only read raw database schemas, OpenMetadata's MCP tools give your AI access to the **full context** of your data platform:

- **Semantic search** — Find assets by meaning, not just name. Search across tables, dashboards, pipelines, and more with catalog-aware ranking.
- **Lineage traversal** — Trace upstream sources and downstream impact across your entire data estate. Understand how a schema change propagates before it breaks anything.
- **Glossary & classification** — Read and write business definitions, tags, and PII classifications. Your AI doesn't just find data — it understands what it means.
- **Catalog mutations** — Create glossary terms, update descriptions, add lineage edges, and patch entities. Go beyond read-only exploration to actually curate your catalog.
- **Framework adapters** — First-class integration with LangChain and OpenAI function calling. Convert MCP tools with a single method call, with built-in include/exclude filtering for safety control.

```python
# Build a custom LangChain agent backed by your catalog
from ai_sdk import AISdk, AISdkConfig

client = AISdk.from_config(AISdkConfig.from_env())

# Convert catalog tools to LangChain format — one line
tools = client.mcp.as_langchain_tools()

# Or call tools directly
result = client.mcp.call_tool("search_metadata", {"query": "customers"})
```

### Collate Agents — Pre-built AI assistants from AI Studio

With [Collate](https://www.getcollate.io), you get access to **AI Studio** — a platform for creating and managing AI agents that are purpose-built for data teams. Each agent combines a persona, a set of abilities, and full catalog access into a ready-to-use assistant you can invoke from any SDK:

```python
from ai_sdk import AISdk

client = AISdk(
    host="https://your-org.getcollate.io",
    token="your-bot-jwt-token"
)

# Invoke a pre-built agent
response = client.agent("DataQualityPlannerAgent").call(
    "What data quality tests should I add for the customers table?"
)
print(response.response)
```

Agents support **streaming**, **multi-turn conversations**, and **async** out of the box. You can also create and manage agents programmatically — define personas, assign abilities, and deploy custom agents through the SDK.

## Quick Start

### Python

```bash
pip install data-ai-sdk
```

```python
from ai_sdk import AISdk, AISdkConfig

config = AISdkConfig.from_env()  # reads AI_SDK_HOST and AI_SDK_TOKEN
client = AISdk.from_config(config)

# default AskCollate agent
response = client.agent().call("What data quality tests should I add?")
print(response.response)

# Named dynamic agent
response = client.agent("DataQualityPlannerAgent").call(
    "What data quality tests should I add for the customers table?"
)
print(response.response)

# Stream responses in real time (works with both)
for event in client.agent().stream("Analyze the orders table"):
    if event.type == "content":
        print(event.content, end="", flush=True)
```

### TypeScript

```bash
npm install @openmetadata/ai-sdk
```

```typescript
import { AISdk } from '@openmetadata/ai-sdk';

const client = new AISdk({
  host: 'https://your-org.getcollate.io',
  token: 'your-bot-jwt-token'
});

// default AskCollate agent
const defaultResponse = await client.agent().invoke('What tables have quality issues?');
console.log(defaultResponse.response);

// Named dynamic agent
const response = await client.agent('DataQualityPlannerAgent').invoke(
  'What data quality tests should I add for the customers table?'
);
console.log(response.response);

// Stream responses (works with both)
for await (const event of client.agent().stream('Analyze data quality')) {
  if (event.type === 'content') {
    process.stdout.write(event.content || '');
  }
}
```

Zero runtime dependencies. Works in Node.js 18+, browsers, Deno, and Bun.

### Java

```xml
<dependency>
  <groupId>org.open-metadata</groupId>
  <artifactId>ai-sdk</artifactId>
  <version>0.1.0</version>
</dependency>
```

```java
import io.openmetadata.ai.AISdk;

AISdk client = new AISdk.Builder()
    .host("https://your-org.getcollate.io")
    .token("your-bot-jwt-token")
    .build();

// default AskCollate agent
InvokeResponse defaultResponse = client.agent()
    .invoke("What data quality tests should I add?");
System.out.println(defaultResponse.getResponse());

// Named dynamic agent
InvokeResponse response = client.agent("DataQualityPlannerAgent")
    .invoke("What data quality tests should I add?");
System.out.println(response.getResponse());
```

### CLI

```bash
# Install
curl -sSL https://raw.githubusercontent.com/open-metadata/ai-sdk/main/cli/install.sh | sh

# Configure
ai-sdk configure

# Use the TUI to chat
ai-sdk chat --profile local

# default AskCollate agent
ai-sdk invoke --default "Analyze the customers table"

# Named dynamic agent
ai-sdk invoke DataQualityPlannerAgent "Analyze the customers table"
```

Interactive TUI with markdown rendering and syntax highlighting.

## Context Memories

OpenMetadata's **Context Center** stores reusable knowledge — user preferences, use cases, runbooks, and FAQs — that any AI agent can read on demand. Each memory has a canonical question/answer pair, a type, and an optional `primaryEntity` so it can be retrieved when working with a specific table, dashboard, or pipeline.

The `client.memories` namespace exposes the full lifecycle. **Hybrid search** combines vector similarity with keyword ranking over the `contextMemory` index — pass a natural-language query and an optional filter map; you get back hits ranked by relevance.

### Python

```python
from ai_sdk import AISdk, CreateContextMemoryRequest, MemoryType, MemoryVisibility

client = AISdk.from_config(AISdkConfig.from_env())

# Create a memory tied to a specific table
created = client.memories.create(CreateContextMemoryRequest(
    name="orders-grain",
    title="Orders grain",
    question="What is the grain of the orders table?",
    answer="One row per order_id; payments roll up to this grain.",
    memory_type=MemoryType.NOTE,
    visibility=MemoryVisibility.SHARED,
    primary_entity=EntityReference(id="<table-uuid>", type="table"),
))

# List memories attached to that asset
for m in client.memories.list(primary_entity_fqn="prod.warehouse.orders"):
    print(m.title)

# Hybrid NLQ search
results = client.memories.search("how do we measure order volume", size=5)
for hit in results.hits:
    print(f"[{hit.score:.2f}] {hit.memory.title}")

# Soft delete (use hard_delete=True to remove permanently)
client.memories.delete(created.id)
```

### TypeScript

```typescript
const created = await client.memories.create({
  name: 'orders-grain',
  title: 'Orders grain',
  question: 'What is the grain of the orders table?',
  answer: 'One row per order_id; payments roll up to this grain.',
  memoryType: 'Note',
  visibility: 'Shared',
  primaryEntity: { id: '<table-uuid>', type: 'table' },
});

for (const m of await client.memories.list({ primaryEntityFqn: 'prod.warehouse.orders' })) {
  console.log(m.title);
}

const results = await client.memories.search('how do we measure order volume', { size: 5 });
for (const hit of results.hits) {
  console.log(`[${hit.score.toFixed(2)}] ${hit.memory.title}`);
}

await client.memories.delete(created.id);
```

### Java

```java
import io.openmetadata.ai.models.*;

ContextMemory created = client.memories().create(
    CreateContextMemoryRequest.builder()
        .name("orders-grain")
        .title("Orders grain")
        .question("What is the grain of the orders table?")
        .answer("One row per order_id; payments roll up to this grain.")
        .memoryType(MemoryType.NOTE)
        .visibility(MemoryVisibility.SHARED)
        .primaryEntity(EntityReference.builder().id("<table-uuid>").type("table").build())
        .build()
);

for (ContextMemory m : client.memories().list("prod.warehouse.orders", null)) {
    System.out.println(m.getTitle());
}

MemorySearchResults results = client.memories().search(
    "how do we measure order volume", null, 5, 0
);
for (MemorySearchHit hit : results.getHits()) {
    System.out.printf("[%.2f] %s%n", hit.getScore(), hit.getMemory().getTitle());
}

client.memories().delete(created.getId());
```

### CLI

```bash
# Create
ai-sdk memories create \
  --name orders-grain \
  --title "Orders grain" \
  --question "What is the grain of the orders table?" \
  --answer "One row per order_id; payments roll up to this grain." \
  --memory-type note \
  --visibility shared \
  --primary-entity-id <table-uuid> --primary-entity-type table

# List by entity
ai-sdk memories list --entity-fqn prod.warehouse.orders

# Hybrid NLQ search (use --json to pipe into jq)
ai-sdk memories search "how do we measure order volume" --size 5 --json

# Delete (add --hard for permanent)
ai-sdk memories delete <memory-id>
```

**Filtering search results.** Pass a JSON filter map to scope by entity, visibility, or any indexed field:

```python
client.memories.search(
    "explain churn",
    filters={"primaryEntityId": ["<uuid>"], "visibility": ["Entity", "Shared"]},
)
```

See each SDK's README for the full surface (sync + async, all enum values, model fields).

## Cookbook

Real-world examples showing how teams use the AI SDK in production workflows.

| Use Case | What It Does | Stack |
|----------|-------------|-------|
| [MCP Impact Analysis](cookbook/mcp-impact-analysis/) | AI-powered impact analysis for schema changes — run in CI to catch breaking changes before they ship | Python SDK, LangChain |
| [DQ Failure Slack Notifications](cookbook/dq-failure-slack-notifications/) | Automatically analyze Data Quality failures and post root-cause summaries to Slack | n8n, Slack |
| [dbt Model PR Review](cookbook/dbt-pr-review/) | GitHub Action that reviews dbt model changes for downstream impact and DQ risks on every PR | GitHub Actions, Python SDK |
| [GDPR DSAR Compliance](cookbook/gdpr-dsar-compliance/) | Trace PII across your catalog to handle data deletion and access requests | TypeScript SDK, Browser |
| [MCP Metadata Chatbot](cookbook/mcp-metadata-chatbot/) | Multi-agent chatbot with specialist agents for discovery, lineage, and curation | Python SDK, LangChain |

Each entry includes a step-by-step tutorial, importable artifacts, and the agent configuration needed to get started.

## Features

All SDKs share a consistent API surface with language-idiomatic patterns:

- **Synchronous & streaming** — Simple request/response or real-time SSE streaming
- **Multi-turn conversations** — Maintain context across messages with conversation IDs
- **Async support** — Native async/await in Python, TypeScript, and Java
- **Typed errors** — Structured error hierarchy (authentication, not-found, rate-limit, etc.)
- **Automatic retries** — Exponential backoff with configurable limits
- **Management APIs** — Create and configure agents, personas, and abilities programmatically

## Documentation

| Resource | Description |
|----------|-------------|
| [Quick Start](docs/quickstart.md) | Get running in 5 minutes |
| [Python SDK](python/README.md) | Full Python reference |
| [TypeScript SDK](typescript/README.md) | Full TypeScript reference |
| [Java SDK](java/README.md) | Full Java reference |
| [CLI](cli/README.md) | CLI usage and commands |
| [MCP Tools](docs/mcp.md) | MCP integration guide |
| [LangChain Integration](docs/langchain.md) | Using agents and tools with LangChain |
| [Async Patterns](docs/async.md) | Async usage across SDKs |
| [Error Handling](docs/error-handling.md) | Exception handling patterns |
| [n8n Integration](n8n-nodes-metadata/README.md) | n8n community node |
| [Cookbook](cookbook/) | Production-ready examples and workflows |

## Development

```bash
make build-all         # Build all SDKs
make lint              # Lint all SDKs
make test-all          # Run unit tests
make test-integration  # Run integration tests (requires AI_SDK_HOST, AI_SDK_TOKEN)
```

See [Releasing](docs/releasing.md) for version management and publishing.

## License

Collate Community License 1.0
