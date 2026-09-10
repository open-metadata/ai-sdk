"""
Persona-aware Context — one agent, two users, two realities.

This demo runs the SAME LangChain agent, with the SAME system prompt and the
SAME tools, twice — once as a **Compliance Officer** and once as a **Data
Engineer**. The only thing that changes is the OpenMetadata token each agent
authenticates with.

Every difference you see in the output is produced server-side by OpenMetadata:

    * AI Persona Context  (get_persona_context)  — a curated, per-persona
      working document. The Compliance persona surfaces PII, glossary, and
      data-quality; the Data Engineer persona surfaces schema, lineage, and
      profiling. Same catalog, different lens.

    * AI Entity Context   (get_entity_details, include=["context"]) — the full
      "Context Profile" of a single asset, filtered live by the caller's RBAC.
      The Compliance Officer owns the asset and sees its PII column profiles;
      the Data Engineer gets the same asset with those profiles withheld.
      (Earlier notes call this tool ``get_asset_context``; on an OpenMetadata
      2.0 server it is a section of ``get_entity_details``.)

The agent never knows who it is. The MCP tools only ever return what the
current identity is allowed to see. That is the whole point: RBAC and persona
scoping live in the platform, not in the prompt.

--------------------------------------------------------------------------------
Prerequisites
--------------------------------------------------------------------------------
1. An OpenMetadata 2.0 instance with the Jaffle Shop demo database
   (``cookbook/resources/demo-database``) ingested. Run ``setup_demo.py`` first:
   it creates the users, personas, PII tags, profiles and data-quality results
   this demo reads, and prints one access token per user.

2. Two personal access tokens — one per demo user:
       * David Kim    -> ComplianceOfficer persona
       * Sara Johnson -> DataEngineer persona

3. Install dependencies:
       pip install "data-ai-sdk[langchain]" langchain langchain-openai

--------------------------------------------------------------------------------
Environment variables
--------------------------------------------------------------------------------
    AI_SDK_HOST             OpenMetadata base URL (e.g. http://localhost:8585)
    DEMO_COMPLIANCE_TOKEN   PAT for the Compliance Officer user (David Kim)
    DEMO_ENGINEER_TOKEN     PAT for the Data Engineer user (Sara Johnson)
    OPENAI_API_KEY          Required only for the agent scenes (--agent)
    DEMO_MODEL              Optional. LangChain model id. Default: openai:gpt-4o
                            (e.g. "anthropic:claude-sonnet-5" also works)
    DEMO_TABLE_FQN          Optional. Fully qualified name of the asset to
                            compare in the RBAC scene. If unset, the demo tries
                            to resolve it from --table via search.

--------------------------------------------------------------------------------
Usage
--------------------------------------------------------------------------------
    # Full demo (persona scene + asset scene, agent answers + raw tool diff)
    python persona_demo.py

    # Just the deterministic proof, no LLM key needed
    python persona_demo.py --no-agent

    # One scene, explicit asset
    python persona_demo.py --scene asset \
        --table-fqn "jaffle shop.jaffle_shop.marts_core.dim_customers"
"""

from __future__ import annotations

import argparse
import difflib
import os
import sys
from dataclasses import dataclass
from typing import cast

from ai_sdk import AISdk
from ai_sdk.mcp.models import MCPTool

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# The read-only, context-focused tool set both agents receive. Identical for
# every identity — the server decides what each call is allowed to return.
# `get_entity_details(include=["context"])` is how an OpenMetadata 2.0 server
# returns an asset's Context Profile. The list is intersected with what the
# server actually advertises (see ``available_tools``) so a build that omits one
# of these degrades instead of failing with "Unknown tool: invalid_tool_name".
WANTED_TOOLS: list[MCPTool] = [
    MCPTool.GET_PERSONA_CONTEXT,
    MCPTool.GET_ENTITY_DETAILS,
    MCPTool.FIND_CONTEXT,
    MCPTool.SEARCH_METADATA,
    MCPTool.SEMANTIC_SEARCH,
    MCPTool.GET_ENTITY_LINEAGE,
]

# One prompt for everyone. Note there is nothing persona-specific here: the
# agent is told to trust the tools, and the tools are already scoped to the
# caller. That is what makes the two runs diverge.
SYSTEM_PROMPT = """You are a data catalog assistant embedded in OpenMetadata.

You answer using ONLY the tools provided. Those tools already return context
scoped to the current user's persona and permissions — you never choose a
persona or filter anything yourself.

Tool guide:
- ALWAYS begin by calling get_persona_context with no arguments — this returns
  YOUR persona's working context and OPERATING RULES (how you should answer).
  Do this first for EVERY question, including questions about a specific asset.
- Then, for a specific asset, call get_entity_details with entityType, fqn and
  include=["context", "quality"] — that returns the asset's Context Profile and
  its data-quality standing. If you only know the asset's name, call
  search_metadata first to resolve its fully qualified name.
- Use find_context for glossary definitions and documentation.

Rules:
- Your persona context may contain OPERATING RULES (for example a knowledge
  article titled "... Operating Rules"). Treat them as instructions for HOW to
  answer: what to lead with, what to cite, what format to use. Apply them and
  state which rule you followed.
- Never invent columns, tags, metrics, or values that are not in the tool
  output. If a column is masked, redacted, or absent, say so explicitly.
- Be faithful and concise. Report what your persona and permissions actually
  expose, and call out anything that appears restricted."""

PERSONA_QUESTION = (
    "What's my working context? Summarize what I should focus on for our "
    "customer and order data, and why those things matter for my role."
)

ASSET_QUESTION_TEMPLATE = (
    "Give me the full context for the `{table}` table: its columns, any "
    "sensitive/PII fields, profiling detail if available, and its data-quality "
    "standing. Be explicit about anything you cannot see."
)

DEFAULT_TABLE = "dim_customers"
DEFAULT_TABLE_FQN = "jaffle shop.jaffle_shop.marts_core.dim_customers"


@dataclass
class Identity:
    """A demo user: a label, the persona they carry, and their access token."""

    label: str
    persona: str
    token: str


# ---------------------------------------------------------------------------
# Agent wiring (mirrors cookbook/mcp-metadata-chatbot/chatbot.py)
# ---------------------------------------------------------------------------


def available_tools(client: AISdk) -> list[MCPTool]:
    """The wanted tools this server actually advertises to this caller."""
    advertised = {tool.name for tool in client.mcp.list_tools()}
    return [tool for tool in WANTED_TOOLS if tool in advertised]


def build_agent(client: AISdk, model: str):
    """Create a LangChain agent wired to the identity's scoped MCP tools.

    ``as_langchain_tools`` calls the MCP server's ``list_tools`` under this
    client's token and builds a LangChain tool per allowed MCP tool. Two
    clients -> two tool sets that behave differently even though the code is
    identical.
    """
    from langchain.agents import create_agent

    langchain_tools = client.mcp.as_langchain_tools(include=available_tools(client))
    return create_agent(
        model=model,
        tools=langchain_tools,
        system_prompt=SYSTEM_PROMPT,
    )


def run_agent(agent, question: str) -> str:
    """Invoke an agent and return its final text answer."""
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    return result["messages"][-1].content


# ---------------------------------------------------------------------------
# Raw MCP calls — deterministic proof, no LLM involved
# ---------------------------------------------------------------------------


def _extract_markdown(data: object) -> str:
    """Pull the rendered markdown out of an MCP tool result payload."""
    if isinstance(data, dict):
        payload = cast("dict[str, object]", data)
        for key in ("content", "markdown", "text"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value
    if isinstance(data, str):
        return data
    return str(data)


def raw_persona_context(client: AISdk) -> str:
    """Fetch the caller's persona context document as markdown (no LLM)."""
    result = client.mcp.call_tool(MCPTool.GET_PERSONA_CONTEXT, {"format": "markdown"})
    if not result.success or result.data is None:
        return f"(no persona context returned: {result.error})"
    return _extract_markdown(result.data)


def raw_asset_context(client: AISdk, entity_type: str, fqn: str) -> str:
    """Fetch a single asset's Context Profile as markdown (no LLM)."""
    result = client.mcp.call_tool(
        MCPTool.GET_ENTITY_DETAILS,
        {
            "entityType": entity_type,
            "fqn": fqn,
            "include": ["context", "quality"],
            "format": "markdown",
        },
    )
    if not result.success or result.data is None:
        return f"(no asset context returned: {result.error})"
    payload = result.data
    section = payload.get("context") if isinstance(payload, dict) else None
    return _extract_markdown(section if section is not None else payload)


def resolve_table_fqn(client: AISdk, table: str, explicit: str | None) -> str | None:
    """Resolve a table's FQN: explicit flag/env wins, else best-effort search."""
    if explicit:
        return explicit
    env_fqn = os.environ.get("DEMO_TABLE_FQN")
    if env_fqn:
        return env_fqn
    if table == DEFAULT_TABLE:
        return DEFAULT_TABLE_FQN
    # Best-effort resolution via search. Shapes vary across builds, so we dig
    # defensively and fall back to None (the caller prints guidance).
    result = client.mcp.call_tool(
        MCPTool.SEARCH_METADATA,
        {"query": table, "entity_type": "table"},
    )
    if not result.success or not isinstance(result.data, dict):
        return None
    hits = (
        result.data.get("results") or result.data.get("hits") or result.data.get("data")
    )
    if isinstance(hits, list):
        for hit in hits:
            if isinstance(hit, dict):
                fqn = hit.get("fullyQualifiedName") or hit.get("fqn")
                if isinstance(fqn, str) and table in fqn:
                    return fqn
    return None


# ---------------------------------------------------------------------------
# Presentation helpers
# ---------------------------------------------------------------------------


def _banner(title: str) -> None:
    print("\n" + "=" * 78)
    print(f"  {title}")
    print("=" * 78)


def _side_by_side_note() -> None:
    print(
        "\n(Same agent, same prompt, same question — the only difference is "
        "which token\n authenticated the MCP calls.)\n"
    )


def _strip_volatile(document: str) -> str:
    """Drop generation timestamps so a diff shows content, not clock skew."""
    return "\n".join(
        line
        for line in document.splitlines()
        if not line.startswith(("timestamp:", "generated_at:", "fingerprint:"))
    )


def print_diff(left: str, right: str, left_label: str, right_label: str) -> None:
    """Show a unified diff so withheld / omitted lines are obvious."""
    diff = difflib.unified_diff(
        _strip_volatile(left).splitlines(),
        _strip_volatile(right).splitlines(),
        fromfile=left_label,
        tofile=right_label,
        lineterm="",
    )
    body = "\n".join(diff)
    _banner(f"DIFF — {left_label}  vs  {right_label}")
    if body.strip():
        print(body)
        print(
            f"\n^ Lines prefixed '-' are visible only to {left_label}; '+' only to {right_label}."
        )
    else:
        print(
            "(identical — did setup_demo.py apply the persona rules, PII tags and ownership?)"
        )


# ---------------------------------------------------------------------------
# Scenes
# ---------------------------------------------------------------------------


def scene_persona(
    compliance: tuple[Identity, object],
    engineer: tuple[Identity, object],
    clients: dict[str, AISdk],
    use_agent: bool,
    use_raw: bool,
) -> None:
    """Axis B — different personas, different curated working context."""
    _banner("SCENE 1 — AI Persona Context: 'what should I focus on?'")
    _side_by_side_note()

    if use_agent:
        for identity, agent in (compliance, engineer):
            _banner(f"{identity.label}  ({identity.persona})  — agent answer")
            print(run_agent(agent, PERSONA_QUESTION))

    if use_raw:
        left = raw_persona_context(clients[compliance[0].label])
        right = raw_persona_context(clients[engineer[0].label])
        print_diff(left, right, compliance[0].persona, engineer[0].persona)


def scene_asset(
    compliance: tuple[Identity, object],
    engineer: tuple[Identity, object],
    clients: dict[str, AISdk],
    table: str,
    table_fqn: str | None,
    use_agent: bool,
    use_raw: bool,
) -> None:
    """Axis A — same asset, RBAC-filtered per caller."""
    _banner(f"SCENE 2 — AI Entity Context: RBAC on `{table}`")
    _side_by_side_note()

    question = ASSET_QUESTION_TEMPLATE.format(table=table)
    if use_agent:
        for identity, agent in (compliance, engineer):
            _banner(f"{identity.label}  ({identity.persona})  — agent answer")
            print(run_agent(agent, question))

    if use_raw:
        fqn = resolve_table_fqn(clients[compliance[0].label], table, table_fqn)
        if fqn is None:
            print(
                "\n[skipping raw asset diff] Could not resolve the table FQN.\n"
                "Pass --table-fqn <fqn> or set DEMO_TABLE_FQN "
                '(e.g. "jaffle shop.jaffle_shop.marts_core.dim_customers").'
            )
            return
        print(f"\nComparing the Context Profile of: {fqn}")
        left = raw_asset_context(clients[compliance[0].label], "table", fqn)
        right = raw_asset_context(clients[engineer[0].label], "table", fqn)
        print_diff(left, right, compliance[0].persona, engineer[0].persona)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _require_env(name: str) -> str:
    """Return a required environment variable, or exit with guidance."""
    value = os.environ.get(name)
    if not value:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        print(
            "See the module docstring for the full list of required variables.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return value


def _load_identities() -> tuple[str, Identity, Identity]:
    """Read host + both tokens from the environment, or exit with guidance."""
    host = _require_env("AI_SDK_HOST")
    compliance = Identity(
        "David Kim", "ComplianceOfficer", _require_env("DEMO_COMPLIANCE_TOKEN")
    )
    engineer = Identity(
        "Sara Johnson", "DataEngineer", _require_env("DEMO_ENGINEER_TOKEN")
    )
    return host, compliance, engineer


def main() -> None:
    parser = argparse.ArgumentParser(description="Persona-aware Context demo")
    parser.add_argument(
        "--scene",
        choices=("persona", "asset", "all"),
        default="all",
        help="Which scene(s) to run (default: all).",
    )
    parser.add_argument(
        "--table",
        default=DEFAULT_TABLE,
        help=f"Table name for the RBAC scene (default: {DEFAULT_TABLE}).",
    )
    parser.add_argument(
        "--table-fqn",
        default=None,
        help="Explicit fully qualified name for the RBAC scene asset.",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("DEMO_MODEL", "openai:gpt-4o"),
        help="LangChain model id for the agent scenes (default: openai:gpt-4o).",
    )
    agent_group = parser.add_mutually_exclusive_group()
    agent_group.add_argument(
        "--agent",
        dest="agent",
        action="store_true",
        help="Run the LangChain agent answers (needs OPENAI_API_KEY).",
    )
    agent_group.add_argument(
        "--no-agent",
        dest="agent",
        action="store_false",
        help="Skip the agent; show only the deterministic raw-tool diff.",
    )
    parser.set_defaults(agent=True)
    parser.add_argument(
        "--no-raw",
        dest="raw",
        action="store_false",
        help="Skip the raw-tool diff; show only the agent answers.",
    )
    parser.set_defaults(raw=True)
    args = parser.parse_args()

    host, compliance_id, engineer_id = _load_identities()

    compliance_client = AISdk(host=host, token=compliance_id.token)
    engineer_client = AISdk(host=host, token=engineer_id.token)
    clients = {
        compliance_id.label: compliance_client,
        engineer_id.label: engineer_client,
    }

    try:
        compliance_agent = (
            build_agent(compliance_client, args.model) if args.agent else None
        )
        engineer_agent = (
            build_agent(engineer_client, args.model) if args.agent else None
        )
        compliance = (compliance_id, compliance_agent)
        engineer = (engineer_id, engineer_agent)

        if args.scene in ("persona", "all"):
            scene_persona(compliance, engineer, clients, args.agent, args.raw)
        if args.scene in ("asset", "all"):
            scene_asset(
                compliance,
                engineer,
                clients,
                args.table,
                args.table_fqn,
                args.agent,
                args.raw,
            )
    finally:
        compliance_client.close()
        engineer_client.close()


if __name__ == "__main__":
    main()
