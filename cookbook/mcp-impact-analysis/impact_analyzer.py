"""
Data Change Impact Analyzer

An AI agent that helps assess the impact of schema changes
before they're made, using OpenMetadata's MCP tools.

Optionally sends a deprecation notice to Slack so the right
people are pinged and the conversation starts in your organization.

Usage:
    python impact_analyzer.py

Environment variables required:
    AI_SDK_HOST       - Your OpenMetadata server URL
    AI_SDK_TOKEN      - Your bot's JWT token
    OPENAI_API_KEY    - OpenAI API key (or configure different LLM)

Optional:
    SLACK_WEBHOOK_URL - Slack Incoming Webhook for deprecation notices
"""

import json
import os
import re
import urllib.error
import urllib.request

from langchain.agents import create_agent

from ai_sdk import AiSdk, AiSdkConfig
from ai_sdk.mcp.models import MCPTool


SYSTEM_PROMPT = """You are a Data Impact Analyst assistant. Your job is to help
data engineers understand the downstream impact of schema changes before they make them.

When analyzing a change, you should:

1. **Find the asset** - Search for the table/column being modified
2. **Trace lineage** - Get downstream dependencies (tables, views, dashboards)
3. **Identify owners** - Find who owns affected assets
4. **Assess risk** - Consider data quality tests, PII implications, SLAs
5. **Summarize impact** - Provide a clear, actionable report

IMPORTANT: For every entity you mention (tables, views, dashboards, pipelines, etc.),
always include its OpenMetadata link using the format:
  [<entity name>]({metadata_host}/<entity_type>/<fqn>)

For example:
  [raw_jaffle_shop.customers]({metadata_host}/table/jaffle_shop.public.customers)

This ensures the report is actionable — readers can click through to the entity in
OpenMetadata directly.

Always structure your response as:

## What Changed
One or two sentences explaining the concrete modification shown in the diff
(e.g. "The column `order_status` was renamed to `fulfillment_status`" or
"A new `currency` column was added and test transactions are now filtered out").
If no diff was provided, summarize what the user described.

## Impact Summary
Brief overview of the downstream scope and overall risk level.

## Affected Assets
List of downstream tables, views, and dashboards with their owners.
Each asset MUST include its OpenMetadata link.

## Risk Assessment
- Data Quality: Tests that may fail
- Compliance: PII/sensitive data implications
- Business: Dashboards or reports affected

## Recommended Actions
1. Notify these stakeholders: [list with owner names]
2. Update these assets: [list with links]
3. Consider these alternatives: [if any]

Use the available tools to gather accurate, real-time metadata.
"""


def create_impact_analyzer():
    """Create an impact analysis agent with MCP tools."""

    config = AiSdkConfig.from_env()
    client = AiSdk.from_config(config)

    # Use read-only MCP tools for safety
    tools = client.mcp.as_langchain_tools(
        include=[
            MCPTool.SEARCH_METADATA,
            MCPTool.GET_ENTITY_DETAILS,
            MCPTool.GET_ENTITY_LINEAGE,
        ]
    )

    # Interpolate the host URL so the agent can build entity links
    system_prompt = SYSTEM_PROMPT.format(metadata_host=config.host.rstrip("/"))

    agent = create_agent(
        model="openai:gpt-4o",
        tools=tools,
        system_prompt=system_prompt,
    )

    return agent, client


def analyze_change(agent, change_description: str) -> dict:
    """Analyze the impact of a proposed change.

    Returns:
        Dict with 'analysis' (str) key.
    """
    result = agent.invoke(
        {"messages": [{"role": "user", "content": change_description}]}
    )
    # The last AI message contains the final answer
    ai_message = result["messages"][-1]
    return {"analysis": ai_message.content}


def _markdown_to_slack_mrkdwn(text: str) -> str:
    """Convert markdown bold/links to Slack mrkdwn format.

    Slack uses *bold* (single asterisk) instead of **bold** (double),
    and <url|label> instead of [label](url).
    """

    # Convert markdown links [text](url) → Slack <url|text>
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"<\2|\1>", text)
    # Convert **bold** → *bold*
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    return text


def send_to_slack(webhook_url: str, analysis: str, change_description: str) -> bool:
    """Send a deprecation notice to Slack via Incoming Webhook.

    Returns True on success, False on failure.
    """
    slack_body = _markdown_to_slack_mrkdwn(analysis)

    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Deprecation Notice — Impact Analysis",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Proposed change:* {change_description}",
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": slack_body,
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Sent by the Data Change Impact Analyzer · ai-sdk-sdk",
                    }
                ],
            },
        ],
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as response:
            return response.status == 200
    except urllib.error.URLError as exc:
        print(f"\nFailed to send Slack message: {exc}")
        return False


def main():
    """Interactive impact analysis session."""
    print("=" * 60)
    print("Data Change Impact Analyzer")
    print("=" * 60)
    print("\nThis tool helps you understand the impact of schema changes")
    print("before you make them. Describe your planned change and I'll")
    print("analyze the downstream dependencies.\n")

    slack_webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if slack_webhook:
        print("Slack integration: enabled")
    else:
        print("Slack integration: disabled (set SLACK_WEBHOOK_URL to enable)")

    print("\nType 'quit' to exit.\n")

    agent, client = create_impact_analyzer()

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
            result = analyze_change(agent, change)

            print("\n" + "=" * 60)
            print("IMPACT ANALYSIS REPORT")
            print("=" * 60)
            print(result["analysis"])

            if slack_webhook:
                send = input("\nSend deprecation notice to Slack? [y/N] ").strip().lower()
                if send == "y":
                    print("Sending to Slack...")
                    if send_to_slack(slack_webhook, result["analysis"], change):
                        print("Deprecation notice sent to Slack.")
                    else:
                        print("Failed to send Slack message. Check your SLACK_WEBHOOK_URL.")

    finally:
        client.close()


if __name__ == "__main__":
    main()
