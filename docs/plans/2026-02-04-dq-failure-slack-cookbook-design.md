# Design: DQ Failure Slack Notifications Cookbook

**Date:** 2026-02-04
**Status:** Approved

## Overview

Create a cookbook entry documenting an end-to-end workflow: when Data Quality tests fail in Collate, automatically analyze the failure, assess downstream impact via lineage, and send a summary to Slack.

## Cookbook Structure

```
cookbook/
├── README.md                           # Index of all use cases
└── dq-failure-slack-notifications/
    ├── README.md                       # Step-by-step tutorial
    ├── workflow.json                   # Importable n8n workflow
    └── agent-config.md                 # Agent setup instructions
```

## n8n Workflow Architecture

```
[Webhook] → [Extract Fields] → [Metadata Agent] → [Slack]
```

### Nodes

**1. Webhook Trigger**
- Listens for POST requests from Collate
- Receives ChangeEvent payload when DQ tests fail

**2. Extract Fields (Code node)**
- Parses the ChangeEvent structure
- Extracts: table FQN, test name, failure message, failed rows %, sample data
- Filters: only proceeds if `testCaseStatus === "Failed"`

**3. Metadata Agent**
- Agent name: `DataQualityAnalyzer` (user-created)
- Message template combining extracted fields with analysis prompt
- Example: "Test {testName} failed on {tableFQN}: {result}. Explore the lineage, assess downstream impact, and suggest remediation steps."

**4. Slack**
- Posts to configured channel
- Header: Table name, test name, failure metrics
- Body: Agent's analysis and recommendations

## Webhook Payload Structure

Collate sends a ChangeEvent:

```json
{
  "id": "UUID",
  "eventType": "entityUpdated",
  "entityType": "testCase",
  "entityFullyQualifiedName": "database.schema.table.test_case_name",
  "changeDescription": {
    "fieldsUpdated": [
      {
        "name": "testCaseResult",
        "newValue": {
          "testCaseFQN": "database.schema.table.test_case_name",
          "testCaseStatus": "Failed",
          "result": "Value 150 is not between 0 and 100",
          "failedRows": 100,
          "failedRowsPercentage": 10.0,
          "sampleData": "[{\"col1\": \"val1\"}]"
        }
      }
    ]
  }
}
```

Key extraction paths:
- `changeDescription.fieldsUpdated[0].newValue.testCaseStatus` - check equals "Failed"
- `changeDescription.fieldsUpdated[0].newValue.result` - human-readable failure
- `changeDescription.fieldsUpdated[0].newValue.failedRows` / `failedRowsPercentage`

## Agent Configuration

### Agent: DataQualityAnalyzer

**Abilities:**
- Lineage and exploration tools
- Data quality and testing tools
- Discovery and search tools

**System Prompt:**
```
You are a Data Quality analyst. When given a test failure:
1. Identify the affected table and understand its purpose
2. Explore downstream lineage to assess impact on dependent tables/dashboards
3. Check upstream lineage for potential root causes
4. Review test definition and historical results
5. Provide a concise summary with:
   - What failed and why
   - Downstream assets at risk
   - Likely root cause
   - Recommended next steps
```

**Setup in Collate:**
- Create via Settings → Dynamic Agents
- Enable API access for n8n invocation
- Assign abilities listed above

## Slack Message Format

```
🚨 Data Quality Alert

*Table:* `database.schema.table_name`
*Test:* columnValuesToBeBetween
*Status:* Failed
*Failed Rows:* 100 (10.0%)

---

*Analysis:*
{Agent's narrative response - explains what failed,
downstream impact, and recommended actions}

---

📊 <link to test in Collate|View Test Details>
```

## Tutorial Outline

### README.md sections:

1. **Overview** - What the workflow does, prerequisites
2. **Create the Agent** - Step-by-step in Collate UI, abilities, API access
3. **Configure Collate Webhook** - Settings → Notifications → Add Destination
4. **Build the n8n Workflow** - Import JSON or step-by-step node setup
5. **Configure Slack** - Create app/webhook, set channel
6. **Test the Integration** - Trigger test failure, verify notification

## Deliverables

- [ ] `cookbook/README.md` - Index page
- [ ] `cookbook/dq-failure-slack-notifications/README.md` - Tutorial
- [ ] `cookbook/dq-failure-slack-notifications/workflow.json` - Importable n8n workflow
- [ ] `cookbook/dq-failure-slack-notifications/agent-config.md` - Agent setup guide
