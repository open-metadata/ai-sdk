"""
Metadata Chatbot — Multi-Agent Metadata Assistant

A conversational chatbot powered by semantic search that discovers
metadata, explores lineage, and updates your data catalog through
agent-to-agent delegation.

Architecture:
    Orchestrator → Discovery Agent (semantic + keyword search)
                 → Lineage Agent (upstream/downstream tracing)
                 → Curator Agent (descriptions, tags, glossary)

Each specialist agent has its own MCP tools and system prompt.
The orchestrator delegates work to the right specialist based on
user intent and can chain multiple specialists for complex tasks.

Usage:
    python chatbot.py

Environment variables required:
    METADATA_HOST     - Your OpenMetadata server URL
    METADATA_TOKEN    - Your bot's JWT token
    OPENAI_API_KEY    - OpenAI API key (or configure different LLM)
"""

from typing import Any

from langchain.agents import create_agent
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from metadata_ai import MetadataAI, MetadataConfig
from metadata_ai.mcp.models import MCPTool


# ---------------------------------------------------------------------------
# System Prompts — Specialist Agents
# ---------------------------------------------------------------------------

DISCOVERY_PROMPT = """You are a Metadata Discovery specialist. Your expertise is
finding and describing data assets in the organization's data catalog.

You have access to:
- **semantic_search** — Find assets by meaning, not just keywords. Use this first
  for natural-language queries like "tables about customer behavior" or "revenue
  metrics."
- **search_metadata** — Keyword search across tables, dashboards, pipelines. Use
  this for exact names or technical terms like "stg_stripe__payments."
- **get_entity_details** — Get full details: columns, tags, owners, description.

Workflow:
1. Use semantic search first for natural-language queries
2. Fall back to keyword search for exact names or technical terms
3. Always retrieve full entity details for the top results
4. Include the entity's fully qualified name (FQN) in your response
5. Mention the owner, description, and tags when available

IMPORTANT: For every entity you mention, include its OpenMetadata link:
  [<entity name>]({metadata_host}/<entity_type>/<fqn>)

Provide a clear, structured summary of what you found."""


LINEAGE_PROMPT = """You are a Data Lineage specialist. Your expertise is tracing
how data flows through the organization — upstream sources and downstream consumers.

You have access to:
- **get_entity_lineage** — Trace upstream and downstream dependencies
- **get_entity_details** — Get full details of entities in the lineage graph

Workflow:
1. Get the lineage of the requested entity
2. Walk both upstream (sources) and downstream (consumers)
3. For key nodes in the lineage, get their details (type, owner, description)
4. Identify critical paths (PII propagation, finance marts, SLA dependencies)
5. Present the lineage as a clear textual flow

IMPORTANT: For every entity you mention, include its OpenMetadata link:
  [<entity name>]({metadata_host}/<entity_type>/<fqn>)

Structure your response as:

## Upstream Sources
Tables and views that feed into this entity.

## Downstream Consumers
Tables, views, and dashboards that depend on this entity.

## Data Flow
A textual representation of the lineage path, showing the chain of
transformations from source to final consumer."""


CURATOR_PROMPT = """You are a Metadata Curator specialist. Your expertise is
enriching and maintaining metadata quality in the data catalog.

You have access to:
- **get_entity_details** — Inspect current metadata before making changes
- **patch_entity** — Update descriptions, tags, and owners on entities
- **create_glossary_term** — Create new business glossary terms

Workflow:
1. ALWAYS get the current entity details before making any update
2. Show the user what you plan to change
3. Apply the update using patch_entity
4. Confirm what was changed

Safety rules:
- Never overwrite an existing description without showing the old one first
- When adding tags, preserve existing tags
- Report exactly what was changed in your response

IMPORTANT: For every entity you mention, include its OpenMetadata link:
  [<entity name>]({metadata_host}/<entity_type>/<fqn>)"""


# ---------------------------------------------------------------------------
# System Prompt — Orchestrator
# ---------------------------------------------------------------------------

ORCHESTRATOR_PROMPT = """You are a Metadata Assistant — a conversational chatbot
that helps users discover, understand, and manage their data catalog.

You coordinate three specialist agents, each with deep expertise:

1. **discover_metadata** — Finds data assets using semantic search and keyword
   search. Use this when the user wants to find tables, understand what data
   exists, or search for assets by meaning or keyword.

2. **explore_lineage** — Traces data lineage upstream and downstream. Use this
   when the user asks about data dependencies, data flow, impact analysis, or
   who produces / consumes a given dataset.

3. **update_metadata** — Enriches metadata by updating descriptions, adding
   tags, or creating glossary terms. Use this when the user wants to improve
   documentation or organize their catalog.

You can chain specialists together for complex tasks. Common patterns:

- "Find all customer tables and show their lineage"
  → discover_metadata first, then explore_lineage for each result

- "Find undocumented tables in the finance schema and add descriptions"
  → discover_metadata to find them, then update_metadata for each

- "What feeds into the revenue dashboard and who owns each source?"
  → explore_lineage to trace sources, the response will include owner details

- "Find tables related to payments and tag them as financial data"
  → discover_metadata to find them, then update_metadata to add tags

Rules:
- ALWAYS delegate to the right specialist — do not answer metadata questions
  from your own knowledge.
- For multi-step tasks, chain specialists in the right order.
- Synthesize the specialists' responses into a single coherent answer.
- Be conversational and helpful.
- If a request is ambiguous, make your best judgment about which specialist
  to call and what query to send."""


# ---------------------------------------------------------------------------
# Specialist Agent Factory
# ---------------------------------------------------------------------------

def _create_specialist(
    client: MetadataAI,
    tools: list[MCPTool],
    system_prompt: str,
):
    """Create a specialist LangChain agent with the given MCP tools."""
    langchain_tools = client.mcp.as_langchain_tools(include=tools)
    return create_agent(
        model="openai:gpt-4o",
        tools=langchain_tools,
        system_prompt=system_prompt,
    )


def _invoke_specialist(agent, query: str) -> str:
    """Invoke a specialist agent and return its text response."""
    result = agent.invoke({"messages": [{"role": "user", "content": query}]})
    return result["messages"][-1].content


# ---------------------------------------------------------------------------
# Orchestrator Tools — Each wraps a specialist agent
# ---------------------------------------------------------------------------

class _DiscoverInput(BaseModel):
    query: str = Field(
        description=(
            "Natural-language query describing what data assets to find. "
            "Examples: 'tables related to customer payments', "
            "'find the orders staging table', 'dashboards about revenue'."
        )
    )


class _LineageInput(BaseModel):
    query: str = Field(
        description=(
            "Name or description of the entity whose lineage to explore. "
            "Examples: 'stg_stripe__payments', 'the daily revenue fact table', "
            "'trace upstream sources of dim_customers'."
        )
    )


class _CuratorInput(BaseModel):
    query: str = Field(
        description=(
            "Description of what metadata to update, including the entity "
            "name and the desired changes. Examples: 'add description to "
            "stg_jaffle_shop__orders: Staging model that cleans raw order data', "
            "'tag dim_customers as Tier1', 'create glossary term for LTV'."
        )
    )


class DiscoverMetadataTool(BaseTool):
    """Delegates metadata discovery to the Discovery specialist agent."""

    name: str = "discover_metadata"
    description: str = (
        "Find data assets (tables, dashboards, pipelines) using semantic search "
        "and keyword search. The Discovery specialist searches the catalog and "
        "returns detailed results including owners, descriptions, and tags."
    )
    args_schema: type[BaseModel] = _DiscoverInput
    handle_tool_error: bool = True

    _specialist: Any

    def __init__(self, specialist, **kwargs: Any):
        super().__init__(**kwargs)
        self._specialist = specialist

    def _run(
        self,
        query: str,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> str:
        return _invoke_specialist(self._specialist, query)


class ExploreLineageTool(BaseTool):
    """Delegates lineage exploration to the Lineage specialist agent."""

    name: str = "explore_lineage"
    description: str = (
        "Trace data lineage — find upstream sources and downstream consumers "
        "of a data asset. The Lineage specialist maps the full dependency graph "
        "and identifies critical paths."
    )
    args_schema: type[BaseModel] = _LineageInput
    handle_tool_error: bool = True

    _specialist: Any

    def __init__(self, specialist, **kwargs: Any):
        super().__init__(**kwargs)
        self._specialist = specialist

    def _run(
        self,
        query: str,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> str:
        return _invoke_specialist(self._specialist, query)


class UpdateMetadataTool(BaseTool):
    """Delegates metadata updates to the Curator specialist agent."""

    name: str = "update_metadata"
    description: str = (
        "Update metadata in the catalog — add or improve descriptions, apply "
        "tags, or create glossary terms. The Curator specialist inspects current "
        "metadata before applying changes and reports what was modified."
    )
    args_schema: type[BaseModel] = _CuratorInput
    handle_tool_error: bool = True

    _specialist: Any

    def __init__(self, specialist, **kwargs: Any):
        super().__init__(**kwargs)
        self._specialist = specialist

    def _run(
        self,
        query: str,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> str:
        return _invoke_specialist(self._specialist, query)


# ---------------------------------------------------------------------------
# Chatbot Factory
# ---------------------------------------------------------------------------

def create_chatbot():
    """Create the multi-agent metadata chatbot.

    Returns the orchestrator agent and the MetadataAI client.
    The orchestrator delegates to three specialist agents (Discovery,
    Lineage, Curator), each with their own MCP tools.
    """
    config = MetadataConfig.from_env()
    client = MetadataAI.from_config(config)
    host = config.host.rstrip("/")

    # Create specialist agents, each with a focused set of MCP tools
    discovery = _create_specialist(
        client,
        tools=[
            MCPTool.SEMANTIC_SEARCH,
            MCPTool.SEARCH_METADATA,
            MCPTool.GET_ENTITY_DETAILS,
        ],
        system_prompt=DISCOVERY_PROMPT.format(metadata_host=host),
    )

    lineage = _create_specialist(
        client,
        tools=[MCPTool.GET_ENTITY_LINEAGE, MCPTool.GET_ENTITY_DETAILS],
        system_prompt=LINEAGE_PROMPT.format(metadata_host=host),
    )

    curator = _create_specialist(
        client,
        tools=[
            MCPTool.GET_ENTITY_DETAILS,
            MCPTool.PATCH_ENTITY,
            MCPTool.CREATE_GLOSSARY_TERM,
        ],
        system_prompt=CURATOR_PROMPT.format(metadata_host=host),
    )

    # Wrap specialist agents as orchestrator tools
    orchestrator_tools = [
        DiscoverMetadataTool(specialist=discovery),
        ExploreLineageTool(specialist=lineage),
        UpdateMetadataTool(specialist=curator),
    ]

    # The orchestrator agent delegates to specialists
    orchestrator = create_agent(
        model="openai:gpt-4o",
        tools=orchestrator_tools,
        system_prompt=ORCHESTRATOR_PROMPT,
    )

    return orchestrator, client


def chat(agent, message: str) -> str:
    """Send a message to the chatbot and return its response.

    Useful for programmatic usage and testing.
    """
    result = agent.invoke(
        {"messages": [{"role": "user", "content": message}]}
    )
    return result["messages"][-1].content


# ---------------------------------------------------------------------------
# Interactive Session
# ---------------------------------------------------------------------------

def main():
    """Interactive metadata chatbot session."""
    print("=" * 60)
    print("  Metadata Chatbot — Multi-Agent Assistant")
    print("=" * 60)
    print()
    print("I can help you discover, explore, and enrich your metadata.")
    print("Ask me anything about your data catalog!")
    print()
    print("Examples:")
    print('  "Find all tables related to customer data"')
    print('  "What feeds into the daily revenue report?"')
    print('  "Add a description to the orders staging table"')
    print('  "Find undocumented finance tables and describe them"')
    print()
    print("Type 'quit' to exit.")
    print()

    orchestrator, client = create_chatbot()

    try:
        while True:
            print("-" * 60)
            question = input("\nYou: ").strip()

            if question.lower() in ("quit", "exit", "q"):
                print("\nGoodbye!")
                break

            if not question:
                continue

            print("\nThinking...\n")
            response = chat(orchestrator, question)

            print("Assistant:")
            print(response)

    finally:
        client.close()


if __name__ == "__main__":
    main()
