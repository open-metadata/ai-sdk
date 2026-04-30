# API Reference

Comprehensive reference of all SDK methods, server endpoints, data models, and feature parity across Python, TypeScript, Java, and Rust CLI.

## Server Endpoint Map

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/agents/dynamic/` | GET/POST | List API-enabled agents / Create agent |
| `/api/v1/agents/dynamic/{name}` | GET | Get agent info |
| `/{agent_name}/invoke` | POST | Invoke agent (sync) |
| `/{agent_name}/stream` | POST | Invoke agent (SSE streaming) |
| `/api/v1/bots/` | GET | List bots (paginated) |
| `/api/v1/bots/name/{name}` | GET | Get bot by name |
| `/api/v1/agents/personas/` | GET/POST | List / Create personas |
| `/api/v1/agents/personas/name/{name}` | GET | Get persona by name |
| `/api/v1/agents/abilities/` | GET | List abilities (paginated) |
| `/api/v1/agents/abilities/name/{name}` | GET | Get ability by name |
| `/api/v1/contextCenter/memories/` | GET/POST | List / Create memories (paginated, optional `primaryEntityFqn` filter) |
| `/api/v1/contextCenter/memories/{id}` | GET/DELETE | Get / Delete memory by ID (`hardDelete=` query param on DELETE) |
| `/api/v1/hybrid/nlq/search?index=contextMemory` | GET | Hybrid NLQ search over the memories index |
| `/mcp` | POST | MCP JSON-RPC 2.0 (`tools/list`, `tools/call`) |

---

## Python SDK (`ai-sdk`)

### AISdk Client

```python
from ai_sdk import AISdk

client = AISdk(
    host="https://your-org.getcollate.io",
    token="your-jwt-token",
    timeout=120.0,           # seconds
    verify_ssl=True,
    enable_async=False,
    max_retries=3,
    retry_delay=1.0,         # seconds
)
```

Entity CRUD lives on namespaces (`client.<entity>.<verb>()`). Each namespace exposes both sync and async methods.

| Method | Endpoint | Streaming | Async |
|--------|----------|-----------|-------|
| `agent(name?) -> AgentHandle` | -- (local) | -- | -- |
| `agents.list(limit?) -> list[AgentInfo]` | `GET /api/v1/agents/dynamic/` | No | `agents.alist()` |
| `agents.create(request) -> AgentInfo` | `POST /api/v1/agents/dynamic/` | No | `agents.acreate()` |
| `bots.list(limit?) -> list[BotInfo]` | `GET /api/v1/bots/` | No | `bots.alist()` |
| `bots.get(name) -> BotInfo` | `GET /api/v1/bots/name/{name}` | No | `bots.aget()` |
| `personas.list(limit?) -> list[PersonaInfo]` | `GET /api/v1/agents/personas/` | No | `personas.alist()` |
| `personas.get(name) -> PersonaInfo` | `GET /api/v1/agents/personas/name/{name}` | No | `personas.aget()` |
| `personas.create(request) -> PersonaInfo` | `POST /api/v1/agents/personas/` | No | `personas.acreate()` |
| `abilities.list(limit?) -> list[AbilityInfo]` | `GET /api/v1/agents/abilities/` | No | `abilities.alist()` |
| `abilities.get(name) -> AbilityInfo` | `GET /api/v1/agents/abilities/name/{name}` | No | `abilities.aget()` |
| `memories.list(primary_entity_fqn?, limit?) -> list[ContextMemory]` | `GET /api/v1/contextCenter/memories/` | No | `memories.alist()` |
| `memories.get(id) -> ContextMemory` | `GET /api/v1/contextCenter/memories/{id}` | No | `memories.aget()` |
| `memories.create(request) -> ContextMemory` | `POST /api/v1/contextCenter/memories/` | No | `memories.acreate()` |
| `memories.delete(id, hard_delete=False) -> None` | `DELETE /api/v1/contextCenter/memories/{id}` | No | `memories.adelete()` |
| `memories.search(query, filters?, size=15, from_=0) -> MemorySearchResults` | `GET /api/v1/hybrid/nlq/search?index=contextMemory` | No | `memories.asearch()` |
| `.mcp` property -> `MCPClient` | -- (lazy init) | -- | -- |

### AgentHandle

```python
agent = client.agent("DataQualityPlannerAgent")
```

| Method | Endpoint | Streaming | Async |
|--------|----------|-----------|-------|
| `call(message?, conversation_id?, parameters?) -> InvokeResponse` | `POST /{agent}/invoke` | No | `acall()` |
| `stream(message?, conversation_id?, parameters?) -> Iterable[StreamEvent]` | `POST /{agent}/stream` | Yes (SSE) | `astream()` |
| `get_info() -> AgentInfo` | `GET /{agent}` | No | `aget_info()` |

### MCPClient (Python-only)

```python
from ai_sdk.mcp.models import MCPTool
```

| Method | Protocol | Description |
|--------|----------|-------------|
| `list_tools() -> list[ToolInfo]` | JSON-RPC `tools/list` via `/mcp` | List available MCP tools |
| `call_tool(name, arguments) -> ToolCallResult` | JSON-RPC `tools/call` via `/mcp` | Execute an MCP tool |
| `as_openai_tools(include?, exclude?) -> list[dict]` | -- (local transform) | Format tools for OpenAI function calling |
| `as_langchain_tools(include?, exclude?) -> list[BaseTool]` | -- (local transform) | Create LangChain tool wrappers |
| `create_tool_executor() -> Callable` | -- (local) | Create executor for OpenAI tool calls |

### Conversation (convenience class)

```python
from ai_sdk import Conversation

conv = Conversation(client.agent("MyAgent"))
print(conv.send("Analyze data"))
print(conv.send("Create tests"))  # auto-tracks conversationId
```

| Method | Description |
|--------|-------------|
| `send(message?, parameters?) -> str` | Send message, auto-track `conversation_id` |
| `asend(message?, parameters?) -> str` | Async variant |
| `stream(message?, parameters?) -> Iterable[StreamEvent]` | Stream with conversation context |
| `astream(message?, parameters?) -> AsyncIterator[StreamEvent]` | Async stream |
| `reset()` | Clear conversation state |
| `history` | List of `(message, response)` tuples |
| `responses` | List of all `InvokeResponse` objects |
| `tools_used` | Unique tool names used across conversation |

---

## TypeScript SDK (`@openmetadata/ai-sdk`)

### AISdk Client

```typescript
import { AISdk } from '@openmetadata/ai-sdk';

const client = new AISdk({
  host: 'https://your-org.getcollate.io',
  token: 'your-jwt-token',
  timeout: 120000,    // milliseconds
  maxRetries: 3,
  retryDelay: 1000,   // milliseconds
});
```

Entity CRUD lives on namespace fields (`client.<entity>.<verb>()`).

| Method | Endpoint | Streaming |
|--------|----------|-----------|
| `agent(name?): AgentHandle` | -- (local) | -- |
| `agents.list(options?): Promise<AgentInfo[]>` | `GET /api/v1/agents/dynamic/` | No |
| `agents.create(request): Promise<AgentInfo>` | `POST /api/v1/agents/dynamic/` | No |
| `bots.list(options?): Promise<BotInfo[]>` | `GET /api/v1/bots/` | No |
| `bots.get(name): Promise<BotInfo>` | `GET /api/v1/bots/name/{name}` | No |
| `personas.list(options?): Promise<PersonaInfo[]>` | `GET /api/v1/agents/personas/` | No |
| `personas.get(name): Promise<PersonaInfo>` | `GET /api/v1/agents/personas/name/{name}` | No |
| `personas.create(request): Promise<PersonaInfo>` | `POST /api/v1/agents/personas/` | No |
| `abilities.list(options?): Promise<AbilityInfo[]>` | `GET /api/v1/agents/abilities/` | No |
| `abilities.get(name): Promise<AbilityInfo>` | `GET /api/v1/agents/abilities/name/{name}` | No |
| `memories.list(options?): Promise<ContextMemory[]>` | `GET /api/v1/contextCenter/memories/` | No |
| `memories.get(id): Promise<ContextMemory>` | `GET /api/v1/contextCenter/memories/{id}` | No |
| `memories.create(request): Promise<ContextMemory>` | `POST /api/v1/contextCenter/memories/` | No |
| `memories.delete(id, options?): Promise<void>` | `DELETE /api/v1/contextCenter/memories/{id}` | No |
| `memories.search(query, options?): Promise<MemorySearchResults>` | `GET /api/v1/hybrid/nlq/search?index=contextMemory` | No |

### AgentHandle

| Method | Endpoint | Streaming |
|--------|----------|-----------|
| `invoke(message?, options?): Promise<InvokeResponse>` | `POST /{agent}/invoke` | No |
| `stream(message?, options?): AsyncGenerator<StreamEvent>` | `POST /{agent}/stream` | Yes (SSE) |
| `getInfo(): Promise<AgentInfo>` | `GET /{agent}` | No |

---

## Java SDK (`org.open-metadata:ai-sdk`)

### AISdk Client

```java
AISdk client = AISdk.builder()
    .host("https://your-org.getcollate.io")
    .token("your-jwt-token")
    .timeout(Duration.ofSeconds(120))
    .maxRetries(3)
    .retryDelay(Duration.ofSeconds(1))
    .build();
```

Entity CRUD lives on namespace accessor methods (`client.<entity>().<verb>()`).

| Method | Endpoint | Streaming |
|--------|----------|-----------|
| `agent(name): AgentHandle` | -- (local) | -- |
| `agents().list() / agents().list(limit)` | `GET /api/v1/agents/dynamic/` | No |
| `agents().create(request): AgentInfo` | `POST /api/v1/agents/dynamic/` | No |
| `bots().list() / bots().list(limit)` | `GET /api/v1/bots/` | No |
| `bots().get(name): BotInfo` | `GET /api/v1/bots/name/{name}` | No |
| `personas().list() / personas().list(limit)` | `GET /api/v1/agents/personas/` | No |
| `personas().get(name): PersonaInfo` | `GET /api/v1/agents/personas/name/{name}` | No |
| `personas().create(request): PersonaInfo` | `POST /api/v1/agents/personas/` | No |
| `abilities().list() / abilities().list(limit)` | `GET /api/v1/agents/abilities/` | No |
| `abilities().get(name): AbilityInfo` | `GET /api/v1/agents/abilities/name/{name}` | No |
| `memories().list() / memories().list(fqn, limit)` | `GET /api/v1/contextCenter/memories/` | No |
| `memories().get(id): ContextMemory` | `GET /api/v1/contextCenter/memories/{id}` | No |
| `memories().create(request): ContextMemory` | `POST /api/v1/contextCenter/memories/` | No |
| `memories().delete(id) / delete(id, hardDelete)` | `DELETE /api/v1/contextCenter/memories/{id}` | No |
| `memories().search(query) / search(query, filters, size, from)` | `GET /api/v1/hybrid/nlq/search?index=contextMemory` | No |

### AgentHandle (fluent builder pattern)

| Method | Endpoint | Streaming |
|--------|----------|-----------|
| `invoke() / invoke(message): InvokeResponse` | `POST /{agent}/invoke` | No |
| `stream(Consumer) / stream(message, Consumer): void` | `POST /{agent}/stream` | Yes (SSE, callback) |
| `streamIterator() / streamIterator(message): Stream<StreamEvent>` | `POST /{agent}/stream` | Yes (Java Stream) |
| `info(): AgentInfo` | `GET /{agent}` | No |
| `conversationId(id): AgentHandle` | -- (local) | -- |
| `parameters(params): AgentHandle` | -- (local) | -- |

---

## Rust CLI (`ai-sdk`)

### Agent Commands

| Command | Endpoint | Streaming |
|---------|----------|-----------|
| `agents list [--json]` | `GET /api/v1/api/agents/` | No |
| `agents info <name> [--json]` | `GET /api/v1/api/agents/{name}` | No |
| `agents create [options]` | `POST /api/v1/agents/dynamic/` | No |

### Bot Commands

| Command | Endpoint |
|---------|----------|
| `bots list [--limit N] [--json]` | `GET /api/v1/bots/` |
| `bots get <name> [--json]` | `GET /api/v1/bots/name/{name}` |

### Persona Commands

| Command | Endpoint |
|---------|----------|
| `personas list [--limit N] [--json]` | `GET /api/v1/agents/personas/` |
| `personas get <name> [--json]` | `GET /api/v1/agents/personas/name/{name}` |
| `personas create [options]` | `POST /api/v1/agents/personas/` |

### Ability Commands

| Command | Endpoint |
|---------|----------|
| `abilities list [--limit N] [--json]` | `GET /api/v1/agents/abilities/` |
| `abilities get <name> [--json]` | `GET /api/v1/agents/abilities/name/{name}` |

### Memory Commands

| Command | Endpoint |
|---------|----------|
| `memories list [--entity-fqn FQN] [--limit N] [--json]` | `GET /api/v1/contextCenter/memories/` |
| `memories get <id> [--json]` | `GET /api/v1/contextCenter/memories/{id}` |
| `memories create --name N --question Q --answer A [...]` | `POST /api/v1/contextCenter/memories/` |
| `memories delete <id> [--hard]` | `DELETE /api/v1/contextCenter/memories/{id}` |
| `memories search <query> [--size N] [--from N] [--json]` | `GET /api/v1/hybrid/nlq/search?index=contextMemory` |

**Memory create options:** `--title`, `--description`, `--memory-type=note` (preference|use-case|note|runbook|faq), `--memory-scope=entity-scoped` (entity-scoped|user-global), `--visibility=private` (private|entity|shared), `--primary-entity-{id,type,fqn}`, `--tags`

### Invoke & Chat

| Command | Endpoint | Streaming |
|---------|----------|-----------|
| `invoke <agent> [message]` | `POST /{agent}/invoke` | No |
| `invoke <agent> [message] --stream` | `POST /{agent}/stream` | Yes (SSE) |
| `chat [agent]` | `POST /{agent}/invoke` or `/stream` | Interactive TUI |

**Invoke options:** `--stream`, `--json`, `-c <conversation-id>`, `-t` (thinking, requires `--stream`), `--debug`

### Configure

```bash
ai-sdk configure                     # Interactive setup
ai-sdk configure set <key> <value>   # Set config value
ai-sdk configure get <key>           # Get config value
ai-sdk configure list                # List all config
```

---

## Data Models

### InvokeRequest

```
{
  message?: string              // Optional (uses agent default if omitted)
  conversationId?: string       // For multi-turn conversations
  parameters?: Record<string, any>
}
```

### InvokeResponse

```
{
  conversationId: string        // Conversation ID for follow-ups
  response: string              // Agent's response text
  toolsUsed: string[]           // Tools the agent used
  usage?: {
    promptTokens: number
    completionTokens: number
    totalTokens: number
  }
}
```

### StreamEvent

```
{
  type: 'start' | 'content' | 'tool_use' | 'end' | 'error'
  content?: string              // For 'content' events
  toolName?: string             // For 'tool_use' events
  conversationId?: string       // On 'start' and 'end'
  error?: string                // For 'error' events
}
```

### AgentInfo

```
{
  name: string
  displayName: string
  description: string
  abilities: string[]
  apiEnabled: boolean
}
```

### PersonaInfo

```
{
  id: string
  name: string
  displayName?: string
  description?: string
  prompt?: string
  provider: string              // "system" or "user"
}
```

### BotInfo

```
{
  id: string
  name: string
  displayName?: string
  description?: string
  botUser?: { id, type, name?, displayName? }
}
```

### AbilityInfo

```
{
  id: string
  name: string
  displayName?: string
  description?: string
  provider?: string
  fullyQualifiedName?: string
  tools: string[]
}
```

### EntityReference

```
{
  id: string
  type: string                  // e.g., "table", "dashboard", "pipeline"
  name?: string
  fullyQualifiedName?: string
  displayName?: string
}
```

### CreateContextMemoryRequest

```
{
  name: string                  // Required: stable system name
  question: string              // Required: canonical question/instruction
  answer: string                // Required: canonical answer/guidance
  title?: string                // Short title shown in Context Center
  description?: string          // Optional markdown description
  memoryType?: 'Preference' | 'UseCase' | 'Note' | 'Runbook' | 'Faq'
                                // Default: 'Note'
  memoryScope?: 'UserGlobal' | 'EntityScoped'
                                // Default: 'EntityScoped'
  visibility?: 'Private' | 'Entity' | 'Shared'
                                // Default: 'Private'
  primaryEntity?: EntityReference
  relatedEntities?: EntityReference[]
  tags?: string[]               // Tag FQN strings; wrapped to TagLabel on the wire
}
```

### ContextMemory

```
{
  id: string
  name: string
  fullyQualifiedName?: string
  title?: string
  question: string
  answer: string
  summary?: string
  memoryType: MemoryType
  memoryScope: MemoryScope
  visibility: MemoryVisibility  // Flattened from shareConfig.visibility
  primaryEntity?: EntityReference
  usageCount: number
  lastUsedAt?: number           // Epoch milliseconds
  deleted: boolean
}
```

### MemorySearchHit / MemorySearchResults

```
MemorySearchHit {
  memory: ContextMemory         // Parsed from _source
  score: number                 // OpenSearch _score
}

MemorySearchResults {
  total: number                 // Hit total (parsed from hits.total.value)
  hits: MemorySearchHit[]
}
```

### MCP Models (Python-only)

```python
class MCPTool(StrEnum):
    SEARCH_METADATA = "search_metadata"
    GET_ENTITY_DETAILS = "get_entity_details"
    GET_ENTITY_LINEAGE = "get_entity_lineage"
    CREATE_GLOSSARY = "create_glossary"
    CREATE_GLOSSARY_TERM = "create_glossary_term"
    CREATE_LINEAGE = "create_lineage"
    PATCH_ENTITY = "patch_entity"

@dataclass
class ToolInfo:
    name: MCPTool
    description: str
    parameters: list[ToolParameter]

@dataclass
class ToolCallResult:
    success: bool
    data: dict | None
    error: str | None

@dataclass
class ToolParameter:
    name: str
    type: str                   # "string", "integer", "boolean", "array", "object"
    description: str
    required: bool
```

---

## Error Hierarchy

All SDKs implement the same error hierarchy:

```
AISdkError (base)
+-- AuthenticationError (401)
+-- AgentNotEnabledError (403)
+-- NotFoundError (404)
|   +-- AgentNotFoundError
|   +-- BotNotFoundError
|   +-- PersonaNotFoundError
|   +-- AbilityNotFoundError
+-- ValidationError (400)
+-- RateLimitError (429)
+-- AgentExecutionError (5xx)
+-- MCPError (Python-only)
    +-- MCPToolExecutionError
```

---

## Authentication

All endpoints require a Bearer token:

```
Authorization: Bearer <jwt_token>
Content-Type: application/json
Accept: application/json        (or text/event-stream for streaming)
User-Agent: ai-sdk/X.Y.Z
X-Request-ID: <correlation_id>
```

---

## Pagination

List endpoints use cursor-based pagination:

```
GET /api/v1/api/agents/?limit=100&after=<cursor>
```

Response:

```json
{
  "data": [...],
  "paging": {
    "after": "next_cursor",
    "total": 250
  }
}
```

All SDKs auto-paginate by default. Pass an optional `limit` to cap results.

---

## Streaming (SSE)

Streaming endpoints use Server-Sent Events:

```
POST /{agent}/stream
Accept: text/event-stream

event: start
data: {"conversationId":"abc","type":"start"}

event: content
data: {"type":"content","content":"partial text..."}

event: end
data: {"type":"end","conversationId":"abc"}
```

SDK-idiomatic streaming:

- **Python:** `agent.stream()` / `agent.astream()` (sync/async generators)
- **TypeScript:** `agent.stream()` (AsyncGenerator)
- **Java:** `agent.stream(Consumer)` or `agent.streamIterator()` (Java Stream)
- **Rust CLI:** `ai-sdk invoke --stream`

---

## Retry Behavior

All SDKs automatically retry on:

- **429** (Rate Limit) -- respects `Retry-After` header
- **500, 502, 503, 504** (Server errors)
- Network timeouts

Default: 3 retries with exponential backoff.

---

## Feature Parity Matrix

| Feature | Python | TypeScript | Java | Rust CLI |
|---------|--------|------------|------|----------|
| Agent invoke | sync + async | async | sync | sync |
| Agent stream | sync + async | async generator | callback + Stream | `--stream` flag |
| Default agent (`client.agent()` no name) | yes | yes | yes | `--default` flag |
| List agents | yes | yes | yes | yes |
| Create agent | yes | yes | yes | yes (TUI + CLI) |
| Bots (list + get) | yes | yes | yes | yes |
| Personas (list + get + create) | yes | yes | yes | yes (TUI + CLI) |
| Abilities (list + get) | yes | yes | yes | yes |
| **Context Memories** (list + get + create + delete + search) | yes (sync + async) | yes | yes | yes |
| Conversations | `Conversation` class | manual `conversationId` | fluent `.conversationId()` | `-c` flag |
| **MCP tools** | **yes** | no | no | no |
| Interactive chat | -- | -- | -- | TUI (`chat`) |
| Retry/backoff | yes | yes | yes | yes |

> **Note:** MCP support is currently Python-only because MCP tools are primarily consumed by Python-based AI frameworks (LangChain, OpenAI SDK). TypeScript and Java MCP support may be added in a future release based on demand.
