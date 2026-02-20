# API Reference

Comprehensive reference of all SDK methods, server endpoints, data models, and feature parity across Python, TypeScript, Java, and Rust CLI.

## Server Endpoint Map

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/api/agents/` | GET | List API-enabled agents (paginated) |
| `/api/v1/api/agents/{name}` | GET | Get agent info |
| `/api/v1/agents/dynamic/` | POST | Create agent |
| `/{agent_name}/invoke` | POST | Invoke agent (sync) |
| `/{agent_name}/stream` | POST | Invoke agent (SSE streaming) |
| `/api/v1/bots/` | GET | List bots (paginated) |
| `/api/v1/bots/name/{name}` | GET | Get bot by name |
| `/api/v1/agents/personas/` | GET/POST | List / Create personas |
| `/api/v1/agents/personas/name/{name}` | GET | Get persona by name |
| `/api/v1/agents/abilities/` | GET | List abilities (paginated) |
| `/api/v1/agents/abilities/name/{name}` | GET | Get ability by name |
| `/mcp` | POST | MCP JSON-RPC 2.0 (`tools/list`, `tools/call`) |

---

## Python SDK (`ai-sdk`)

### MetadataAI Client

```python
from ai_sdk import MetadataAI

client = MetadataAI(
    host="https://your-org.getcollate.io",
    token="your-jwt-token",
    timeout=120.0,           # seconds
    verify_ssl=True,
    enable_async=False,
    max_retries=3,
    retry_delay=1.0,         # seconds
)
```

| Method | Endpoint | Streaming | Async |
|--------|----------|-----------|-------|
| `agent(name) -> AgentHandle` | -- (local) | -- | -- |
| `list_agents(limit?) -> list[AgentInfo]` | `GET /api/v1/api/agents/` | No | `alist_agents()` |
| `create_agent(request) -> AgentInfo` | `POST /api/v1/agents/dynamic/` | No | `acreate_agent()` |
| `list_bots(limit?) -> list[BotInfo]` | `GET /api/v1/bots/` | No | `alist_bots()` |
| `get_bot(name) -> BotInfo` | `GET /api/v1/bots/name/{name}` | No | `aget_bot()` |
| `list_personas(limit?) -> list[PersonaInfo]` | `GET /api/v1/agents/personas/` | No | `alist_personas()` |
| `get_persona(name) -> PersonaInfo` | `GET /api/v1/agents/personas/name/{name}` | No | `aget_persona()` |
| `create_persona(request) -> PersonaInfo` | `POST /api/v1/agents/personas/` | No | `acreate_persona()` |
| `list_abilities(limit?) -> list[AbilityInfo]` | `GET /api/v1/agents/abilities/` | No | `alist_abilities()` |
| `get_ability(name) -> AbilityInfo` | `GET /api/v1/agents/abilities/name/{name}` | No | `aget_ability()` |
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

### MetadataAI Client

```typescript
import { MetadataAI } from '@openmetadata/ai-sdk';

const client = new MetadataAI({
  host: 'https://your-org.getcollate.io',
  token: 'your-jwt-token',
  timeout: 120000,    // milliseconds
  maxRetries: 3,
  retryDelay: 1000,   // milliseconds
});
```

| Method | Endpoint | Streaming |
|--------|----------|-----------|
| `agent(name): AgentHandle` | -- (local) | -- |
| `listAgents(options?): Promise<AgentInfo[]>` | `GET /api/v1/api/agents/` | No |
| `createAgent(request): Promise<AgentInfo>` | `POST /api/v1/agents/dynamic/` | No |
| `listBots(options?): Promise<BotInfo[]>` | `GET /api/v1/bots/` | No |
| `getBot(name): Promise<BotInfo>` | `GET /api/v1/bots/name/{name}` | No |
| `listPersonas(options?): Promise<PersonaInfo[]>` | `GET /api/v1/agents/personas/` | No |
| `getPersona(name): Promise<PersonaInfo>` | `GET /api/v1/agents/personas/name/{name}` | No |
| `createPersona(request): Promise<PersonaInfo>` | `POST /api/v1/agents/personas/` | No |
| `listAbilities(options?): Promise<AbilityInfo[]>` | `GET /api/v1/agents/abilities/` | No |
| `getAbility(name): Promise<AbilityInfo>` | `GET /api/v1/agents/abilities/name/{name}` | No |

### AgentHandle

| Method | Endpoint | Streaming |
|--------|----------|-----------|
| `invoke(message?, options?): Promise<InvokeResponse>` | `POST /{agent}/invoke` | No |
| `stream(message?, options?): AsyncGenerator<StreamEvent>` | `POST /{agent}/stream` | Yes (SSE) |
| `getInfo(): Promise<AgentInfo>` | `GET /{agent}` | No |

---

## Java SDK (`io.openmetadata:ai-sdk`)

### MetadataAI Client

```java
MetadataAI client = MetadataAI.builder()
    .host("https://your-org.getcollate.io")
    .token("your-jwt-token")
    .timeout(Duration.ofSeconds(120))
    .maxRetries(3)
    .retryDelay(Duration.ofSeconds(1))
    .build();
```

| Method | Endpoint | Streaming |
|--------|----------|-----------|
| `agent(name): AgentHandle` | -- (local) | -- |
| `listAgents() / listAgents(limit)` | `GET /api/v1/api/agents/` | No |
| `createAgent(builder): AgentInfo` | `POST /api/v1/agents/dynamic/` | No |
| `listBots() / listBots(limit)` | `GET /api/v1/bots/` | No |
| `getBot(name): BotInfo` | `GET /api/v1/bots/name/{name}` | No |
| `listPersonas() / listPersonas(limit)` | `GET /api/v1/agents/personas/` | No |
| `getPersona(name): PersonaInfo` | `GET /api/v1/agents/personas/name/{name}` | No |
| `createPersona(request): PersonaInfo` | `POST /api/v1/agents/personas/` | No |
| `listAbilities() / listAbilities(limit)` | `GET /api/v1/agents/abilities/` | No |
| `getAbility(name): AbilityInfo` | `GET /api/v1/agents/abilities/name/{name}` | No |

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
MetadataError (base)
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
| List agents | yes | yes | yes | yes |
| Create agent | yes | yes | yes | yes (TUI + CLI) |
| Bots (list + get) | yes | yes | yes | yes |
| Personas (list + get + create) | yes | yes | yes | yes (TUI + CLI) |
| Abilities (list + get) | yes | yes | yes | yes |
| Conversations | `Conversation` class | manual `conversationId` | fluent `.conversationId()` | `-c` flag |
| **MCP tools** | **yes** | no | no | no |
| Interactive chat | -- | -- | -- | TUI (`chat`) |
| Retry/backoff | yes | yes | yes | yes |

> **Note:** MCP support is currently Python-only because MCP tools are primarily consumed by Python-based AI frameworks (LangChain, OpenAI SDK). TypeScript and Java MCP support may be added in a future release based on demand.
