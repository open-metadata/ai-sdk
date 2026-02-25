# dbt Model PR Review

Automatically review dbt model changes in pull requests, analyzing downstream impact, data quality risks, and breaking changes using Metadata AI.

## Overview

When a PR modifies dbt models (`models/**/*.sql`), this workflow:
1. Extracts the git diff for changed model files
2. Invokes a Metadata AI agent with the diff content
3. Agent searches OpenMetadata for each model by name
4. Agent analyzes lineage, DQ tests, and identifies breaking changes
5. Posts a structured review comment on the PR

## Prerequisites

- Collate/OpenMetadata instance with your dbt models cataloged
- GitHub repository with dbt models in `models/` directory
- Metadata AI agent configured (see [agent-config.md](./agent-config.md))

## Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   GitHub PR     │ trigger │  GitHub Action   │  invoke │  Metadata AI    │
│  (dbt models)   │────────►│    Workflow      │────────►│  Agent (API)    │
└─────────────────┘         └────────┬─────────┘         └────────┬────────┘
                                     │                            │
                                     │ post comment               │ searches models
                                     ▼                            │ explores lineage
                              ┌─────────────┐                     │ checks DQ tests
                              │ PR Comment  │◄────────────────────┘
                              │  (review)   │      returns analysis
                              └─────────────┘
```

## Step 1: Create the Agent

See [agent-config.md](./agent-config.md) for detailed setup instructions.

**Quick setup with CLI:**

```bash
# Create the Persona
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

# Create the Agent
ai-sdk agents create \
  --name DBTReviewer \
  --description "Reviews dbt model PRs for downstream impact and DQ risks" \
  --persona DBTReviewerPersona \
  --abilities discoveryAndSearch,dataLineageAndExploration,dataQualityAndTesting \
  --api-enabled true
```

## Step 2: Configure GitHub Secrets

Add these secrets to your GitHub repository (Settings → Secrets and variables → Actions):

| Secret | Description |
|--------|-------------|
| `AI_SDK_HOST` | Your Collate/OpenMetadata instance URL (e.g., `https://your-instance.getcollate.io`) |
| `AI_SDK_TOKEN` | JWT token for API authentication |

## Step 3: Add the Workflow

Copy the workflow file to your repository:

```bash
mkdir -p .github/workflows .github/scripts
cp dbt-review.yml .github/workflows/
cp dbt_review.py .github/scripts/
```

Or create the files manually using the contents in this cookbook.

### Workflow File: `.github/workflows/dbt-review.yml`

```yaml
name: dbt Model Review

on:
  pull_request:
    types: [opened, synchronize]
    paths:
      - 'models/**/*.sql'

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Get changed models
        id: changes
        run: |
          FILES=$(git diff --name-only origin/${{ github.base_ref }}...HEAD -- 'models/**/*.sql')
          echo "files<<EOF" >> $GITHUB_OUTPUT
          echo "$FILES" >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT

      - name: Setup Python
        if: steps.changes.outputs.files != ''
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        if: steps.changes.outputs.files != ''
        run: pip install ai-sdk

      - name: Run dbt review
        if: steps.changes.outputs.files != ''
        env:
          AI_SDK_HOST: ${{ secrets.AI_SDK_HOST }}
          AI_SDK_TOKEN: ${{ secrets.AI_SDK_TOKEN }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_BASE_REF: ${{ github.base_ref }}
        run: |
          python .github/scripts/dbt_review.py \
            --pr-number ${{ github.event.pull_request.number }} \
            --changed-files "${{ steps.changes.outputs.files }}"
```

### Review Script: `.github/scripts/dbt_review.py`

See [dbt_review.py](./dbt_review.py) for the full script.

## Step 4: Test the Integration

1. Create a branch with changes to a dbt model
2. Open a pull request
3. Watch the Actions tab for the workflow run
4. Check the PR for the review comment

## Sample Output

```markdown
## 🔍 dbt Model Review

### Summary
Changes to `orders.sql` affect 2 dashboards and 1 downstream model. One DQ test may need updating.

### Impact Analysis

**orders.sql** → `warehouse.analytics.orders`

| Downstream Asset | Type | Risk |
|------------------|------|------|
| Daily Revenue Dashboard | Dashboard | 🔴 High - uses `total_amount` column |
| customer_summary | Table | 🟡 Medium - aggregates from this model |
| Weekly Sales Report | Dashboard | 🟢 Low - only uses `order_date` |

### Data Quality Risks

- **columnValuesToBeNotNull** on `customer_id` - ✅ No impact
- **columnValuesToBeBetween** on `total_amount` - ⚠️ Review needed

### Breaking Changes

- Column `order_total` renamed to `total_amount` on line 15

### Recommendations

1. Verify `Daily Revenue Dashboard` calculates correctly with new column name
2. Update downstream references to use `total_amount`
3. Review the DQ test bounds on `total_amount`

---
*Powered by [Metadata AI](https://github.com/open-metadata/ai-sdk)*
```

## Customization

### Change the Models Path

If your dbt models are in a different directory, update the workflow:

```yaml
paths:
  - 'dbt/models/**/*.sql'  # Adjust to your path
```

And update the diff command in the workflow accordingly.

### Make Review Required

By default, the review is advisory. To make it a required check:

1. Go to repository Settings → Branches → Branch protection rules
2. Add a rule for your main branch
3. Enable "Require status checks to pass"
4. Add "dbt Model Review" to required checks

### Customize Review Focus

Edit the prompt in `dbt_review.py` to focus on specific concerns:

```python
# Example: Focus only on breaking changes
prompt = """Review these dbt model changes. Focus ONLY on:
1. Column renames or removals
2. Changed data types
3. Modified join conditions
4. Altered filter logic

Ignore cosmetic changes like formatting or comments."""
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Workflow not triggering | Check that PR changes files matching `models/**/*.sql` |
| "Model not found" in review | Ensure models are cataloged in OpenMetadata |
| Authentication error | Verify `AI_SDK_HOST` and `AI_SDK_TOKEN` secrets |
| Empty review comment | Check agent has required abilities enabled |
| Comment not posting | Verify workflow has `pull-requests: write` permission |

## Related Resources

- [Metadata AI Python SDK](../../python/)
- [Metadata AI CLI](../../cli/)
- [Agent Configuration Guide](./agent-config.md)
