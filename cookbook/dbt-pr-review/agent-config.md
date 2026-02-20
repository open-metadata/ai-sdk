# Agent Configuration: DBTReviewer

This guide shows how to create the `DBTReviewer` agent required for the dbt PR review workflow.

## Using the CLI (Recommended)

The `ai-sdk` CLI provides the fastest way to set up the agent.

### Prerequisites

```bash
# Install the CLI
cargo install ai-sdk

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
- **discoveryAndSearch** - Find tables by model name, search metadata
- **dataLineageAndExploration** - Traverse downstream dependencies, assess impact
- **dataQualityAndTesting** - Review existing DQ tests, identify risks

### Step 2: Create the Persona

```bash
ai-sdk personas create \
  --name DBTReviewerPersona \
  --description "dbt model code review specialist" \
  --prompt "You are a senior data engineer reviewing dbt model changes. You:
1. Search OpenMetadata to find the table corresponding to each changed model
2. Analyze downstream lineage to identify dashboards, tables, and pipelines that depend on it
3. Review data quality tests and warn if changes could break them
4. Identify breaking changes like renamed columns, removed fields, or modified join logic
5. Provide clear, actionable feedback focused on production impact

Be concise. Focus on what matters: will this change break something downstream?"
```

### Step 3: Create the Agent

```bash
ai-sdk agents create \
  --name DBTReviewer \
  --description "Reviews dbt model PRs for downstream impact and DQ risks" \
  --persona DBTReviewerPersona \
  --abilities discoveryAndSearch,dataLineageAndExploration,dataQualityAndTesting \
  --api-enabled true
```

### Step 4: Verify the Agent

```bash
# Check agent was created
ai-sdk agents list

# Get agent details
ai-sdk agents info DBTReviewer

# Test with a sample query
ai-sdk invoke DBTReviewer "What tables depend on the orders model?"
```

## Using the Collate UI

1. Go to **Govern → Agents → Dynamic Agents**
2. Click **Create Agent**
3. Fill in:
   - **Name:** `DBTReviewer`
   - **Description:** Reviews dbt model PRs for downstream impact and DQ risks
   - **Persona:** Create new with the prompt above
   - **Abilities:** Select:
     - Discovery and Search
     - Data Lineage and Exploration
     - Data Quality and Testing
   - **API Enabled:** Toggle ON
4. Click **Save**

## Using the Python SDK

```python
from ai_sdk import AiSdk

client = AiSdk(
    host="https://your-instance.getcollate.io",
    token="your-jwt-token"
)

# Create the agent
agent = client.create_agent(
    name="DBTReviewer",
    description="Reviews dbt model PRs for downstream impact and DQ risks",
    persona="DBTReviewerPersona",
    abilities=["discoveryAndSearch", "dataLineageAndExploration", "dataQualityAndTesting"],
    api_enabled=True
)

print(f"Created agent: {agent.name}")
```

## Using the TypeScript SDK

```typescript
import { AiSdk } from '@openmetadata/ai-sdk';

const client = new AiSdk({
  host: 'https://your-instance.getcollate.io',
  token: 'your-jwt-token'
});

const agent = await client.createAgent({
  name: 'DBTReviewer',
  description: 'Reviews dbt model PRs for downstream impact and DQ risks',
  persona: 'DBTReviewerPersona',
  abilities: ['discoveryAndSearch', 'dataLineageAndExploration', 'dataQualityAndTesting'],
  apiEnabled: true
});

console.log(`Created agent: ${agent.name}`);
```

## Verifying API Access

```bash
ai-sdk agents info DBTReviewer

# Should show:
# Name: DBTReviewer
# API Enabled: true
# Abilities: discoveryAndSearch, dataLineageAndExploration, dataQualityAndTesting
```
