#!/usr/bin/env python3
"""
Example: Using AI Agents with LangChain

This example demonstrates how to use the SemanticLayerAgent as a tool
in a LangChain pipeline to query metrics and explore your semantic layer.

Prerequisites:
    pip install data-ai-sdk[langchain]

Environment variables:
    AI_SDK_HOST: Your server URL
    AI_SDK_TOKEN: Your bot JWT token
    OPENAI_API_KEY: Your OpenAI API key

Usage:
    python example.py           # Normal mode (minimal output)
    python example.py --debug   # Debug mode (verbose logging)
"""

import argparse
import os
import sys

from langchain.agents import create_agent

from ai_sdk import AISdk, set_debug
from ai_sdk.exceptions import (
    AgentNotEnabledError,
    AgentNotFoundError,
    AuthenticationError,
    AISdkError,
)
from ai_sdk.integrations.langchain import AISdkAgentTool


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="AI SDK Example")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging for verbose output",
    )
    args = parser.parse_args()

    # Enable debug mode if requested
    if args.debug:
        set_debug(True)
        print("[DEBUG MODE ENABLED]")

    # Configuration from environment
    metadata_host = os.getenv("AI_SDK_HOST", "http://localhost:8585")
    metadata_token = os.getenv("AI_SDK_TOKEN")

    if not metadata_token:
        print("Error: AI_SDK_TOKEN environment variable is required")
        sys.exit(1)

    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable is required")
        sys.exit(1)

    # Initialize client
    print(f"Connecting to server at {metadata_host}...")
    client = AISdk(
        host=metadata_host,
        token=metadata_token,
    )

    try:
        # Create a LangChain tool from the SemanticLayerAgent
        print("Setting up SemanticLayerAgent...")
        semantic_layer_tool = AISdkAgentTool.from_client(
            client,
            "SemanticLayerAgent",
            name="semantic_layer",
            description=(
                "Query the semantic layer to get business metrics, KPIs, and dimensions. "
                "Use this tool to answer questions about revenue, customers, orders, "
                "and other business metrics defined in your data models."
            ),
        )

        # Create the agent with the new LangChain 1.x API
        agent = create_agent(
            model="openai:gpt-4",
            tools=[semantic_layer_tool],
            system_prompt="""You are a business intelligence assistant with access to the semantic layer.

CRITICAL RULES - YOU MUST FOLLOW THESE EXACTLY:
1. You can ONLY provide information that comes DIRECTLY from tool responses
2. If a tool returns empty, blank, or no data, you MUST say: "I could not retrieve that information from the semantic layer."
3. NEVER invent, guess, fabricate, or make up metrics, data, numbers, or names
4. NEVER provide example data or placeholder data
5. If the tool response is empty, DO NOT answer the question with made-up data
6. Only describe data that was EXPLICITLY returned by the tool

You can help users by using the semantic_layer tool to:
- Query business metrics and KPIs
- Explore available dimensions and measures
- Answer questions about business performance

If the semantic_layer tool returns empty or no results, respond with:
"The semantic layer returned no data for this query. Please verify that the requested metrics/dimensions exist."

DO NOT HALLUCINATE. DO NOT MAKE UP DATA. ONLY USE ACTUAL TOOL RESPONSES.""",
        )

        # Queries to run
        queries = [
            "What metrics are available in the semantic layer? Show me how to compute them.",
            "Compute our current total eco-friendly sales",
        ]

        print("\n" + "=" * 60)
        print("Running Semantic Layer Queries")
        print("=" * 60)

        for query in queries:
            print(f"\n{'=' * 60}")
            print(f"Query: {query}")
            print("=" * 60)

            result = agent.invoke({"messages": [{"role": "user", "content": query}]})

            # Debug: Print all messages to see the full flow
            if args.debug:
                print("\n[DEBUG] Full message flow:")
                for i, msg in enumerate(result["messages"]):
                    content = getattr(msg, 'content', 'N/A')
                    content_preview = content[:200] if content else 'N/A'
                    print(f"  [{i}] {msg.__class__.__name__}: {content_preview}...")
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        print(f"      tool_calls: {msg.tool_calls}")

            # Get the last message from the agent
            last_message = result["messages"][-1]
            print(f"\nResult:\n{last_message.content}")

        print("\n" + "=" * 60)
        print("Done!")
        print("=" * 60)

    except AuthenticationError:
        print("Error: Invalid or expired token")
        sys.exit(1)

    except AgentNotFoundError as e:
        print(f"Error: Agent not found: {e.agent_name}")
        sys.exit(1)

    except AgentNotEnabledError as e:
        print(f"Error: Agent '{e.agent_name}' is not API-enabled")
        sys.exit(1)

    except AISdkError as e:
        print(f"AI SDK error: {e}")
        sys.exit(1)

    finally:
        client.close()


if __name__ == "__main__":
    main()
