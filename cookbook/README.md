# Metadata AI Cookbook

Practical examples and workflows for integrating Metadata AI into your data platform.

## Use Cases

| Use Case | Description | Tools |
|----------|-------------|-------|
| [DQ Failure Slack Notifications](./dq-failure-slack-notifications/) | Automatically analyze Data Quality failures and send impact summaries to Slack | n8n, Slack |

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
