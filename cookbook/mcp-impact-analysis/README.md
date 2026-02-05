# MCP Impact Analysis: Data Change Assessment

Automate impact analysis for schema changes using OpenMetadata's MCP tools. This cookbook shows how to build an AI-powered assistant that helps data engineers understand the downstream impact before modifying tables, columns, or pipelines.

## Business Problem

**Scenario:** Your team needs to deprecate the `ssn_last_four` column from the `customers` table due to compliance requirements. Before making this change, you need to answer:

1. What downstream tables, views, and dashboards depend on this column?
2. Who owns those assets and should be notified?
3. Are there data quality tests that will fail?
4. What's the blast radius of this change?

**Traditional approach:** Manually query lineage graphs, check documentation, send emails. This takes hours and often misses dependencies.

**With MCP tools:** Ask an AI assistant that queries your metadata catalog in real-time and provides a comprehensive impact report in seconds.

## Prerequisites

- [Demo Database](../demo-database/) running with data ingested into OpenMetadata
- Python 3.10+
- OpenAI API key (or use any LangChain-compatible LLM)

## Installation

```bash
pip install metadata-ai[langchain] langchain-openai
```

## Environment Setup

```bash
# OpenMetadata credentials
export METADATA_HOST="https://your-openmetadata.com"
export METADATA_TOKEN="your-jwt-token"

# LLM API key
export OPENAI_API_KEY="your-openai-key"
```

## The Impact Analysis Agent

### impact_analyzer.py

```python
"""
Data Change Impact Analyzer

An AI agent that helps assess the impact of schema changes
before they're made, using OpenMetadata's MCP tools.
"""

from metadata_ai import MetadataAI, MetadataConfig
from metadata_ai.mcp import MCPTool
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate


SYSTEM_PROMPT = """You are a Data Impact Analyst assistant. Your job is to help
data engineers understand the downstream impact of schema changes before they make them.

When analyzing a change, you should:

1. **Find the asset** - Search for the table/column being modified
2. **Trace lineage** - Get downstream dependencies (tables, views, dashboards)
3. **Identify owners** - Find who owns affected assets
4. **Assess risk** - Consider data quality tests, PII implications, SLAs
5. **Summarize impact** - Provide a clear, actionable report

Always structure your response as:

## Impact Summary
Brief overview of the change and its scope.

## Affected Assets
List of downstream tables, views, and dashboards with their owners.

## Risk Assessment
- Data Quality: Tests that may fail
- Compliance: PII/sensitive data implications
- Business: Dashboards or reports affected

## Recommended Actions
1. Notify these stakeholders: [list]
2. Update these assets: [list]
3. Consider these alternatives: [if any]

Use the available tools to gather accurate, real-time metadata.
"""


def create_impact_analyzer():
    """Create an impact analysis agent with MCP tools."""

    # Initialize Metadata client
    config = MetadataConfig.from_env()
    client = MetadataAI.from_config(config)

    # Use read-only MCP tools for safety
    tools = client.mcp.as_langchain_tools(
        include=[
            MCPTool.SEARCH_METADATA,
            MCPTool.GET_ENTITY_DETAILS,
            MCPTool.GET_ENTITY_LINEAGE,
        ]
    )

    # Configure LLM
    llm = ChatOpenAI(
        model="gpt-4",
        temperature=0,  # Deterministic for consistency
    )

    # Build prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    # Create agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=10,  # Allow thorough exploration
        return_intermediate_steps=True,
    )

    return executor, client


def analyze_change(executor, change_description: str) -> dict:
    """Analyze the impact of a proposed change."""
    result = executor.invoke({"input": change_description})
    return {
        "analysis": result["output"],
        "steps": len(result.get("intermediate_steps", [])),
    }


def main():
    """Interactive impact analysis session."""
    print("=" * 60)
    print("Data Change Impact Analyzer")
    print("=" * 60)
    print("\nThis tool helps you understand the impact of schema changes")
    print("before you make them. Describe your planned change and I'll")
    print("analyze the downstream dependencies.\n")
    print("Type 'quit' to exit.\n")

    executor, client = create_impact_analyzer()

    try:
        while True:
            print("-" * 60)
            change = input("\nDescribe your planned change:\n> ").strip()

            if change.lower() in ("quit", "exit", "q"):
                print("\nGoodbye!")
                break

            if not change:
                continue

            print("\nAnalyzing impact...\n")
            result = analyze_change(executor, change)

            print("\n" + "=" * 60)
            print("IMPACT ANALYSIS REPORT")
            print("=" * 60)
            print(result["analysis"])
            print(f"\n[Analysis completed in {result['steps']} steps]")

    finally:
        client.close()


if __name__ == "__main__":
    main()
```

## Example Interactions

### Example 1: Column Deprecation

**Input:**
```
I want to remove the ssn_last_four column from raw_jaffle_shop.customers.
What's the impact?
```

**Expected Response:**

```markdown
## Impact Summary
Removing `ssn_last_four` from `raw_jaffle_shop.customers` affects 3 downstream
assets across 2 schemas. This is a **medium-risk** change due to the sensitive
nature of the data.

## Affected Assets

| Asset | Type | Schema | Owner |
|-------|------|--------|-------|
| stg_jaffle_shop__customers | View | staging | data-engineering@jaffle.shop |
| dim_customers | Table | marts_core | analytics@jaffle.shop |

Note: The column is not propagated beyond staging as it's filtered in the
stg_jaffle_shop__customers model.

## Risk Assessment

**Data Quality:**
- No DQ tests reference this column directly
- The staging model filters it out, so downstream tests unaffected

**Compliance:**
- POSITIVE: Removing SSN data reduces compliance burden
- Ensure data retention policies allow deletion

**Business:**
- No dashboards reference this column
- No active queries in pg_stat_statements use this column

## Recommended Actions

1. **Notify stakeholders:**
   - data-engineering@jaffle.shop (staging model owner)

2. **Update assets:**
   - Remove column reference from `stg_jaffle_shop__customers.sql`
   - Update dbt schema documentation

3. **Migration steps:**
   - Add column to staging model exclusion list (already excluded)
   - Drop column from source table
   - Run full dbt refresh
```

### Example 2: Table Restructure

**Input:**
```
We're planning to split raw_stripe.payments into two tables:
payments_transactions and payments_methods. What will break?
```

**Expected Response:**

```markdown
## Impact Summary
Splitting `raw_stripe.payments` is a **high-risk** change affecting 6 downstream
assets including critical finance marts. This requires coordinated migration.

## Affected Assets

| Asset | Type | Schema | Owner | Risk |
|-------|------|--------|-------|------|
| stg_stripe__payments | View | staging | data-engineering | HIGH |
| int_orders__enriched | View | intermediate | data-engineering | HIGH |
| fct_orders | Table | marts_core | analytics | HIGH |
| fct_daily_revenue | Table | marts_finance | finance-team | CRITICAL |
| fct_monthly_revenue | Table | marts_finance | finance-team | CRITICAL |

## Risk Assessment

**Data Quality:**
- 3 tests on `stg_stripe__payments` will fail during migration
- `payment_status` accepted_values test
- `payment_id` uniqueness test
- `payment_amount` not_null test

**Compliance:**
- `card_last_four` and `ip_address` are PII columns
- Must ensure both new tables have proper access controls

**Business:**
- `fct_daily_revenue` powers the executive dashboard
- `fct_monthly_revenue` feeds the monthly board report
- Finance team has SLA for daily revenue by 6 AM

## Recommended Actions

1. **Notify stakeholders:**
   - finance-team@jaffle.shop (CRITICAL - revenue marts)
   - analytics@jaffle.shop (fct_orders owner)
   - data-engineering@jaffle.shop (staging/intermediate)

2. **Migration strategy:**
   - Create new tables alongside existing
   - Update staging models to union both sources
   - Run parallel validation for 1 week
   - Cut over after validation passes

3. **Rollback plan:**
   - Keep original payments table for 30 days
   - Staging model should support both schemas
```

### Example 3: Adding a New Column

**Input:**
```
I want to add a loyalty_tier column to dim_customers.
What do I need to update?
```

**Expected Response:**

```markdown
## Impact Summary
Adding `loyalty_tier` to `dim_customers` is a **low-risk** additive change.
No existing assets will break, but there are opportunities to propagate
this new attribute downstream.

## Affected Assets
No assets are negatively affected (additive change).

## Propagation Opportunities

Assets that could benefit from `loyalty_tier`:

| Asset | Type | Recommendation |
|-------|------|----------------|
| fct_orders | Table | Add loyalty_tier for order-level segmentation |
| fct_daily_revenue | Table | Add loyalty_tier breakdown |
| Customer Segments (Metabase) | Dashboard | Add loyalty_tier filter |

## Risk Assessment

**Data Quality:**
- Add accepted_values test for loyalty_tier enum
- Add not_null test if required field

**Compliance:**
- Not PII - no special handling needed

**Business:**
- Marketing team may want access for campaign targeting
- Consider adding to customer export APIs

## Recommended Actions

1. **Implementation:**
   - Add column to `int_orders__enriched` calculation
   - Update `dim_customers.sql` with segmentation logic
   - Add schema documentation in `_schema.yml`

2. **Testing:**
   - Add accepted_values: ['Bronze', 'Silver', 'Gold', 'Platinum']
   - Add not_null test

3. **Communication:**
   - Announce new attribute in #data-updates Slack
   - Update data dictionary documentation
```

## Tool Response Examples

Understanding what each MCP tool returns helps you interpret the agent's analysis.

### search_metadata Response

```json
{
  "hits": [
    {
      "id": "d4e5f6...",
      "name": "customers",
      "fullyQualifiedName": "jaffle-shop-postgres.jaffle_shop.raw_jaffle_shop.customers",
      "entityType": "table",
      "description": "Raw customer data from the Jaffle Shop application",
      "owner": {
        "name": "data-engineering",
        "type": "team"
      },
      "tags": ["PII", "Tier1"]
    }
  ],
  "total": 1
}
```

### get_entity_details Response

```json
{
  "id": "d4e5f6...",
  "name": "customers",
  "fullyQualifiedName": "jaffle-shop-postgres.jaffle_shop.raw_jaffle_shop.customers",
  "columns": [
    {
      "name": "id",
      "dataType": "INT",
      "constraint": "PRIMARY_KEY"
    },
    {
      "name": "email",
      "dataType": "VARCHAR",
      "tags": [{"tagFQN": "PII.Email"}],
      "description": "Customer email address - PII"
    },
    {
      "name": "ssn_last_four",
      "dataType": "VARCHAR",
      "tags": [{"tagFQN": "PII.SSN"}],
      "description": "Last 4 digits of SSN - Sensitive PII"
    }
  ],
  "owner": {
    "name": "data-engineering",
    "type": "team"
  },
  "dataQualityTests": [
    {"name": "email_not_null", "status": "Success"},
    {"name": "id_unique", "status": "Success"}
  ]
}
```

### get_entity_lineage Response

```json
{
  "entity": {
    "id": "d4e5f6...",
    "name": "customers",
    "type": "table"
  },
  "upstreamEdges": [],
  "downstreamEdges": [
    {
      "fromEntity": "raw_jaffle_shop.customers",
      "toEntity": "staging.stg_jaffle_shop__customers",
      "lineageType": "VIEW"
    },
    {
      "fromEntity": "staging.stg_jaffle_shop__customers",
      "toEntity": "marts_core.dim_customers",
      "lineageType": "TRANSFORM"
    }
  ],
  "nodes": [
    {
      "id": "...",
      "name": "stg_jaffle_shop__customers",
      "type": "table",
      "owner": {"name": "data-engineering"}
    },
    {
      "id": "...",
      "name": "dim_customers",
      "type": "table",
      "owner": {"name": "analytics"}
    }
  ]
}
```

## Advanced: Batch Impact Analysis

For CI/CD integration, analyze multiple changes in a PR:

### batch_analyzer.py

```python
"""Analyze impact of all changes in a dbt PR."""

import sys
from pathlib import Path
from impact_analyzer import create_impact_analyzer, analyze_change


def get_changed_models(diff_output: str) -> list[str]:
    """Extract changed dbt model names from git diff."""
    models = []
    for line in diff_output.split("\n"):
        if line.startswith("+++ b/") and line.endswith(".sql"):
            # Extract model name from path
            path = Path(line.replace("+++ b/", ""))
            if "models" in path.parts:
                models.append(path.stem)
    return models


def main():
    if len(sys.argv) < 2:
        print("Usage: python batch_analyzer.py <git-diff-output>")
        sys.exit(1)

    diff_file = sys.argv[1]
    with open(diff_file) as f:
        diff_output = f.read()

    changed_models = get_changed_models(diff_output)

    if not changed_models:
        print("No dbt model changes detected.")
        sys.exit(0)

    print(f"Analyzing impact of {len(changed_models)} changed models...")

    executor, client = create_impact_analyzer()

    try:
        for model in changed_models:
            print(f"\n{'='*60}")
            print(f"Analyzing: {model}")
            print("="*60)

            result = analyze_change(
                executor,
                f"The dbt model '{model}' has been modified. "
                f"What downstream assets are affected?"
            )
            print(result["analysis"])

    finally:
        client.close()


if __name__ == "__main__":
    main()
```

### GitHub Actions Integration

```yaml
# .github/workflows/impact-analysis.yml
name: Data Impact Analysis

on:
  pull_request:
    paths:
      - 'dbt/models/**'

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install metadata-ai[langchain] langchain-openai

      - name: Get changed files
        run: |
          git diff origin/main...HEAD > changes.diff

      - name: Run impact analysis
        env:
          METADATA_HOST: ${{ secrets.METADATA_HOST }}
          METADATA_TOKEN: ${{ secrets.METADATA_TOKEN }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: python batch_analyzer.py changes.diff > impact_report.md

      - name: Post comment
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('impact_report.md', 'utf8');
            github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: `## Data Impact Analysis\n\n${report}`
            });
```

## Configuration Options

### Using Different LLMs

```python
# Claude (via Amazon Bedrock)
from langchain_aws import ChatBedrock

llm = ChatBedrock(
    model_id="anthropic.claude-3-sonnet-20240229-v1:0",
    region_name="us-east-1"
)

# Local LLM (via Ollama)
from langchain_ollama import ChatOllama

llm = ChatOllama(model="llama3.1:70b")

# Azure OpenAI
from langchain_openai import AzureChatOpenAI

llm = AzureChatOpenAI(
    deployment_name="gpt-4",
    api_version="2024-02-15-preview"
)
```

### Customizing the Prompt

Adapt the system prompt for your organization:

```python
CUSTOM_PROMPT = """You are a Data Impact Analyst at {company_name}.

Our data platform uses:
- dbt for transformations
- Snowflake as the warehouse
- Looker for dashboards
- PagerDuty for alerting

When analyzing changes, pay special attention to:
- Tier 1 tables (SLA: 99.9% uptime)
- PII columns (GDPR/CCPA compliance)
- Finance marts (SOX controls)

{base_instructions}
"""
```

## Next Steps

- [Demo Database Setup](../demo-database/) - Get the sample data running
- [DQ Failure Notifications](../dq-failure-slack-notifications/) - Alert on quality issues
- [dbt PR Review](../dbt-pr-review/) - Automated PR reviews
