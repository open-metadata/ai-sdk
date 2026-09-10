# Demo Guide: Stop Rebuilding Context for Every New Agent

This is a three-act demo with one idea running through it: **context is a
governed platform capability, not prompt assembly code**.

The acts deliberately increase how much application code we own while keeping
the Collate context contract constant:

```text
RETRIEVE                         BUILD                          EXTEND
Context API + MCP                AI Studio agent                Our own agent

JSON Schema contracts      ->   Browser                         Browser
REST /context                    -> thin Node server             -> LangGraph workflow
MCP get_asset_context               -> GDPR agent in Collate        |- GDPR agent in Collate
RBAC at retrieval time                                             |- live steward/expert directory
                                                                   `- internal handoff agent
```

Suggested length: 20 minutes (6 + 6 + 8), with five minutes for questions.

## Align the published abstract

The runnable story below is a request-driven GDPR escalation, not a continuous
numeric-variance monitor. If the session description can still be edited,
replace this sentence:

> We'll build an agent that monitors business data continuously and escalates a
> variance the moment it appears.

with:

> We'll build an agent that investigates a GDPR request with governed data
> context and escalates it to the right steward and domain experts.

If the description is already fixed, be explicit in the opening: the DSAR is
the event entering the workflow, and the same Retrieve / Build / Extend pattern
also applies to a scheduled variance event. Do not claim that this application
continuously monitors a metric; it does not.

## The through-line

Use this sentence at every transition:

> We are changing where the agent runs and who owns the orchestration. We are
> not copying the catalog, policies, corrections, lineage, or permissions into
> a new prompt.

## Before the session

You need one Collate/OpenMetadata instance containing the demo metadata, a JWT
that can invoke the API-enabled `GDPRComplianceAnalyzer`, and the provider key
for the internal handoff model used only in Act 3.

```bash
export AI_SDK_HOST="https://your-instance.getcollate.io"
export AI_SDK_TOKEN="<jwt>"
export OPENAI_API_KEY="<only-needed-in-act-3>"
export AI_SDK_SERVICE="jaffle shop"
export AI_SDK_DATABASE="jaffle_shop"
```

Prepare the Jaffle Shop catalog and organizational context using
[`resources/demo-database`](../resources/demo-database/README.md). In
particular, rerun the idempotent ownership setup so the demo has explicit
Data Steward and Domain expert relationships:

```bash
python cookbook/resources/demo-database/scripts/create_owners_and_domains.py
make setup-gdpr-agent
```

`setup-gdpr-agent` creates or updates the `GDPRAnalyst` prompt and
`GDPRComplianceAnalyzer` knowledge scope. This matters on a shared catalog: the
agent must reject unrelated assets even when they also contain tables named
`customers`, `orders`, or `payments`. The service-level boundary is stored in
AI Studio, so neither web application needs to append it to every request. See
[`agent-config.md`](./agent-config.md) for the exact rule and manual setup.

Validate both applications before going on stage:

```bash
# Terminal 1 — Act 2, http://localhost:8080
make demo-gdpr

# Terminal 2 — Act 3, http://localhost:8081
make demo-gdpr-extended
```

Use the same request in both applications:

```text
Customer Michael Perez (customer_id: 1, email: mperez@example.com) has
requested deletion of all his personal data under GDPR Article 17. Find every
affected asset, trace downstream copies, identify PII and retention conflicts,
and produce an actionable deletion plan.
```

Do not add the service name to this audience-facing request. The useful proof is
that scope comes from the governed agent configuration rather than being rebuilt
by every caller. The report should begin by confirming service `jaffle shop`,
database `jaffle_shop`, and should identify all assets with fully qualified
names under `jaffle shop.jaffle_shop.`.

## Act 1 — Retrieve: one context contract

Open
[`explore_context_endpoint.ipynb`](../persona-aware-context/explore_context_endpoint.ipynb)
and then
[`persona_demo.ipynb`](../persona-aware-context/persona_demo.ipynb).

### Start with the JSON Schema foundation

Talk track:

1. OpenMetadata entities start as JSON Schema contracts. The server models,
   generated clients, ingestion models, and API payloads share those contracts.
   If you want to show the source of truth, open the
   [table schema](https://github.com/open-metadata/OpenMetadata/blob/main/openmetadata-spec/src/main/resources/json/schema/entity/data/table.json)
   and point out `$ref`, required fields, and `additionalProperties`.
2. The Context API assembles the graph around an asset into one `AIContext`
   document. `format=json` is for programs; the default Markdown rendering is
   ready for a model context window.
3. MCP does not create a second context model. It publishes the same capability
   as a tool, and its `inputSchema` is JSON Schema. Any compatible agent runtime
   can discover and validate the call.
4. Authorization happens while the context is assembled. The caller's token is
   part of the retrieval contract, so forbidden context never needs to be
   removed by a prompt.

Show the tool contract live:

```bash
curl -sS "$AI_SDK_HOST/mcp" \
  -H "Authorization: Bearer $AI_SDK_TOKEN" \
  -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","id":"schema","method":"tools/list","params":{}}' \
  | jq '.result.tools[] | select(.name == "get_asset_context") | .inputSchema'
```

Show that the REST representation is equally direct (set `TABLE_FQN` to an
ingested table):

```bash
curl -sS --get \
  "$AI_SDK_HOST/api/v1/tables/name/$TABLE_FQN/context" \
  -H "Authorization: Bearer $AI_SDK_TOKEN" \
  --data-urlencode "format=json" \
  | jq .
```

Then run the notebook's Markdown and JSON cells for one asset. Point out schema,
transformation/lineage, quality, glossary terms, and attached knowledge in the
single response. Finish with the persona notebook's two-token comparison: same
tool and same asset, but only the context each identity is allowed to see.

### What the audience should remember

The stable integration boundary is not a hand-written mega-prompt. It is a
typed, discoverable, permission-aware context operation.

## Act 2 — Build: use the AI Studio agent as the backend

Open <http://localhost:8080> and draw attention to the badge:
`AI Studio agent · no local LLM`.

Submit the prepared request, then show the small integration in
[`serve.js`](./serve.js):

```javascript
const client = new AISdk({ host: HOST, token: TOKEN });
const result = await client.agent("GDPRComplianceAnalyzer").invoke(message);
```

Talk track:

- The HTML collects a request and renders Markdown. It does not select a model,
  define tools, run a tool loop, or reconstruct catalog context.
- The thin server keeps the Collate JWT out of the browser and invokes the
  API-enabled agent built in AI Studio.
- The agent's persona, skills, corrections, context retrieval, and governance
  stay in Collate. Every application invoking this agent benefits from the same
  updates.
- `toolsUsed` at the bottom is useful stage evidence: the report was grounded by
  catalog search, entity context, and lineage rather than model memory.

### Transition to Act 3

> Sometimes delegation is the whole application. Sometimes we need our own
> workflow around it. We can extend the agent without forking its knowledge.

## Act 3 — Extend: our agent, Collate's context

Open <http://localhost:8081>. The page uses the same request form, but the badge
now reads `LangGraph · AI Studio + Collate experts`. A new **Who is doing the
work?** panel makes the ownership boundary visible and animates each real graph
node as it completes.

Submit the identical request. The response adds `Recommended assignees` and a
human handoff plan. Walk left-to-right through the graph:

1. **GDPR Agent / Collate AI Studio** owns the expensive data work: scoped
   search, context retrieval, lineage, PII, retention, and the compliance plan.
2. **Expert directory / our tool → Collate** reads live users/personas, Domain
   experts, and Data Product experts. The code defines the tool contract;
   Collate remains the source of truth and authorization boundary.
3. **Internal agent / our LangGraph app** matches the two governed results and
   writes only the assignee recommendation and approval-oriented handoff. The
   application prepends the AI Studio report unchanged.

At the bottom of the report, distinguish the two levels of tool evidence:
`LangGraph tools` are the two application boundaries, while `Inside the AI
Studio GDPR Agent` lists catalog tools run within the delegated agent.

For an observability-focused version of the talk, enable Langfuse before
starting Act 3. After the request, click **Open this execution in Langfuse** to
show the same nodes, timings, nested tools, and internal model generation:

```bash
export LANGFUSE_ENABLED=true
export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_SECRET_KEY="sk-lf-..."
# export LANGFUSE_BASE_URL="https://your-langfuse.example.com"  # self-hosted
make demo-gdpr-extended
```

Use this distinction in the talk: **LangGraph is the executable flow;
Langfuse is the per-run trace.** The in-page flow still works when Langfuse is
off.

Open [`extended/server.py`](./extended/server.py) and
[`extended/expert_directory.py`](./extended/expert_directory.py). The key reveal
is how little domain context exists in the internal prompt: LangGraph defines
the workflow, the prompt defines only handoff policy, and both tools retrieve
their own current context.

For the seeded Jaffle Shop data, useful evidence includes:

| Candidate | Governed signal | Likely handoff |
|---|---|---|
| Alice Johnson | Data Steward persona; Data Engineering expert | Coordinate privacy review and transformed copies |
| Eve Davis | Sales Domain expert | Own customer/order/support asset remediation |
| Bob Smith | Finance Domain expert | Resolve payment and finance retention conflicts |

Describe these as **recommendations**, not completed assignments. The demo does
not mutate ownership or create tickets.

### The final message

> The internal agent is replaceable. The context is not trapped inside it. A
> Python agent, a Java service, a TypeScript application, or an AI Studio agent
> can all retrieve the same governed truth and the same corrections from
> Collate.

## Failure-safe stage plan

- If the model provider is slow, use Act 1's raw Context API/MCP cells; they need
  no external LLM and prove the central claim deterministically.
- If Act 2 times out, show the already generated report and the `toolsUsed`
  console output, then explain the two-line SDK boundary.
- If expert discovery is partially unauthorized, keep the warning in the Act 3
  result. That is evidence of fail-closed governance, not something to hide.
- Keep screenshots of both final reports as a last resort, but run the Context
  API call live if at all possible.

## Claims to keep precise

- The Context API returns metadata and attached organizational knowledge; it is
  not a query engine for arbitrary warehouse rows.
- RBAC is enforced according to the identity represented by the JWT supplied to
  Collate.
- The internal handoff agent proposes assignees. It does not assign work.
- In Act 3, the configured internal model receives the DSAR and the AI Studio
  report so it can synthesize the handoff. Use an approved provider and your
  normal data-handling controls for a real request.
- The AI Studio path removes local model selection, tool definitions, and the
  tool-execution loop—not the need for a small credential-protecting backend in
  a browser application.
