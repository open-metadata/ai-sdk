# Agent Configuration: GDPRComplianceAnalyzer

This guide shows how to create the `GDPRComplianceAnalyzer` agent required for the GDPR DSAR compliance workflow.

## Using the CLI (Recommended)

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

### Step 1: Explore Available Abilities

```bash
# List all abilities
ai-sdk abilities list

# Get details on specific abilities
ai-sdk abilities get discoveryAndSearch
ai-sdk abilities get dataLineageAndExploration
ai-sdk abilities get dataQualityAndTesting
```

The agent needs these abilities:
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
  --description "GDPR compliance and PII analysis specialist" \
  --prompt "You are a GDPR compliance analyst. You MUST execute the full analysis yourself and produce a complete compliance report. Do NOT stop to ask the user what to do next — complete every step autonomously.

When a customer requests data deletion, execute ALL of these steps:

STEP 1 — SEARCH: Search for tables where the customer's data likely resides (e.g., 'customers', 'payments', 'orders'). Use the search tools to find them.

STEP 2 — TRACE LINEAGE: For EACH table found in Step 1, trace its lineage (both upstream and downstream). Do this yourself — call the lineage tools for every table. This will reveal derived views, staging tables, marts, and analytics tables that also contain customer data.

STEP 3 — INSPECT TABLE DETAILS: For EACH table discovered (from both Step 1 and Step 2), get its full details — columns, tags, classifications, and retention period. Do not skip any table.

STEP 4 — PRODUCE THE FULL COMPLIANCE REPORT with these sections:
  a) A table listing every affected asset with: table name, PII columns found, retention period, and whether there is a retention conflict
  b) Retention conflicts: flag every case where a downstream table has a longer retention than its source (e.g., a view with P5Y retention pulling email from a P90D source table)
  c) Recommended deletion order respecting foreign key dependencies
  d) Risk flags: orphaned FK references, free-text fields with unstructured PII, PII duplicated across tables with different retention

IMPORTANT: Do not present intermediate findings and ask the user for next steps. Execute the full workflow and deliver the complete report."
```

### Step 3: Create the Agent

```bash
ai-sdk agents create \
  --name GDPRComplianceAnalyzer \
  --description "Handles GDPR deletion requests by searching for customer data, tracing lineage, and checking retention policies" \
  --persona GDPRAnalyst \
  --abilities discoveryAndSearch,dataLineageAndExploration,dataQualityAndTesting \
  --api-enabled true
```

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
   - **Abilities:** Select:
     - Discovery and Search
     - Data Lineage and Exploration
     - Data Quality and Testing
   - **API Enabled:** Toggle ON
4. Click **Save**

## Using the Python SDK

```python
from ai_sdk import AISdk

client = AISdk(
    host="https://your-instance.getcollate.io",
    token="your-jwt-token"
)

# Create the agent
agent = client.create_agent(
    name="GDPRComplianceAnalyzer",
    description="Handles GDPR deletion requests by searching for customer data, tracing lineage, and checking retention policies",
    persona="GDPRAnalyst",
    abilities=["discoveryAndSearch", "dataLineageAndExploration", "dataQualityAndTesting"],
    api_enabled=True
)

print(f"Created agent: {agent.name}")
```

## Using the TypeScript SDK

```typescript
import { AISdk } from '@openmetadata/ai-sdk';

const client = new AISdk({
  host: 'https://your-instance.getcollate.io',
  token: 'your-jwt-token'
});

const agent = await client.createAgent({
  name: 'GDPRComplianceAnalyzer',
  description: 'Handles GDPR deletion requests by searching for customer data, tracing lineage, and checking retention policies',
  persona: 'GDPRAnalyst',
  abilities: ['discoveryAndSearch', 'dataLineageAndExploration', 'dataQualityAndTesting'],
  apiEnabled: true
});

console.log(`Created agent: ${agent.name}`);
```

## Using the Java SDK

```java
import io.metadata.ai.AISdk;
import io.metadata.ai.models.CreateAgentRequest;

AISdk client = new AISdk(
    "https://your-instance.getcollate.io",
    "your-jwt-token"
);

CreateAgentRequest request = CreateAgentRequest.builder()
    .name("GDPRComplianceAnalyzer")
    .description("Handles GDPR deletion requests by searching for customer data, tracing lineage, and checking retention policies")
    .persona("GDPRAnalyst")
    .abilities(List.of("discoveryAndSearch", "dataLineageAndExploration", "dataQualityAndTesting"))
    .apiEnabled(true)
    .build();

Agent agent = client.createAgent(request);
System.out.println("Created agent: " + agent.getName());
```

## System Prompt Customization

For more control over the agent's behavior, customize the persona's system prompt:

```
You are a GDPR compliance analyst. You MUST execute the full analysis yourself
and produce a complete compliance report. Do NOT stop to ask the user what to
do next — complete every step autonomously.

When a customer requests data deletion, execute ALL of these steps:

STEP 1 — SEARCH
- Search for tables where the customer's data likely resides
- Don't try to list all PII tables — focus on tables related to this specific customer
- Use the customer's identifiers (name, email, ID) to narrow down relevant tables

STEP 2 — TRACE LINEAGE (do this yourself, for every table found)
- For EACH table found in Step 1, call the lineage tools to trace upstream and downstream
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
# Abilities: discoveryAndSearch, dataLineageAndExploration, dataQualityAndTesting
```

If `API Enabled` is `false`, update the agent:

```bash
# Via CLI (if update command available)
# Or via UI: Settings > Dynamic Agents > GDPRComplianceAnalyzer > Enable API toggle
```
