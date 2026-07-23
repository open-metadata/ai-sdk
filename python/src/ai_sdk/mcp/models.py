"""Models for MCP integration."""

from __future__ import annotations

import sys
from dataclasses import dataclass

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    from enum import Enum

    class StrEnum(str, Enum):
        """Backport of StrEnum for Python 3.10."""


class MCPTool(StrEnum):
    """Available MCP tools from OpenMetadata.

    Values mirror the tool names published by the OpenMetadata 2.0 MCP server
    (``openmetadata-mcp`` ``tools.json``). Unknown server tools are ignored by
    the client (see ``MCPClient._parse_tool_info``), so this enum is the
    allowlist the SDK exposes to LangChain / OpenAI adapters.
    """

    # Search & discovery
    SEARCH_METADATA = "search_metadata"
    SEMANTIC_SEARCH = "semantic_search"
    GET_ENTITY_DETAILS = "get_entity_details"
    GET_ENTITY_LINEAGE = "get_entity_lineage"

    # AI Context (Context Profiles) — 2.0
    GET_ASSET_CONTEXT = "get_asset_context"
    GET_PERSONA_CONTEXT = "get_persona_context"
    FIND_CONTEXT = "find_context"
    GET_KNOWLEDGE_CONTENT = "get_knowledge_content"

    # Company context — 2.0
    GET_COMPANY_CONTEXT = "get_company_context"
    SEARCH_COMPANY_CONTEXT = "search_company_context"

    # Authoring — 2.0
    CREATE_CLASSIFICATION = "create_classification"
    CREATE_TAG = "create_tag"
    CREATE_DOMAIN = "create_domain"
    CREATE_DATA_PRODUCT = "create_data_product"
    CREATE_METRIC = "create_metric"
    CREATE_CONTEXT_MEMORY = "create_context_memory"
    CREATE_GLOSSARY = "create_glossary"
    CREATE_GLOSSARY_TERM = "create_glossary_term"
    CREATE_LINEAGE = "create_lineage"

    # Governance & data quality
    PATCH_ENTITY = "patch_entity"
    GET_TEST_DEFINITIONS = "get_test_definitions"
    CREATE_TEST_CASE = "create_test_case"
    ROOT_CAUSE_ANALYSIS = "root_cause_analysis"


@dataclass
class ToolParameter:
    """Schema for a tool parameter."""

    name: str
    type: str  # "string", "integer", "boolean", "array", "object"
    description: str
    required: bool


@dataclass
class ToolInfo:
    """Metadata about an MCP tool."""

    name: MCPTool
    description: str
    parameters: list[ToolParameter]


@dataclass
class ToolCallResult:
    """Result from calling an MCP tool."""

    success: bool
    data: dict | None
    error: str | None
