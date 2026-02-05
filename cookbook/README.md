# Metadata AI Cookbook

Practical examples and workflows for integrating Metadata AI into your data platform.

## Demo Environment

| Resource | Description |
|----------|-------------|
| [Demo Database](./demo-database/) | PostgreSQL + dbt + Metabase setup with realistic e-commerce data. Use this as the foundation for testing all cookbook examples. |

## Use Cases

| Use Case | Description | Tools |
|----------|-------------|-------|
| [MCP Impact Analysis](./mcp-impact-analysis/) | AI-powered impact analysis for schema changes using MCP tools | Python SDK, LangChain |
| [DQ Failure Slack Notifications](./dq-failure-slack-notifications/) | Automatically analyze Data Quality failures and send impact summaries to Slack | n8n, Slack |
| [dbt Model PR Review](./dbt-pr-review/) | Automatically review dbt model changes for downstream impact and DQ risks | GitHub Actions, Python SDK |

## Getting Started

Each cookbook entry includes:
- **Step-by-step tutorial** - Detailed walkthrough
- **Importable artifacts** - Workflow files, config snippets
- **Agent configuration** - Required Dynamic Agents and abilities

## Prerequisites

- Running Collate/OpenMetadata instance
- API access enabled (JWT token)
- [Metadata AI CLI](../cli/) or SDK installed

## Contributing

To add a new use case:
1. Create a directory under `cookbook/`
2. Include a `README.md` with tutorial steps
3. Add any importable files (workflow JSON, scripts)
4. Update this index
