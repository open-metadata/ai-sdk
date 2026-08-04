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

- **AI Entity Context** (`get_asset_context`) — the full Context Profile of a
  single asset, **RBAC-filtered live by the caller**. A Compliance Officer sees
  sensitive PII column profiles and sample values; a Data Engineer gets the same
  asset with those columns masked.
- **AI Persona Context** (`get_persona_context`) — a curated, per-persona working
  document. The Compliance persona surfaces PII, glossary terms, and data
  quality; the Data Engineer persona surfaces schema, lineage, and profiling.
  Same catalog, different lens.
- **Context Center ground rules** — private `Preference` memories (and Knowledge
  Articles) that encode *behavior*, not facts: "cite the retention policy",
  "never select PII into a non-secure mart". They attach to assets and surface in
  `/context` **per person** — each user sees only their own.

## Business Problem

**Scenario:** You are putting an AI assistant in front of your data catalog. The
catalog contains sensitive customer data — SSNs, tax IDs, IBANs. Two very
different people ask it for help:

- **David Kim, Compliance Officer** — needs to see exactly which fields are
  sensitive, whether they're documented, and whether data-quality checks pass.
- **Sara Johnson, Data Engineer** — needs schema, joins, lineage, and freshness
  to build and fix pipelines. She should *not* see raw SSN values.

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
                   │  get_asset_context    ──► RBAC/PII masking (Axis A)
                   └───────────────────────────┘
                                │
        David → curated compliance view · UNMASKED PII
        Sara  → curated engineering view · MASKED PII
```

### How the scoping works (server-side)

| Lever | Tool | What differs | Mechanism |
|------|------|--------------|-----------|
| **Persona** | `get_persona_context` | Which assets and which *sections* render | Admin-authored `contextDefinition` rules on the persona (entityType + queryFilter + sections). Resolved from the caller's active/default persona. |
| **Entity RBAC** | `get_asset_context` | Whether PII columns are masked | OpenMetadata masks `PII.Sensitive` column profiles and sample values for everyone except **admins, bots, and owners** of the asset. |
| **Ground rules** | `get_asset_context` | Which operating rules appear | Private `Preference` Context Center memories, owned per user (owner-only visibility); every knowledge item is also re-checked against the caller's permissions, fail-closed. |

The agent never chooses a persona or filters anything — it just calls the tools.
Everything else is OpenMetadata.

## Prerequisites

- The [banking](../resources/banking/) cookbook ingested into an
  **OpenMetadata 2.0** instance. This provides the tables, the `PII` classification
  on customer columns, and the `ComplianceOfficer` / `DataEngineer` personas with
  users David Kim and Sara Johnson assigned.
- Python 3.10+
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

It is idempotent and self-contained: it first creates the demo **users**
(`david.kim`, `sara.johnson`) and the `ComplianceOfficer` / `DataEngineer`
**personas** if they don't already exist, then does five things:

- **Persona context** — attaches `contextDefinition` rules to the `ComplianceOfficer`
  and `DataEngineer` personas (different `sections` over the same PII-tagged tables).
- **Governance content** — creates a `Data Governance` glossary (terms tagged onto the
  PII table) and one Knowledge Center article linked to it, so the Compliance persona's
  `glossaryTerms` and `articles` sections render real content while the Engineer persona
  (which has neither section) shows none. Disable with `--skip-knowledge`.
- **Default persona** — sets each demo user's `defaultPersona` (David →
  `ComplianceOfficer`, Sara → `DataEngineer`) and guarantees persona membership.
  `get_persona_context` (called with no persona name, as the agent does) resolves the
  caller's active persona, falling back to `defaultPersona` — **without this the persona
  scene is empty**. Disable with `--skip-default-persona`.
- **Entity RBAC** — adds David Kim as an **owner** of the PII tables, so
  `get_asset_context` returns unmasked PII for him and masked PII for Sara.
- **Ground rules** — creates a private `Preference` memory per user (owner-only
  visibility) attached to the PII table, so each person's `get_asset_context`
  carries their own operating rules. Disable with `--skip-ground-rules`.

Preview without changing anything:

```bash
python setup_demo.py --dry-run
```

Pin specific tables (instead of search discovery) and, on enterprise builds with
policy-driven masking, also create an allow-policy/role:

```bash
python setup_demo.py \
  --pii-table-fqn redshift.banking.marts_core.dim_customers \
  --with-pii-policy
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
export DEMO_TABLE_FQN="redshift.banking.marts_core.dim_customers"
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
python persona_demo.py --scene asset --table-fqn redshift.banking.marts_core.dim_customers
```

- `--scene {persona,asset,all}` — which scene(s) to run.
- `--no-agent` — skip the LLM; show only the raw tool diff (great for a stage
  reveal, and needs no OpenAI key).
- `--no-raw` — skip the diff; show only the agent answers.

## Example Output

### Scene 1 — AI Persona Context ("what should I focus on?")

Both users ask the identical question. `get_persona_context` returns each one's
curated document.

**David Kim (ComplianceOfficer):**
```markdown
# Your Working Context — Compliance Officer

## dim_customers
Sensitive customer master data.
**Tags:** PII.Sensitive (ssn, tax_id, date_of_birth), PII.NonSensitive (email)
**Glossary terms:** Personally Identifiable Information, Data Retention
**Knowledge article:** Customer PII Handling Policy — restrict SSN/tax_id, cite retention, confirm consent
**Data quality:** 4/5 tests passing — 1 failing: `ssn_not_null`
```

**Sara Johnson (DataEngineer):**
```markdown
# Your Working Context — Data Engineer

## dim_customers
**Schema:** customer_id (PK), first_name, last_name, ssn, email, branch_id (FK → dim_branches)
**Frequent joins:** dim_branches (branch_id), fct_transactions (customer_id)
**Lineage:** stg_core_banking__customers → dim_customers → fct_customer_360
**Profile:** 5,000 rows · customer_id 100% unique · updated 2h ago
```

Same table, same question — a compliance lens vs an engineering lens.

### Scene 2 — AI Entity Context (RBAC / PII masking)

Both users call `get_asset_context` on the **same** `dim_customers`. The diff
shows what only one of them can see — both the data *and* the ground rules:

```diff
--- ComplianceOfficer
+++ DataEngineer
   ## Data Profile
   | Column   | Null % | Distinct |
-  | ssn      | 0.0%   | 5000     |   ← David sees real profiles + sample values
-  | tax_id   | 0.0%   | 5000     |
+  | ssn [MASKED]    | —  | — |       ← Sara: PII columns masked
+  | tax_id [MASKED] | —  | — |

   ## Knowledge
-  Ground rules: handling customer PII — cite retention, flag every PII field.
+  Ground rules: building on customer data — prefer masked marts, document SLAs.
```

Each person's *own* `Preference` memory shows up (private, owner-scoped); neither
sees the other's. The agent, told to be faithful, reports it plainly: David
summarizes the SSN distribution and echoes his retention rule; Sara says *"the
`ssn` and `tax_id` columns are masked — I can see they exist and their types, but
not their values,"* and follows her masked-marts rule.

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
| Scene 1 diff is empty | `setup_demo.py` didn't apply persona rules. Re-run it with an admin token; check the personas exist (`ComplianceOfficer`, `DataEngineer`). |
| Scene 2 shows no masking difference | David isn't an owner of the table, or the build unmasks differently. Re-run `setup_demo.py` (Axis A), or pass `--pii-table-fqn`. On enterprise builds try `--with-pii-policy`. |
| `get_persona_context` returns nothing / "No active persona is configured for this user" | The caller has no `defaultPersona`. Re-run `setup_demo.py` (it sets one per demo user), or set it in the UI: user profile → default persona. |
| Tools missing / agent ignores them | Upgrade `data-ai-sdk` to a version with the 2.0 MCP tools. |
| 403 on `setup_demo.py` | `AI_SDK_TOKEN` must be an **admin** token — persona AI-context config is admin-only. |
