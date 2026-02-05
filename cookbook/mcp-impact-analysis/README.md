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
pip install metadata-ai[langchain]
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

The interactive agent is implemented in [`impact_analyzer.py`](./impact_analyzer.py). Here's how it works:

1. **MCP tool selection** - It initializes a `MetadataAI` client and loads only the read-only MCP tools (`search_metadata`, `get_entity_details`, `get_entity_lineage`). Mutation tools are excluded so the agent can never modify your catalog during analysis.

2. **System prompt** - A structured prompt instructs the LLM to follow a repeatable workflow: find the asset, trace lineage, identify owners, assess risk, and summarize the impact. The prompt also enforces a consistent output format with sections for affected assets, risk assessment, and recommended actions.

3. **LangChain agent loop** - The tools and prompt are wired into a LangChain `AgentExecutor` with `max_iterations=10`, giving the LLM enough room to chain multiple tool calls (e.g., search for a table, get its details, then traverse its lineage).

4. **Interactive REPL** - The `main()` function provides a terminal loop where you describe a planned change in plain English and receive a structured impact report.

Run it with:

```bash
python impact_analyzer.py
```

## Example Interactions

### Example 1: Column Deprecation

**Input:**
```
I want to remove the ssn_last_four column from raw_jaffle_shop.customers.
What's the impact?
```

**Expected Response:**

The agent will call `search_metadata` to locate the table, then `get_entity_lineage` to walk the downstream graph, and finally `get_entity_details` on each affected node. A typical report looks like:

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

Because `raw_stripe.payments` sits at the root of the finance lineage chain, the agent will discover a deep dependency graph. It calls `get_entity_lineage` on the payments table, then iterates through each downstream node with `get_entity_details` to check for owners, DQ tests, and PII tags.

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

Additive changes produce a different kind of report. The agent finds no downstream breakage but identifies opportunities to propagate the new attribute.

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

## Batch Impact Analysis for CI/CD

The [`batch_analyzer.py`](./batch_analyzer.py) script extends the interactive agent for automated use in pull requests. It:

1. Reads a `git diff` file and extracts every changed `.sql` file under a `models/` directory.
2. Spins up the same agent from `impact_analyzer.py`.
3. Iterates over each changed model and asks the agent for its downstream impact.
4. Prints a combined Markdown report suitable for posting as a PR comment.

Run it locally:

```bash
git diff origin/main...HEAD > changes.diff
python batch_analyzer.py changes.diff
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
        run: pip install metadata-ai[langchain]

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

The agent uses LangChain, so you can swap in any compatible LLM by replacing the `ChatOpenAI` call in `impact_analyzer.py`:

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
