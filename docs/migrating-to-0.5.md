# Migrate to 0.5.0

Version 0.5.0 targets the OpenMetadata and Collate 2.1 APIs. Upgrade the SDK and
update the calls below before moving your server to 2.1.

## Create standalone agents

Replace `mode="chat"`, `"agent"`, or `"both"` with `mode="standalone"` for agents
you invoke directly. Planner-dispatched agents use `mode="worker"` and require
`planner_description` in Python or `plannerDescription` in TypeScript and Java.
That description contains `description`, `input`, `output`, and `prompt` strings.

```python
from ai_sdk import CreateAgentRequest

agent = client.agents.create(CreateAgentRequest(
    name="OrdersHelper",
    description="Answer questions about orders",
    persona="DataAnalyst",
    mode="standalone",
    api_enabled=True,
))
```

`type` defaults to `external`. Use `internal` for an agent with fixed instructions.
The `provider` field identifies system or user ownership.
The server creates API-submitted agents as user-owned.

Remove `schedule` from agent creation requests. Configure scheduled execution
through Collate automations instead.

Calls without a message now send `"message": ""` in synchronous and streaming
requests. The SDK still accepts a prompt-only call, and the server receives its
required message field.

## Filter memories by an entity UUID

The memory list endpoint accepts an asset UUID. Replace the old FQN filter and
pass the asset's `id` from its metadata response.

| Client | Old argument | New argument |
| --- | --- | --- |
| Python | `primary_entity_fqn` | `primary_entity_id` |
| TypeScript | `primaryEntityFqn` | `primaryEntityId` |
| Java | `memories().list(fqn, limit)` | `memories().list(entityId, limit)` |
| CLI | `memories list --entity-fqn` | `memories list --entity-id` |

```python
memories = client.memories.list(
    primary_entity_id="11111111-1111-1111-1111-111111111111",
)
```

Memory types now include `Learning`. Visibility now includes `Public`. `Shared`
continues to describe explicit sharing. Use `Public` for organization-wide
visibility, subject to the server's access rules.

Read `entity_status` and `status_reason` in Python, `entityStatus` and
`statusReason` in TypeScript, or `getEntityStatus()` and `getStatusReason()` in
Java, to distinguish pending memories from approved memories. The CLI displays
these fields and includes them in JSON.
Collate defaults new memories to `Unprocessed`; OpenMetadata defaults them to
`Approved`. The server enforces approval permissions when you set the initial
`entity_status` or `entityStatus` on a create request. The CLI exposes this as
`memories create --entity-status approved`.

## Use the current MCP tools

Use `create_entity` instead of the old entity-specific creation tools. Supply
`entityType`, `name`, and the entity-specific `attributes` advertised by the server.
Use `describe_entity_type` to inspect those attributes.

Use `company_context` for company knowledge. Use
`get_entity_details(include=["context"])` for an asset's context, and
`get_entity_details(include=["content"])` for its knowledge content.

The SDK exposes every tool advertised by `tools/list`, including tools supplied
by Collate. Tool names are strings; `MCPTool` remains a convenience enum for the
current built-in names. Explicit include and exclude filters accept either form.
Use an include filter when your application grants access to a fixed set of tools.

```python
from ai_sdk.mcp.models import MCPTool

tools = client.mcp.as_langchain_tools(include=[
    MCPTool.SEARCH_METADATA,
    MCPTool.GET_ENTITY_DETAILS,
    MCPTool.GET_ENTITY_LINEAGE,
])
```

`ToolInfo.input_schema` replaces `ToolInfo.parameters` and `ToolParameter`.
Both framework adapters retain the server's full JSON Schema, including nested
objects, array item types, and enum constraints. The LangChain extra requires
`langchain-core>=0.3.79` for JSON Schema tool definitions.

## Handle structured responses and stream errors

Synchronous invocation responses retain the server's `components` array. Read it
alongside `response` when tools return charts or other structured output.

A terminal `stream-error` produces an error event in Python, TypeScript, and Java.
The CLI returns an error and a nonzero exit status. Check streaming error events
even when the HTTP request initially succeeds.

## Check against the server source

Run the contract check with local clones of both server repositories. It reads
Git revisions and makes no server requests.

```bash
PYTHONPATH=python/src python scripts/check-server-contracts.py \
    --openmetadata /path/to/OpenMetadata \
    --collate /path/to/openmetadata-collate
```

The default revision is `origin/main` in each repository. Use
`--openmetadata-ref` and `--collate-ref` to check the release commits.
