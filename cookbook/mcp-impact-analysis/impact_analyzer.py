"""
Data Change Impact Analyzer

An AI agent that helps assess the impact of schema changes
before they're made, using OpenMetadata's MCP tools.

Usage:
    python impact_analyzer.py

Environment variables required:
    METADATA_HOST - Your OpenMetadata server URL
    METADATA_TOKEN - Your bot's JWT token
    OPENAI_API_KEY - OpenAI API key (or configure different LLM)
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
