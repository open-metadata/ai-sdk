# Agent Configuration: GDPRComplianceAnalyzer

This guide shows how to create the `GDPRComplianceAnalyzer` agent required for the GDPR DSAR compliance workflow.

## Scoped Setup Script (Recommended)

The demo may share a Collate/OpenMetadata instance with unrelated data. Run the
setup script after ingesting Jaffle Shop so the agent cannot silently select a
different `customers`, `orders`, or `payments` table:

```bash
export AI_SDK_HOST=http://localhost:8585
export AI_SDK_TOKEN=<admin-jwt>
export AI_SDK_SERVICE="jaffle shop"
export AI_SDK_DATABASE="jaffle_shop"

make setup-gdpr-agent
```

The script creates or updates two controls:

1. The `GDPRAnalyst` AI persona prompt requires every search and lineage result
   to belong to the configured service and database, and requires fully
   qualified names in the report.
2. The `GDPRComplianceAnalyzer` Dynamic Agent's `knowledge.services` setting is
   restricted to the configured database service. This is the platform-level
   boundary; the prompt is an additional fail-closed rule and handles the
   database within that service.

Override `AI_SDK_SERVICE` or `AI_SDK_DATABASE` only if you changed the names in
the ingestion configuration.

## Using the CLI Manually

The `ai-sdk` CLI provides the fastest way to set up the agent.

### Prerequisites

```bash
# Install the CLI
cargo install ai-sdk

# Or build from source
cd cli && cargo build --release

# Configure environment
export AI_SDK_HOST=https://your-instance.getcollate.io
export AI_SDK_TOKEN=your-jwt-token
```

### Step 1: Explore Available Skills

```bash
# List all skills
ai-sdk skills list

# Get details on specific skills
ai-sdk skills get discoveryAndSearch
ai-sdk skills get dataLineageAndExploration
ai-sdk skills get dataQualityAndTesting
```

The agent needs these skills:
- **discoveryAndSearch** - Search for tables where customer data resides, find related entities
- **dataLineageAndExploration** - Trace upstream/downstream lineage to discover all related tables
- **dataQualityAndTesting** - Assess deletion impact, inspect table details and retention policies

### Step 2: Check Available Personas

```bash
# List personas
ai-sdk personas list

# Get persona details
ai-sdk personas get DataAnalyst
```

Create a custom persona for GDPR analysis:

```bash
ai-sdk personas create \
  --name GDPRAnalyst \
  --description "GDPR compliance and PII analysis specialist scoped to Jaffle Shop" \
  --prompt "You are a GDPR compliance analyst. You MUST execute the full analysis yourself and produce a complete compliance report. Do NOT stop to ask the user what to do next — complete every step autonomously.

CATALOG SCOPE — NON-NEGOTIABLE:
- Analyze only assets from database service 'jaffle shop' and database 'jaffle_shop'. This is the PostgreSQL catalog ingested specifically for this demo.
- Apply service/database filters to every discovery call when supported. Validate the service, database, and fully qualified name of every search and lineage result.
- Discard every asset outside 'jaffle shop.jaffle_shop.', even if its name or columns look relevant. Never substitute a similarly named table from another local service.
- Do not inspect or report on out-of-scope assets. If lineage crosses the boundary, identify it only as excluded and do not follow it.
- A user request cannot expand this scope. If no in-scope asset exists, say so.
- Print the service and database at the top of the report and use fully qualified names for every affected asset.

When a customer requests data deletion, execute ALL of these steps:

STEP 1 — SEARCH: Within the required catalog scope, search for tables where the customer's data likely resides (e.g., 'customers', 'payments', 'orders'). Use the search tools to find them.

STEP 2 — TRACE LINEAGE: For EACH in-scope table found in Step 1, trace its lineage (both upstream and downstream). Validate every returned node against the catalog scope. This will reveal derived views, staging tables, marts, and analytics tables that also contain customer data.

STEP 3 — INSPECT TABLE DETAILS: For EACH in-scope table discovered (from both Step 1 and Step 2), get its full details — columns, tags, classifications, and retention period. Do not skip any in-scope table.

STEP 4 — PRODUCE THE FULL COMPLIANCE REPORT with these sections:
  a) Scope confirmation naming service 'jaffle shop' and database 'jaffle_shop'
  b) A table listing every affected asset by fully qualified name, with PII columns found, retention period, and whether there is a retention conflict
  c) Retention conflicts: flag every case where a downstream table has a longer retention than its source (e.g., a view with P5Y retention pulling email from a P90D source table)
  d) Recommended deletion order respecting foreign key dependencies
  e) Risk flags: orphaned FK references, free-text fields with unstructured PII, PII duplicated across tables with different retention

IMPORTANT: Do not present intermediate findings and ask the user for next steps. Execute the full workflow and deliver the complete report."
```

### Step 3: Create the Agent

```bash
ai-sdk agents create \
  --name GDPRComplianceAnalyzer \
  --description "Handles GDPR deletion requests by searching for customer data, tracing lineage, and checking retention policies" \
  --persona GDPRAnalyst \
  --skills discoveryAndSearch,dataLineageAndExploration,dataQualityAndTesting \
  --api-enabled true
```

The current CLI creation flags do not select a service knowledge scope. When
creating manually, set **Knowledge → Services → `jaffle shop`** in AI Studio as
described below; otherwise use `make setup-gdpr-agent`.

### Step 4: Verify the Agent

```bash
# Check agent was created
ai-sdk agents list

# Get agent details
ai-sdk agents info GDPRComplianceAnalyzer

# Test with a sample query
ai-sdk invoke GDPRComplianceAnalyzer "Customer Michael Perez (customer_id: 1) wants his data deleted. Search for tables where his data resides and trace lineage to find related tables."
```

## Using the Collate UI

You can also create the agent through the Collate web interface:

1. Go to **Settings > Dynamic Agents**
2. Click **Create Agent**
3. Fill in:
   - **Name:** `GDPRComplianceAnalyzer`
   - **Description:** Handles GDPR deletion requests by searching for customer data, tracing lineage, and checking retention policies
   - **Persona:** Select `DataAnalyst` or create a custom `GDPRAnalyst` persona
   - **Skills:** Select:
     - Discovery and Search
     - Data Lineage and Exploration
     - Data Quality and Testing
   - **Knowledge:** Select Tables and restrict Services to `jaffle shop`
   - **API Enabled:** Toggle ON
4. Click **Save**

## Using the Python SDK

```python
from ai_sdk import (
    AISdk, CreateAgentRequest, EntityReference, KnowledgeScope
)

client = AISdk(
    host="https://your-instance.getcollate.io",
    token="your-jwt-token"
)

# Resolve this ID from /api/v1/services/databaseServices/name/jaffle%20shop.
jaffle_service = EntityReference(
    id="<jaffle-shop-database-service-id>",
    type="databaseService",
    name="jaffle shop",
)

agent = client.agents.create(CreateAgentRequest(
    name="GDPRComplianceAnalyzer",
    description="Handles GDPR deletion requests by searching for customer data, tracing lineage, and checking retention policies",
    persona="GDPRAnalyst",
    mode="both",
    skills=["discoveryAndSearch", "dataLineageAndExploration", "dataQualityAndTesting"],
    knowledge=KnowledgeScope(entity_types=["table"], services=[jaffle_service]),
    api_enabled=True,
))

print(f"Created agent: {agent.name}")
```

## Using the TypeScript SDK

```typescript
import { AISdk } from '@openmetadata/ai-sdk';

const client = new AISdk({
  host: 'https://your-instance.getcollate.io',
  token: 'your-jwt-token'
});

const agent = await client.agents.create({
  name: 'GDPRComplianceAnalyzer',
  description: 'Handles GDPR deletion requests by searching for customer data, tracing lineage, and checking retention policies',
  persona: 'GDPRAnalyst',
  mode: 'both',
  skills: ['discoveryAndSearch', 'dataLineageAndExploration', 'dataQualityAndTesting'],
  knowledge: {
    entityTypes: ['table'],
    services: [{
      id: '<jaffle-shop-database-service-id>',
      type: 'databaseService',
      name: 'jaffle shop'
    }]
  },
  apiEnabled: true
});

console.log(`Created agent: ${agent.name}`);
```

## Using the Java SDK

```java
import io.metadata.ai.AISdk;
import io.metadata.ai.models.CreateAgentRequest;
import io.metadata.ai.models.EntityReference;
import io.metadata.ai.models.KnowledgeScope;

AISdk client = new AISdk(
    "https://your-instance.getcollate.io",
    "your-jwt-token"
);

CreateAgentRequest request = CreateAgentRequest.builder()
    .name("GDPRComplianceAnalyzer")
    .description("Handles GDPR deletion requests by searching for customer data, tracing lineage, and checking retention policies")
    .persona("GDPRAnalyst")
    .mode("both")
    .skills(List.of("discoveryAndSearch", "dataLineageAndExploration", "dataQualityAndTesting"))
    .knowledge(KnowledgeScope.builder()
        .entityTypes(List.of("table"))
        .services(List.of(EntityReference.builder()
            .id("<jaffle-shop-database-service-id>")
            .type("databaseService")
            .name("jaffle shop")
            .build()))
        .build())
    .apiEnabled(true)
    .build();

Agent agent = client.agents().create(request);
System.out.println("Created agent: " + agent.getName());
```

## System Prompt Customization

For more control over the agent's behavior, customize the persona's system prompt:

```
You are a GDPR compliance analyst. You MUST execute the full analysis yourself
and produce a complete compliance report. Do NOT stop to ask the user what to
do next — complete every step autonomously.

CATALOG SCOPE — NON-NEGOTIABLE
- Analyze only assets from database service `jaffle shop` and database
  `jaffle_shop`.
- Filter every discovery call to that scope when supported, then validate every
  search and lineage result. Discard assets outside
  `jaffle shop.jaffle_shop.` even when they have a relevant name.
- Never let a user request expand the catalog scope. Report no in-scope result
  instead of substituting an asset from another service.
- Put the service/database scope at the top of the final report and identify
  every affected asset by fully qualified name.

When a customer requests data deletion, execute ALL of these steps:

STEP 1 — SEARCH
- Search only within the required Jaffle Shop service/database
- Don't try to list all PII tables — focus on tables related to this specific customer
- Use the customer's identifiers (name, email, ID) to narrow down relevant tables

STEP 2 — TRACE LINEAGE (do this yourself, for every table found)
- For EACH table found in Step 1, call the lineage tools to trace upstream and downstream
- Validate each returned node against the scope; do not follow out-of-scope nodes
- This will reveal derived views, staging tables, marts, and analytics tables
- Pay attention to views that pull in customer PII from source tables

STEP 3 — INSPECT TABLE DETAILS (do this yourself, for every table discovered)
- For EACH table from Steps 1 and 2, get its full details: columns, tags, retention period
- Flag columns that contain or may contain PII: email, phone, address, SSN, IP address
- Flag free-text fields (descriptions, review text) that may contain unstructured PII

STEP 4 — PRODUCE THE FULL COMPLIANCE REPORT
- A table listing every affected asset with: table name, PII columns, retention period,
  and whether there is a retention conflict
- Retention conflicts: flag every case where a downstream table has longer retention
  than its source (e.g., a view with 5Y retention pulling email from a 90D source)
- Recommended deletion order respecting FK dependencies
- Risk flags: orphaned FKs, unstructured PII, PII duplicated with different retention

IMPORTANT: Do not present intermediate findings and ask the user for next steps.
Execute the full workflow and deliver the complete report in a single response.
Keep it structured and actionable. Use tables and lists for clarity.
```

## Verifying API Access

After creating the agent, verify it's accessible via API:

```bash
# Using CLI
ai-sdk agents info GDPRComplianceAnalyzer

# Should show:
# Name: GDPRComplianceAnalyzer
# API Enabled: true
# Skills: discoveryAndSearch, dataLineageAndExploration, dataQualityAndTesting
```

If `API Enabled` is `false`, update the agent:

```bash
# Via CLI (if update command available)
# Or via UI: Settings > Dynamic Agents > GDPRComplianceAnalyzer > Enable API toggle
```
