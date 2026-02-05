# DQ Failure Slack Notifications

Automatically analyze Data Quality test failures, assess downstream impact via lineage, and send actionable summaries to Slack.

## Overview

When a Data Quality test fails in Collate, this workflow:
1. Receives the failure event via webhook
2. Extracts test details (table, failure message, metrics)
3. Uses a Metadata AI agent to analyze lineage and assess impact
4. Sends a structured summary with AI-generated recommendations to Slack

## Prerequisites

- Collate/OpenMetadata instance with DQ tests configured
- n8n instance (Cloud or self-hosted)
- Slack workspace with incoming webhooks enabled
- Metadata AI CLI or SDK (for agent setup)

## Architecture

```
┌─────────┐     webhook      ┌─────────┐     invoke      ┌──────────────────┐
│ Collate │ ───────────────► │  n8n    │ ──────────────► │ DataQuality      │
│ DQ Test │                  │ Workflow│                 │ Analyzer Agent   │
└─────────┘                  └────┬────┘                 └──────────────────┘
                                  │                              │
                                  │ post                         │ analysis
                                  ▼                              │
                             ┌─────────┐◄────────────────────────┘
                             │  Slack  │
                             └─────────┘
```

## Step 1: Create the Agent

First, create a Dynamic Agent with the abilities needed for DQ analysis.

See [agent-config.md](./agent-config.md) for detailed setup instructions using the CLI, UI, or SDKs.

**Quick setup with CLI:**

```bash
# Create the Persona
metadata-ai personas create \
  --name DQAnalyst \
  --description "Data Quality analysis specialist" \
  --prompt "You are a Data Quality analyst. When analyzing test failures, you:
1. Identify the affected table and understand its purpose
2. Explore downstream lineage to assess impact on dependent assets
3. Check upstream lineage for potential root causes
4. Review test definition and historical results
5. Provide concise summaries with actionable recommendations"

# Create the Agent
metadata-ai agents create \
  --name DataQualityAnalyzer \
  --description "Analyzes DQ test failures, explores lineage impact, and suggests remediation" \
  --persona DQAnalyst \
  --abilities dataLineageAndExploration,dataQualityAndTesting,discoveryAndSearch \
  --api-enabled true
```

## Step 2: Configure Collate Webhook

Set up Collate to send DQ failure events to your n8n webhook.

1. Go to **Settings → Notifications → Destinations**
2. Click **Add Destination**
3. Select **Webhook**
4. Configure:
   - **Name:** `n8n-dq-alerts`
   - **Endpoint URL:** Your n8n webhook URL (from Step 3)
   - **Secret:** (optional) Shared secret for validation

5. Go to **Settings → Notifications → Alerts**
6. Click **Add Alert**
7. Configure:
   - **Name:** `DQ Test Failures`
   - **Source:** Test Case
   - **Filter:** Status equals `Failed`
   - **Destination:** Select `n8n-dq-alerts`

## Step 3: Build the n8n Workflow

### Option A: Import the Workflow

1. In n8n, go to **Workflows → Import**
2. Upload [`workflow.json`](./workflow.json)
3. Configure credentials (Metadata API, Slack)
4. Activate the workflow

### Option B: Build Manually

#### Node 1: Webhook Trigger

- **Type:** Webhook
- **HTTP Method:** POST
- **Path:** `dq-failure`
- **Authentication:** (optional) Header Auth with secret

#### Node 2: Extract Fields (Code)

```javascript
// Extract relevant fields from Collate ChangeEvent
// n8n wraps the webhook payload in a body property
const event = $input.first().json.body;

const fieldUpdate = event.changeDescription?.fieldsUpdated?.find(
  f => f.name === 'testCaseResult'
);

if (!fieldUpdate) {
  return []; // Not a test result update
}

const result = fieldUpdate.newValue;

// Only process failures
if (result.testCaseStatus !== 'Failed') {
  return [];
}

// Parse table FQN from test case FQN
// Format: service.database.schema.table.test_name
const fqnParts = event.entityFullyQualifiedName.split('.');
const tableFqn = fqnParts.slice(0, -1).join('.');
const testName = fqnParts[fqnParts.length - 1];

return [{
  json: {
    tableFqn,
    testName,
    testCaseFqn: result.testCaseFQN,
    status: result.testCaseStatus,
    failureMessage: result.result,
    failedRows: result.failedRows,
    failedRowsPercentage: result.failedRowsPercentage,
    sampleData: result.sampleData,
    timestamp: result.timestamp,
    incidentId: result.incidentId
  }
}];
```

#### Node 3: Metadata Agent

- **Type:** Metadata Agent (from `n8n-nodes-metadata`)
- **Credentials:** Configure with your Collate host and JWT token
- **Agent Name:** `DataQualityAnalyzer`
- **Message:**

```
Data Quality test "${tableFqn}.${testName}" has FAILED.

Failure details:
- Table: ${tableFqn}
- Test: ${testName}
- Result: ${failureMessage}

Please:
1. Identify the affected table and its purpose
2. Explore downstream lineage to find impacted assets
3. Check upstream lineage for potential root causes
4. Summarize the impact and recommend next steps
```

(Use n8n expressions: `{{ $json.tableFqn }}`, etc.)

#### Node 4: Slack

- **Type:** Slack
- **Operation:** Send Message
- **Channel:** Your alerts channel
- **Message:**

```
:rotating_light: *Data Quality Alert*

*Table:* `{{ $('Extract Fields').item.json.tableFqn }}`
*Test:* {{ $('Extract Fields').item.json.testName }}
*Status:* Failed

---

*Analysis:*
{{ $json.response }}

---

:bar_chart: <https://your-collate-instance/test/{{ $('Extract Fields').item.json.testCaseFqn }}|View Test Details>
```

## Step 4: Configure Slack

1. Go to [Slack API](https://api.slack.com/apps) and create an app
2. Add **OAuth & Permissions** → Add scopes: `chat:write`, `channels:read`
3. Install the app to your workspace
4. Copy the **Bot User OAuth Token** (`xoxb-...`)
5. **Invite the bot to your channel**: In Slack, go to the channel and type `/invite @YourBotName`
6. In n8n, add Slack credentials with the bot token

### Test Slack Integration

Before running the full workflow, verify the bot can post to your channel:

```bash
# Test posting a message
curl -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer xoxb-YOUR-BOT-TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "your-channel-name",
    "text": "Test message from n8n integration"
  }'
```

Expected response: `{"ok":true,...}`

**Common errors:**
| Error | Solution |
|-------|----------|
| `channel_not_found` | Invite the bot to the channel: `/invite @YourBotName` |
| `not_in_channel` | Bot needs to be added to the channel |
| `invalid_auth` | Check bot token is correct |

To list channels the bot can access:
```bash
curl -s "https://slack.com/api/conversations.list?types=public_channel,private_channel" \
  -H "Authorization: Bearer xoxb-YOUR-BOT-TOKEN" | jq '.channels[] | {name, id}'
```

## Step 5: Test the Integration

1. **Activate** the n8n workflow
2. In Collate, trigger a DQ test failure:
   - Run a test you know will fail, OR
   - Manually update a test result via API
3. Verify the Slack message arrives with analysis

### Sample Slack Output

```
:rotating_light: Data Quality Alert

Table: warehouse.analytics.customer_orders
Test: columnValuesToBeBetween
Status: Failed

---

Analysis:
The test "columnValuesToBeBetween" failed on the customer_orders table
because 100 rows (10%) have values outside the expected range of 0-100.

**Downstream Impact:**
- Dashboard: "Daily Revenue Report" uses this table
- Table: "customer_summary" aggregates from this table
- 3 downstream consumers may show incorrect data

**Likely Root Cause:**
The upstream ETL job "orders_ingestion" ran at 14:30 UTC. Check for
data type issues or source system changes.

**Recommended Actions:**
1. Check the orders_ingestion job logs for errors
2. Validate source data in the orders_raw table
3. Consider adding a data validation step before transformation

---

:bar_chart: View Test Details
```

## Customization

### Filter by Severity

Add a filter node after "Extract Fields" to only alert on high-impact failures:

```javascript
// Only alert if more than 5% of rows failed
if ($json.failedRowsPercentage < 5) {
  return [];
}
return [$input.item];
```

### Multiple Channels

Route alerts to different Slack channels based on the table's domain or owner by adding a Switch node.

### Include Sample Data

Add failed row samples to the Slack message:

```javascript
const samples = JSON.parse($json.sampleData || '[]');
const formatted = samples.slice(0, 3)
  .map(row => '`' + JSON.stringify(row) + '`')
  .join('\n');
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Webhook not receiving events | Check Collate notification config, verify URL is accessible |
| Agent returns error | Verify agent is API-enabled, check JWT token permissions |
| Slack message not posting | Verify Slack credentials, check channel permissions |
| Empty analysis | Ensure agent has required abilities assigned |

## Related Resources

- [Metadata AI Node for n8n](../../n8n-nodes-metadata/)
- [TypeScript SDK Documentation](../../typescript/)
- [Collate Notifications Documentation](https://docs.getcollate.io)
