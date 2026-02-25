# AI SDK

Bring AI to your metadata. The OpenMetadata AI SDK gives you programmatic access to your data catalog through two complementary paths: **MCP tools** for building custom AI applications with any LLM, and **Dynamic Agents** for invoking ready-to-use AI assistants from [Collate's AI Studio](https://www.getcollate.io).

| SDK | Package | Install |
|-----|---------|---------|
| Python | [`ai-sdk`](https://pypi.org/project/ai-sdk/) | `pip install ai-sdk` |
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
pip install ai-sdk
```

```python
from ai_sdk import AISdk, AISdkConfig

config = AISdkConfig.from_env()  # reads AI_SDK_HOST and AI_SDK_TOKEN
client = AISdk.from_config(config)

# Invoke an agent
response = client.agent("DataQualityPlannerAgent").call(
    "What data quality tests should I add for the customers table?"
)
print(response.response)

# Stream responses in real time
for event in client.agent("DataQualityPlannerAgent").stream("Analyze the orders table"):
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

const response = await client.agent('DataQualityPlannerAgent').call(
  'What data quality tests should I add for the customers table?'
);
console.log(response.response);

// Stream responses
for await (const event of client.agent('DataQualityPlannerAgent').stream('Analyze data quality')) {
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

InvokeResponse response = client.agent("DataQualityPlannerAgent")
    .call("What data quality tests should I add?");
System.out.println(response.getResponse());
```

### CLI

```bash
# Install
curl -sSL https://raw.githubusercontent.com/open-metadata/ai-sdk/main/cli/install.sh | sh

# Configure
ai-sdk configure

# Invoke an agent
ai-sdk invoke DataQualityPlannerAgent "Analyze the customers table"
```

Interactive TUI with markdown rendering and syntax highlighting.

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
