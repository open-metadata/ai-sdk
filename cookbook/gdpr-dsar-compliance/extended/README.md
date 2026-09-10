# Extended GDPR Agent: Visible LangGraph + Optional Langfuse Trace

This is the third act of the GDPR demo. It defines our application workflow as
an explicit LangGraph while reusing the same browser UI and the same AI Studio
`GDPRComplianceAnalyzer` from the base cookbook.

```text
Browser
  -> LangGraph (our workflow)
       |
       |- 1. Collate AI Studio: GDPR Agent
       |       `- scoped catalog search, PII, lineage, retention analysis
       |
       |- 2. Our tool -> Collate: Expert directory
       |       `- users, Data Steward personas, Domain/Data Product experts
       |
       `- 3. Our internal agent
               `- match evidence to people and write the human handoff
```

The workflow does not contain a list of employees or a copy of the catalog.
Both are looked up under `AI_SDK_TOKEN` at request time. The AI Studio report is
prepended to the result unchanged; the internal model only produces the
`Recommended assignees` and `Handoff` sections.

The browser renders the graph without an external service and updates each node
as it completes. Langfuse is optional: enable it when you also want a durable,
nested trace with timings and model/tool observations.

## Prerequisites

- Python 3.10+
- An API-enabled `GDPRComplianceAnalyzer`; see
  [`../agent-config.md`](../agent-config.md)
- The agent knowledge scope restricted to database service `jaffle shop`, with
  the matching fail-closed rule in its `GDPRAnalyst` persona. Running
  `make setup-gdpr-agent` configures both.
- Jaffle Shop metadata and organizational context; rerun the idempotent
  [`create_owners_and_domains.py`](../../resources/demo-database/scripts/create_owners_and_domains.py)
- A provider key for the model used by the internal handoff agent

## Run

From the repository root:

```bash
export AI_SDK_HOST="http://localhost:8585"
export AI_SDK_TOKEN="<local-admin-jwt>"
export OPENAI_API_KEY="<provider-key>"
export AI_SDK_SERVICE="jaffle shop"
export AI_SDK_DATABASE="jaffle_shop"

# Optional overrides
export AI_SDK_AGENT="GDPRComplianceAnalyzer"
export DEMO_MODEL="openai:gpt-4o"
export PORT=8081

make demo-gdpr-extended
```

Replace `AI_SDK_HOST` with your Collate URL when the catalog is not local.

`AI_SDK_SERVICE` and `AI_SDK_DATABASE` are consumed during
`make setup-gdpr-agent`; the extended workflow deliberately does not rebuild
that scope in each request.

Open <http://localhost:8081>. Use the same Michael Perez request as the base
demo. The result should include both the compliance report and a catalog-backed
handoff plan. The `Who is doing the work?` panel animates these actual LangGraph
nodes as the newline-delimited response streams back to the page.

## Optional: record the run in Langfuse

The in-page graph works with no Langfuse account. To record the full execution,
configure either Langfuse Cloud or a self-hosted Langfuse instance before
starting the demo:

```bash
export LANGFUSE_ENABLED=true
export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_SECRET_KEY="sk-lf-..."

# Only for a non-default region or self-hosted instance:
export LANGFUSE_BASE_URL="https://your-langfuse.example.com"

make demo-gdpr-extended
```

After a successful request, the page displays **Open this execution in
Langfuse** when the SDK can resolve the project's trace URL. The trace root is
`gdpr-handoff-workflow`; beneath it, the Langfuse LangChain callback records the
LangGraph nodes, both tool calls, and the internal model generation. The remote
AI Studio agent remains one delegated observation, while its returned
`collateToolsUsed` list shows the tools it ran inside Collate.

Tracing is an explicit opt-in because a trace contains the submitted DSAR, the
AI Studio report, and the visible expert-directory result. Use only an approved
Langfuse deployment and data-handling configuration for real requests.

## LangGraph versus Langfuse

| Component | Role in this demo | Required? |
|---|---|---|
| LangGraph | Defines and executes the three-node application workflow; exposes Mermaid and streams node completion to the browser | Yes, installed by `make demo-gdpr-extended` |
| Langfuse | Stores and visualizes individual executions, timings, nested tool/model calls, and inputs/outputs | No, enabled only with `LANGFUSE_ENABLED=true` and credentials |

## What the expert tool reads

`CollateExpertDirectory` combines these read-only API views:

| Source | Fields used | Why |
|---|---|---|
| `/api/v1/users` | teams, roles, personas, domains | Find human users assigned a Data Steward role/persona and enrich contact context |
| `/api/v1/domains` | experts | Find subject-matter experts for affected business domains |
| `/api/v1/dataProducts` | domain, experts | Find experts for a more specific governed product when available |

Each returned recommendation carries its evidence as structured `signals`. An
endpoint that is missing or forbidden becomes an explicit warning; results from
the other sources remain usable.

## Tool schemas

Both tools use Pydantic input models, which publish JSON Schema at their
boundaries. You can inspect the exact contracts without invoking a model:

```bash
PYTHONPATH="python/src:cookbook/gdpr-dsar-compliance/extended" python3 - <<'PY'
import json
from server import ExpertDirectoryInput, GDPRAnalysisInput

print(json.dumps(GDPRAnalysisInput.model_json_schema(), indent=2))
print(json.dumps(ExpertDirectoryInput.model_json_schema(), indent=2))
PY
```

That is the same contract pattern introduced in Act 1: discoverable inputs,
validated at the tool boundary, with current governed context retrieved only
when the tool runs. LangGraph defines the order; the schemas still define what
can cross each boundary.

## Test

The tests use an in-memory HTTP transport and do not need Collate or an LLM:

```bash
pytest -q cookbook/gdpr-dsar-compliance/extended/tests
```

## Production notes

This is intentionally demo-sized. Before production use, add your normal web
authentication, request audit trail, case/ticket integration, rate limits, and
an approval step before assigning a person or changing catalog metadata. The
configured internal model receives the DSAR, the AI Studio report, and the
expert context; use only an approved provider and data-handling configuration
for real requests.

## Framework references

- [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [Langfuse Python SDK](https://python.reference.langfuse.com/langfuse)
- [Langfuse trace URLs](https://langfuse.com/docs/observability/features/url)
