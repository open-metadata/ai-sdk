# Agent Configuration: DataQualityAnalyzer

This guide shows how to create the `DataQualityAnalyzer` agent required for the DQ failure workflow.

## Using the CLI (Recommended)

The `ai-sdk` CLI provides the fastest way to set up the agent.

### Prerequisites

```bash
# Install the CLI
cargo install ai-sdk

# Or build from source
cd cli && cargo build --release

# Configure environment
export METADATA_HOST=https://your-instance.getcollate.io
export METADATA_TOKEN=your-jwt-token
```

### Step 1: Explore Available Abilities

```bash
# List all abilities
ai-sdk abilities list

# Get details on specific abilities
ai-sdk abilities get dataLineageAndExploration
ai-sdk abilities get dataQualityAndTesting
```

The agent needs these abilities:
- **dataLineageAndExploration** - Traverse upstream/downstream dependencies, get entity details
- **dataQualityAndTesting** - DQ assessment, test case generation, root cause analysis
- **discoveryAndSearch** - Find assets, search metadata, list entities

### Step 2: Check Available Personas

```bash
# List personas
ai-sdk personas list

# Get persona details
ai-sdk personas get DataAnalyst
```

If you need a custom persona, create one:

```bash
ai-sdk personas create \
  --name DQAnalyst \
  --description "Data Quality analysis specialist" \
  --prompt "You are a Data Quality analyst. When analyzing test failures, you:
1. Identify the affected table and understand its purpose
2. Explore downstream lineage to assess impact on dependent assets
3. Check upstream lineage for potential root causes
4. Review test definition and historical results
5. Provide concise summaries with actionable recommendations"
```

### Step 3: Create the Agent

```bash
ai-sdk agents create \
  --name DataQualityAnalyzer \
  --description "Analyzes DQ test failures, explores lineage impact, and suggests remediation steps" \
  --persona DQAnalyst \
  --abilities dataLineageAndExploration,dataQualityAndTesting,discoveryAndSearch \
  --api-enabled true
```

### Step 4: Verify the Agent

```bash
# Check agent was created
ai-sdk agents list

# Get agent details
ai-sdk agents info DataQualityAnalyzer

# Test with a sample query
ai-sdk invoke DataQualityAnalyzer "What tables depend on warehouse.analytics.orders?"
```

## Using the Collate UI

You can also create the agent through the Collate web interface:

1. Go to **Settings → Dynamic Agents**
2. Click **Create Agent**
3. Fill in:
   - **Name:** `DataQualityAnalyzer`
   - **Description:** Analyzes DQ test failures, explores lineage impact, and suggests remediation steps
   - **Persona:** Select `DataAnalyst` or create a custom one
   - **Abilities:** Select:
     - Data Lineage and Exploration
     - Data Quality and Testing
     - Discovery and Search
   - **API Enabled:** Toggle ON
4. Click **Save**

## Using the Python SDK

```python
from ai_sdk import MetadataAI

client = MetadataAI(
    host="https://your-instance.getcollate.io",
    token="your-jwt-token"
)

# Create the agent
agent = client.create_agent(
    name="DataQualityAnalyzer",
    description="Analyzes DQ test failures, explores lineage impact, and suggests remediation steps",
    persona="DataAnalyst",
    abilities=["dataLineageAndExploration", "dataQualityAndTesting", "discoveryAndSearch"],
    api_enabled=True
)

print(f"Created agent: {agent.name}")
```

## Using the TypeScript SDK

```typescript
import { MetadataAI } from '@openmetadata/ai-sdk';

const client = new MetadataAI({
  host: 'https://your-instance.getcollate.io',
  token: 'your-jwt-token'
});

const agent = await client.createAgent({
  name: 'DataQualityAnalyzer',
  description: 'Analyzes DQ test failures, explores lineage impact, and suggests remediation steps',
  persona: 'DataAnalyst',
  abilities: ['dataLineageAndExploration', 'dataQualityAndTesting', 'discoveryAndSearch'],
  apiEnabled: true
});

console.log(`Created agent: ${agent.name}`);
```

## Using the Java SDK

```java
import io.metadata.ai.MetadataAI;
import io.metadata.ai.models.CreateAgentRequest;

MetadataAI client = new MetadataAI(
    "https://your-instance.getcollate.io",
    "your-jwt-token"
);

CreateAgentRequest request = CreateAgentRequest.builder()
    .name("DataQualityAnalyzer")
    .description("Analyzes DQ test failures, explores lineage impact, and suggests remediation steps")
    .persona("DataAnalyst")
    .abilities(List.of("dataLineageAndExploration", "dataQualityAndTesting", "discoveryAndSearch"))
    .apiEnabled(true)
    .build();

Agent agent = client.createAgent(request);
System.out.println("Created agent: " + agent.getName());
```

## System Prompt Customization

For more control over the agent's behavior, customize the persona's system prompt:

```
You are a Data Quality analyst specializing in root cause analysis.

When given a test failure:

1. **Identify the Issue**
   - What table is affected?
   - What test failed and why?
   - How severe is the failure (% of rows affected)?

2. **Assess Impact**
   - What downstream tables/dashboards consume this data?
   - Who are the data owners that should be notified?
   - What business processes might be affected?

3. **Investigate Root Cause**
   - What upstream sources feed this table?
   - When was the data last updated?
   - Are there related test failures?

4. **Recommend Actions**
   - Immediate steps to mitigate impact
   - Investigation steps for root cause
   - Preventive measures for the future

Keep responses concise and actionable. Prioritize impact over technical details.
```

## Verifying API Access

After creating the agent, verify it's accessible via API:

```bash
# Using CLI
ai-sdk agents info DataQualityAnalyzer

# Should show:
# Name: DataQualityAnalyzer
# API Enabled: true
# Abilities: dataLineageAndExploration, dataQualityAndTesting, discoveryAndSearch
```

If `API Enabled` is `false`, update the agent:

```bash
# Via CLI (if update command available)
# Or via UI: Settings → Dynamic Agents → DataQualityAnalyzer → Enable API toggle
```
