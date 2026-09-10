# Persona-aware Context: One Agent, Two Users, Two Realities

The same AI agent answers the same question for two different people — and each
gets a different, correct answer. Not because the agent has two prompts, but
because **OpenMetadata scopes what each identity is allowed to see** at the MCP
layer.

It builds on one new primitive: the **`/context` endpoint**
(`GET /v1/{entityType}/name/{fqn}/context`, `EntityResource.getAiContextByName`)
and its MCP tool `get_asset_context`. One call walks the knowledge graph outward
from an entity and returns a single rendered **Context Profile** — description,
tags, glossary, lineage, profile, data quality, and attached Context Center
knowledge — ready to drop into an LLM. Three capabilities then combine:

- **AI Entity Context** (`get_entity_details` with `include=["context"]`) — the
  full Context Profile of a single asset, **RBAC-filtered live by the caller**.
  The Compliance Officer owns the asset and sees its sensitive column profiles;
  the Data Engineer gets the same asset with those profiles withheld. (Earlier
  notes call this tool `get_asset_context`; on an OpenMetadata 2.0 server it is a
  section of `get_entity_details`.)
- **AI Persona Context** (`get_persona_context`) — a curated, per-persona working
  document. The Compliance persona surfaces PII, glossary terms, and data
  quality; the Data Engineer persona surfaces schema, lineage, and profiling.
  Same catalog, different lens.
- **Operating rules** — a Knowledge Article per persona that encodes *behaviour*,
  not facts: "cite the retention policy", "give the dbt model path". Each one is
  pulled in by that persona's own `page` rule, so it appears in exactly one
  persona's document. `setup_demo.py` also writes the same guidance as a private
  `Preference` memory per user, which is how you would model a genuinely
  per-*person* rule — see [Troubleshooting](#troubleshooting) for what current
  builds surface.

## Business Problem

**Scenario:** You are putting an AI assistant in front of your data catalog. The
catalog contains sensitive customer data — names, emails, phone numbers, postal
codes, dates of birth. Two very different people ask it for help:

- **David Kim, Compliance Officer** — needs to see exactly which fields are
  sensitive, whether they're documented, and whether data-quality checks pass.
- **Sara Johnson, Data Engineer** — needs schema, joins, lineage, and freshness
  to build and fix pipelines. She should *not* see customer contact detail.

**The wrong way:** encode "who sees what" in the agent's prompt, or run two
different agents. Prompts leak, drift, and can be jailbroken — and the model
still *received* the sensitive data over the wire.

**The right way:** the agent is identical for everyone. Access control and
persona curation live in the platform. The MCP tools only ever return what the
current token is allowed to see, so the model never even receives data the user
can't access.

## Architecture

```
              Same code · same prompt · same question
                               │
             ┌─────────────────┴──────────────────┐
             │                                     │
     David Kim's token                     Sara Johnson's token
     (ComplianceOfficer)                     (DataEngineer)
             │                                     │
     ┌───────▼────────┐                    ┌───────▼────────┐
     │  LangChain     │                    │  LangChain     │
     │  agent         │   ← identical →    │  agent         │
     └───────┬────────┘                    └───────┬────────┘
             │      client.mcp.as_langchain_tools(...)      │
             └──────────────────┬──────────────────────────┘
                                │
                   ┌────────────▼─────────────┐
                   │   OpenMetadata 2.0        │
                   │   MCP server              │
                   │                           │
                   │  get_persona_context  ──► persona rules   (Axis B)
                   │  get_entity_details   ──► RBAC/PII masking (Axis A)
                   │    include=["context"]
                   └───────────────────────────┘
                                │
        David → curated compliance view · UNMASKED PII
        Sara  → curated engineering view · MASKED PII
```

### How the scoping works (server-side)

| Lever | Tool | What differs | Mechanism |
|------|------|--------------|-----------|
| **Persona** | `get_persona_context` | Which assets and which *sections* render | Admin-authored `contextDefinition` rules on the persona (entityType + queryFilter + sections). Resolved from the caller's active/default persona. |
| **Entity RBAC** | `get_entity_details` | Whether PII column profiles and sample rows render | OpenMetadata withholds the profile of a `PII.Sensitive` **column**, and masks sample rows **wholesale**, for everyone except **admins, bots, and owners**. The schema still lists the column; its distribution and values are gone. |
| **Operating rules** | `get_persona_context` | Which "how to answer" article appears | A second persona rule over `entityType: page` selecting one Knowledge Article by name. The article is attached to no asset, so nothing else can pull it in. |

The agent never chooses a persona or filters anything — it just calls the tools.
Everything else is OpenMetadata.

## Prerequisites

- The [Jaffle Shop demo database](../resources/demo-database/) running and
  ingested into an **OpenMetadata 2.0** instance as a database service named
  `jaffle shop`:

  ```bash
  make demo-database     # from the repo root: Postgres on :5433 + Metabase
  make demo-dbt          # build the dbt models
  # then run an OpenMetadata metadata ingestion against localhost:5433
  ```

  Everything else — users, personas, PII tags, column profiles, data-quality
  results, glossary, articles — is created by `setup_demo.py`.
- Python 3.10+, and `psycopg2-binary` for the profiling step
- An OpenAI API key (or any LangChain-compatible LLM — see [Configuration](#configuration))

## Installation

```bash
pip install "data-ai-sdk[langchain]" langchain langchain-openai requests
```

> Requires `data-ai-sdk` ≥ the release that adds the OpenMetadata 2.0 MCP tools
> (`get_asset_context`, `get_persona_context`). Earlier versions silently drop
> unknown server tools.

## Setup

### 1. Configure the demo

Run the setup script **once, with an admin token**. It is idempotent.

```bash
export AI_SDK_HOST="http://localhost:8585"
export AI_SDK_TOKEN="<admin-jwt>"

python setup_demo.py
```

It is idempotent and self-contained. It creates the demo **users**
(`david.kim`, `sara.johnson`) and the `ComplianceOfficer` / `DataEngineer`
**personas** if they don't already exist, then:

- **Baseline access** — grants both users the built-in `DataConsumer` role. New users
  inherit their permissions from their teams' default roles; on an instance where
  `Organization` carries none, every non-admin call fails with
  `403 ... operations [ViewAll] not allowed` and the demo looks broken rather than
  scoped. Both users get the *same* role — they diverge through ownership and persona.
  Disable with `--skip-roles`.
- **PII tags** — tags the sensitive columns (`email`, `phone_number`, `ssn_last_four`,
  `date_of_birth`, names, address) on the customer tables. Masking is per **column**;
  a table-level tag masks nothing. Disable with `--skip-pii-tags`.
- **Profiles + sample rows** — profiles the demo tables straight from the running demo
  Postgres and pushes column profiles and sample rows over the REST API. A metadata-only
  ingestion carries neither, and masking that has nothing to hide is invisible.
  Needs `psycopg2`; skipped with a warning if it or the database is unavailable.
  Disable with `--skip-profiles`.
- **Data-quality results** — executes the tests dbt ingestion registered but never ran,
  so `dataQuality` reports a verdict instead of "0 passed, 0 failed". Adds one extra test
  (`not_null` on `email`) that genuinely fails on the demo data. Disable with
  `--skip-tests`.
- **Governance content** — creates a `Data Governance` glossary (terms tagged onto the
  demo table) and the long `Customer 360 Data Model` article linked to it, so the
  Compliance persona's `glossaryTerms` and `articles` sections render real content while
  the Engineer persona (which has neither section) shows none. Also creates one
  **operating-rules article per persona**. Disable with `--skip-knowledge`.
- **Persona context** — attaches `contextDefinition` rules to both personas: one over the
  PII-tagged tables with different `sections` each, plus one over `entityType: page`
  selecting that persona's operating-rules article. Rules are **replaced** on re-run, so
  editing the script and running it again actually takes effect.
- **Default persona** — sets each demo user's `defaultPersona` (David →
  `ComplianceOfficer`, Sara → `DataEngineer`) and guarantees persona membership.
  `get_persona_context` (called with no persona name, as the agent does) resolves the
  caller's active persona, falling back to `defaultPersona` — **without this the persona
  scene is empty**. Disable with `--skip-default-persona`.
- **Entity RBAC** — adds David Kim as an **owner** of the PII tables, so the Context
  Profile keeps their PII column profiles for him and drops them for Sara.
- **Ground rules** — writes a private `Preference` memory per user (owner-only
  visibility) attached to the demo table. Disable with `--skip-ground-rules`.

Preview without changing anything:

```bash
python setup_demo.py --dry-run
```

Point it at a differently named service, pin specific tables, or — on enterprise
builds with policy-driven masking — also create an allow-policy/role:

```bash
python setup_demo.py --service "my jaffle service"
python setup_demo.py --pii-table-fqn "jaffle shop.jaffle_shop.marts_core.dim_customers"
python setup_demo.py --with-pii-policy
```

> **Why ownership, not a DENY policy?** In open-source OpenMetadata, PII
> unmasking is `isAdmin || isBot || isOwner` — no permission operation unmasks
> it, so masking is already the default for non-owners. Making the Compliance
> Officer an *owner* is the lever that creates the visible difference. The
> optional `--with-pii-policy` path is for enterprise authorizers whose masking
> is policy-driven.

### 2. Get one token per user

The demo needs a token for **each** user so the MCP calls run under their real
identity (this is what makes RBAC apply).

`setup_demo.py` does this for you on **basic-auth** instances: it sets a password
on each demo user, logs in as them, and prints a paste-ready line:

```bash
export DEMO_COMPLIANCE_TOKEN=<david.kim's token>
export DEMO_ENGINEER_TOKEN=<sara.johnson's token>
```

On SSO instances (Google/Okta/…) there is no password login — and OpenMetadata
forbids an admin from minting another user's token (anti-impersonation) — so the
script prints guidance instead: log in **as each user**, open their profile →
**Access Tokens** → Generate. (Bot tokens won't work — they bypass PII masking,
which is exactly the contrast the demo shows.)

## Environment

```bash
export AI_SDK_HOST="http://localhost:8585"
export DEMO_COMPLIANCE_TOKEN="<david.kim's token>"
export DEMO_ENGINEER_TOKEN="<sara.johnson's token>"

# Required only for the agent scenes (not for --no-agent):
export OPENAI_API_KEY="..."

# Optional:
export DEMO_MODEL="openai:gpt-4o"                          # or anthropic:claude-sonnet-5
export DEMO_TABLE_FQN="jaffle shop.jaffle_shop.marts_core.dim_customers"
```

## Running

Two ways to run the same demo:

- **Notebook — recommended for showcasing.** [`persona_demo.ipynb`](./persona_demo.ipynb)
  renders both users **side by side** and shows the RBAC **diff inline**. Set `AI_SDK_HOST`,
  `DEMO_COMPLIANCE_TOKEN`, and `DEMO_ENGINEER_TOKEN` (plus an LLM key for the optional agent
  cells), then run it top to bottom. `USE_AGENT` auto-detects an LLM key — the raw-tool proof
  needs no key at all.
- **Script — same logic for the terminal / CI.** `persona_demo.py`:

```bash
# Full demo — both scenes, agent answers + deterministic raw-tool diff
python persona_demo.py

# The undeniable proof, no LLM key required (raw MCP tool output diff)
python persona_demo.py --no-agent

# Just the RBAC scene, against a specific table
python persona_demo.py --scene asset --table-fqn "jaffle shop.jaffle_shop.marts_core.dim_customers"
```

- `--scene {persona,asset,all}` — which scene(s) to run.
- `--no-agent` — skip the LLM; show only the raw tool diff (great for a stage
  reveal, and needs no OpenAI key).
- `--no-raw` — skip the diff; show only the agent answers.

## Example Output

### Scene 1 — AI Persona Context ("what should I focus on?")

Both users ask the identical question. `get_persona_context` returns each one's
curated document. Same four PII-tagged tables, two lenses.

**David Kim (ComplianceOfficer):**
```markdown
# Rule: Sensitive customer and account data (table) — 4 matched, 4 rendered

## Table: dim_customers
### Tags
`PII.Sensitive`
### Business Definitions
##### Data Retention · ##### Personally Identifiable Information
### Knowledge Articles
##### Customer 360 Data Model
### Data Quality
Tests — passed: 4, failed: 1, aborted: 0
> 1 data-quality test(s) are currently failing on this asset — qualify any answer accordingly.

# Rule: Compliance Operating Rules (how to answer) (page) — 1 matched, 1 rendered
- Lead with its owner, its domain, and its governance status.
- Cite the governing policy (retention, consent basis) and the glossary term.
```

**Sara Johnson (DataEngineer):**
```markdown
# Rule: Customer and account data pipelines (table) — 4 matched, 4 rendered

## Table: dim_customers
### Schema
| customer_id | integer | ... | Unique customer identifier |
| email | text | ... | Customer email (PII - may be null for data quality issues) |
### Lineage
stg_jaffle_shop__customers → dim_customers  (column-level)
### Data Profile
25 rows · customer_id 100% unique

# Rule: Engineering Operating Rules (how to answer) (page) — 1 matched, 1 rendered
- Give the dbt model path, e.g. `models/marts/core/dim_customers.sql`.
- Include a short, runnable `SELECT` the reader can paste.
```

Same tables, same question — a compliance lens vs an engineering lens, each with
its own operating rules.

### Scene 2 — AI Entity Context (RBAC / PII masking)

Both users read the **same** `dim_customers` Context Profile. The diff shows what
only the owner can see:

```diff
--- David Kim · owner
+++ Sara Johnson · non-owner
 | Column | Null % | Distinct | Min | Max |
 |--------|--------|----------|-----|-----|
 | customer_id | 0% | 25 | 1.0 | 25.0 |
-| first_name | 4% | 23 |  |  |
-| last_name | 0% | 24 |  |  |
-| full_name | 4% | 23 |  |  |
-| email | 8% | 22 |  |  |
-| phone_number | 4% | 23 |  |  |
 | city | 4% | 22 |  |  |
-| postal_code | 4% | 22 |  |  |
```

```
David Kim    (owner)     : 26 columns profiled
Sara Johnson (non-owner) : 20 columns profiled

Withheld from Sara : email, first_name, full_name, last_name, phone_number, postal_code
Still in her schema: True — she sees the columns exist, not their distributions
```

Sample rows go further — one sensitive column redacts the whole grid, because a row
is only as shareable as its most sensitive field:

```
David Kim    — 0/26 columns masked
customer_id | first_name | last_name | full_name     | email
1           | Michael    | Perez     | Michael Perez | mperez@example.com

Sara Johnson — 26/26 columns masked
customer_id [MASKED] | first_name [MASKED] | ... | email [MASKED]
********             | ********            | ... | ********
```

> **`sampleData` is JSON-only.** It lives at `assetContext.table.sampleData`; the
> `format=markdown` render has no Sample Data section, so ask for `format="json"` when you
> want the rows.

Structure is metadata; distributions and values are data. Sara's agent never receives the
withheld rows, so no amount of prompting can make it reveal them.

## Configuration

### Using a different LLM

`--model` / `DEMO_MODEL` accept any LangChain model id:

```bash
python persona_demo.py --model anthropic:claude-sonnet-5   # needs ANTHROPIC_API_KEY
python persona_demo.py --model openai:gpt-4o               # default
```

The differentiation is server-side, so the choice of model doesn't affect what
each user is allowed to see — only how the answer is phrased.

### Identity via impersonation (alternative)

This demo uses two real user tokens — the cleanest way to make RBAC apply. If you
prefer a single bot token with `X-Impersonate-User`, note that the SDK's MCP
client does not forward custom headers; you'd call the `/mcp` endpoint directly.
Two user tokens is the recommended path.

## Troubleshooting

| Symptom | Cause / Fix |
|---------|-------------|
| `403 ... operations [ViewAll] not allowed` on every call | The demo user has no role. Re-run `setup_demo.py` (it grants `DataConsumer`), or add a default role to the `Organization` team. |
| Scene 1 renders the same document for both users | `setup_demo.py` didn't apply the persona rules. Re-run it with an admin token and check both personas exist. |
| Scene 1 is stale after you changed the catalog | The persona document is cached (`cacheTtlMinutes`, set to 5 by this demo). Wait it out or lower it further. |
| A persona rule shows "0 matched" | The `queryFilter` matched nothing. Filters over the **page** index need an explicit `{"query": ...}` wrapper; table filters do not. |
| Scene 2 shows no difference | Either the sensitive columns aren't tagged `PII.Sensitive` (masking is per *column* — a table-level tag does nothing), or the table has no column profile to withhold, or David isn't an owner. Re-run `setup_demo.py`; it does all three. |
| Data quality reads "0 passed, 0 failed" | dbt ingestion registers tests but never runs them. `setup_demo.py --skip-tests` was passed, or `psycopg2` / the demo database wasn't reachable. |
| `Unknown tool: invalid_tool_name` | The server doesn't advertise a tool in the list. On OpenMetadata 2.0 the asset Context Profile lives in `get_entity_details(include=["context"])`, not a separate `get_asset_context`. Both notebook and script intersect their wanted tools with `list_tools()`. |
| Sample rows missing from the Context Profile | `sampleData` is returned only with `format=json` (at `assetContext.table.sampleData`); the markdown render omits it. Also check the table actually has sample data — `setup_demo.py` pushes it from the demo Postgres. |
| The `?query=` excerpt never changes | The attached article is under ~1500 chars (so not truncated), fits in one ~380-word chunk, or the instance has no vector embeddings. |
| Private `Preference` memories don't appear in the Context Profile | Current builds surface `Private` memories to admins only; the per-role difference in this demo comes from the persona operating-rules articles instead. Setting a memory's visibility to `Entity` makes it visible to every caller who can see the asset. |
| `get_persona_context` returns "No active persona is configured for this user" | The caller has no `defaultPersona`. Re-run `setup_demo.py`, or set it in the UI: user profile → default persona. |
| 403 on `setup_demo.py` | `AI_SDK_TOKEN` must be an **admin** token — persona AI-context config is admin-only. |
