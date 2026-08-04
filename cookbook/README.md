# Metadata AI Cookbook

Practical examples and workflows for integrating Metadata AI into your data platform.

## Demo Environment

| Resource | Description |
|----------|-------------|
| [Demo Database](./resources/demo-database/) | PostgreSQL + dbt + Metabase setup with realistic e-commerce data. Use this as the foundation for testing all cookbook examples. |
| [Banking Demo](./resources/banking/) | Full banking stack on **Redshift or BigQuery** — 38 raw tables, ~70 dbt models, 4 Superset dashboards, glossaries, PII classification, and Context Center seeding. Pick the warehouse with `WAREHOUSE=bigquery`. |

## Use Cases

| Use Case | Description | Tools |
|----------|-------------|-------|
| [MCP Impact Analysis](./mcp-impact-analysis/) | AI-powered impact analysis for schema changes using MCP tools | Python SDK, LangChain |
| [DQ Failure Slack Notifications](./dq-failure-slack-notifications/) | Automatically analyze Data Quality failures and send impact summaries to Slack | n8n, Slack |
| [dbt Model PR Review](./dbt-pr-review/) | Automatically review dbt model changes for downstream impact and DQ risks | GitHub Actions, Python SDK |
| [GDPR DSAR Compliance](./gdpr-dsar-compliance/) | Trace PII across your catalog to handle GDPR deletion and access requests | TypeScript SDK, Browser |
| [MCP Metadata Chatbot](./mcp-metadata-chatbot/) | Multi-agent chatbot with semantic search, lineage exploration, and metadata curation via agent-to-agent delegation | Python SDK, LangChain |
| [Persona-aware Context](./persona-aware-context/) | One LangChain agent, two users — each sees a different, RBAC- and persona-scoped view of the same asset via AI Entity Context + AI Persona Context | Python SDK, LangChain |

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
