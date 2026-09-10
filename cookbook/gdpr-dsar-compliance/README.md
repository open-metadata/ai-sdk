# GDPR DSAR Compliance

Trace customer data across your data catalog to handle GDPR Data Subject Access Requests (DSARs) for deletion, access, or rectification.

## Overview

When a customer requests data deletion under GDPR (e.g., "delete all my data"), this workflow:
1. Receives the customer's identifiers (name, email, customer ID)
2. Uses a Metadata AI agent to **search for tables** where the customer's data may reside
3. **Traces lineage** from those tables to discover related upstream sources and downstream copies
4. **Inspects table details** (columns, tags) to flag fields that likely contain PII
5. **Checks retention policies** on each table to identify conflicts with immediate deletion
6. Produces a structured compliance report with deletion steps, retention conflicts, and impact assessment

This cookbook has two runnable iterations:

- **AI Studio integration** — the browser uses a thin credential-protecting
  Node server to invoke the complete `GDPRComplianceAnalyzer`. There is no local
  model, tool loop, or agent definition.
- **Extended custom agent** — an explicit LangGraph reuses that same AI Studio
  agent as one tool, adds live Data Steward / Domain expert discovery from
  Collate, and can record the split in Langfuse. See [extended/](./extended/)
  and the complete [three-act demo guide](./DEMO_GUIDE.md).

## Prerequisites

- Collate/OpenMetadata instance with metadata ingested (tables, lineage, retention policies)
- PII classification tags applied to relevant assets (or auto-classification configured)
- API access enabled (JWT token)
- [Metadata AI CLI](../../cli/) or SDK installed (for agent setup)

## Architecture

```
┌────────────┐   POST /api/analyze   ┌────────────────┐   AI SDK invoke   ┌──────────────────────┐
│  Browser   │ ────────────────────► │ Thin Node      │ ────────────────► │ GDPRCompliance       │
│  (UI form) │ ◄──────────────────── │ server         │ ◄──────────────── │ Analyzer (AI Studio) │
└────────────┘   completed report    └────────────────┘                   └──────────┬───────────┘
                                                                                   │
                                                             1. searches catalog  │
                                                             2. traces lineage    │
                                                             3. inspects PII      │
                                                             4. checks retention  │
                                                                                   ▼
                                                                        Collate context + RBAC
```

## Step 1: Create the Agent

Create a Dynamic Agent with PII search and lineage tracing skills. The setup
also prevents similarly named assets from unrelated local services entering the
report:

- the `GDPRAnalyst` AI persona contains a fail-closed rule for the Jaffle Shop
  service and database;
- the Dynamic Agent's `knowledge.services` scope is restricted to the Jaffle
  Shop database service.

After ingesting PostgreSQL, run:

```bash
export AI_SDK_SERVICE="jaffle shop"
export AI_SDK_DATABASE="jaffle_shop"
make setup-gdpr-agent
```

The command creates missing entities and updates an existing
`GDPRAnalyst`/`GDPRComplianceAnalyzer` to the requested scope. See
[agent-config.md](./agent-config.md) for the exact persona rule and manual UI
setup.

## Step 2: Configure the Connection

Keep the JWT on the server, not in the HTML:

```bash
export AI_SDK_HOST="https://your-instance.getcollate.io"
export AI_SDK_TOKEN="your-jwt-token"
export AI_SDK_AGENT="GDPRComplianceAnalyzer"  # optional; this is the default
export AI_SDK_SERVICE="jaffle shop"            # used by setup-gdpr-agent
export AI_SDK_DATABASE="jaffle_shop"           # used by setup-gdpr-agent
```

## Step 3: Start the Demo

```bash
# Install dependencies and start the server
cd cookbook/gdpr-dsar-compliance
npm install
node serve.js

# Or from the repo root:
make demo-gdpr

# Override the OpenMetadata host / port:
AI_SDK_HOST=https://your-instance.getcollate.io PORT=3000 make demo-gdpr
```

Open `http://localhost:8080` (or the port you specified).

## Step 4: Submit a DSAR

Type your Data Subject Access Request in the text area and click **Submit Request** (or press `Ctrl+Enter`).

The UI shows a working state while the AI Studio agent completes its tool calls,
then renders the report and the names of the tools used.

![img.png](img.png)

### Example Prompts

**Deletion request (recommended starting point):**
```
Customer Michael Perez has requested
deletion of all his personal data under GDPR Article 17. Search for tables where
his data resides, trace lineage to find all related tables, identify PII columns
in each, and check retention policies for conflicts with immediate deletion.
```

**Access request:**
```
Customer Sara Chen has submitted a
Subject Access Request under GDPR Article 15. Find all tables containing her
data by searching for customer-related tables and tracing lineage. For each
table, list the PII columns and the retention period.
```

**Rectification request:**
```
Customer Diana Williams has requested rectification
of her address data under GDPR Article 16. Search for tables that store address
information, trace lineage to find downstream copies, and identify all locations
where her address data may need to be updated.
```

**Scope assessment:**
```
We need to assess the GDPR deletion impact for the customers table in the
jaffle shop database. Trace all downstream lineage from the customers table,
identify which downstream tables contain PII, and check whether their retention
policies are compatible with a 90-day customer data retention window.
```

## How It Works

The server uses the [TypeScript SDK](../../typescript/) (`@openmetadata/ai-sdk` on npm). It uses the SDK's `agent().invoke()` method to get the complete compliance report after the agent finishes all tool calls (search, lineage, detail inspection):

```javascript
import { AISdk } from '@openmetadata/ai-sdk';

const client = new AISdk({ host: HOST, token: TOKEN });

const result = await client.agent(AGENT_NAME).invoke(message);
// result.response contains the full compliance report (markdown)
// result.toolsUsed lists all tools the agent called
```

The agent executes multiple tool calls server-side (searching tables, tracing lineage, inspecting details) before returning the complete report. The same pattern works in Node.js for scripting or automation.

## Customization

### Adjust the Agent Persona

Edit the persona system prompt to focus on your organization's specific needs:
- Add references to your naming conventions (e.g., `*_pii` column suffix)
- Include your specific retention policy rules and legal hold requirements
- Specify the output format you need (JSON, markdown table, etc.)
- Adjust the lineage depth the agent should trace

See [agent-config.md](./agent-config.md) for the full system prompt template.

### Add to an Automated Workflow

Combine this with n8n or a scheduled script to process DSARs from a queue:

```python
from ai_sdk import AISdk

client = AISdk(host="https://...", token="...")

# Process a DSAR from your ticketing system
response = client.agent("GDPRComplianceAnalyzer").call(
    "Customer Michael Perez (customer_id: 1, email: mperez@example.com) has "
    "requested deletion of all his personal data. Search for tables where his "
    "data resides, trace lineage, identify PII, and check retention policies."
)

# Send the compliance report to your DSAR tracking tool
print(response.response)
```

### Extend It With Your Own Agent

Run the final iteration when you need application-specific orchestration around
the governed AI Studio analysis:

```bash
export OPENAI_API_KEY="your-provider-key"
make demo-gdpr-extended
```

Open `http://localhost:8081`. The shared UI now animates the three LangGraph
nodes and adds catalog-backed assignee recommendations to the same compliance
report. See [extended/README.md](./extended/README.md) for the architecture,
tool contracts, and optional Langfuse trace setup.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No response from agent | Verify `AI_SDK_TOKEN` is correct; check the server and browser consoles |
| Agent returns empty analysis | Ensure PII classification tags are applied to your assets in Collate |
| CORS error in browser | Use `serve.js` instead of a plain static server — it proxies API calls |
| `Proxy error` in response | Check that `AI_SDK_HOST` is reachable from where `serve.js` runs |
| Tool usage not showing | The agent may not need tools for simple queries; try a more specific request |

## Related Resources

- [Metadata AI TypeScript SDK](../../typescript/)
- [Metadata AI Python SDK](../../python/)
- [Metadata AI CLI](../../cli/)
- [Three-act Retrieve / Build / Extend demo guide](./DEMO_GUIDE.md)
- [Collate PII Classification Documentation](https://docs.getcollate.io)


## Demo Scenario: Michael Perez Requests Erasure

This demo is built around a concrete DSAR scenario using the Jaffle Shop demo database.

**The request:** Michael Perez (`customer_id=1`, `mperez@example.com`) wants all his personal data deleted under GDPR Article 17.

### What the Agent Should Do

1. **Search for customer tables** — The agent searches for "customer" tables and finds `raw_jaffle_shop.customers` as the primary source of customer data.

2. **Trace lineage** — From the customers table, the agent traces downstream lineage and discovers related tables: `orders`, `payments`, `user_sessions`, `tickets`, `reviews`, and the `analytics.customer_ltv` view.

3. **Inspect PII in each table** — For each discovered table, the agent inspects columns and tags to identify PII fields (email, phone, SSN, IP address, billing_email, free-text description fields, etc.).

4. **Check retention policies** — Each table has a retention period set. The agent should flag conflicts:

| Table | PII Present | Retention | Conflict |
|-------|-------------|-----------|----------|
| `customers` | email, phone, SSN, DOB, address | P90D | Source of truth — supports deletion |
| `payments` | billing_email, IP address | P180D | PII persists 90 days after customer record deleted |
| `orders` | customer_id FK | P3Y | Pseudonymous link survives ~3 years |
| `user_sessions` | customer_id FK, IP address | P1Y | Browsing PII survives 9 months after customer gone |
| `tickets` | free-text description | P1Y | May mention customer name/details |
| `reviews` | free-text review_text | P1Y | Unstructured PII risk |
| `customer_ltv` view | email + full name directly | P5Y | Exposes PII from deleted source for ~5 years |

### Key Flags the Agent Should Raise

1. **Billing email duplication** — `payments.billing_email` stores the same email as `customers.email` but with 2x longer retention
2. **Aggregated view leaks source PII** — `analytics.customer_ltv` selects `c.email` and `first_name || last_name` but has a 5Y retention vs 90D on the source table
3. **FK orphan chain** — Deleting from `customers` orphans `orders`, which orphans `payments`, which orphans `refunds` — cascading integrity issues
4. **Free-text PII in support tickets** — The `description` field in tickets and `review_text` in reviews may contain customer names or details that can't be systematically purged
