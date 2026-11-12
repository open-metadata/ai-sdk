"""Models for MCP integration."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    from enum import Enum

    class StrEnum(str, Enum):
        """Backport of StrEnum for Python 3.10."""


class MCPTool(StrEnum):
    """Available MCP tools from OpenMetadata.

    Convenience names for the OpenMetadata and Collate 2.1 tools.
    Discovery and invocation also accept server-provided string names.
    """

    # Search & discovery
    SEARCH_METADATA = "search_metadata"
    SEMANTIC_SEARCH = "semantic_search"
    GET_ENTITY_DETAILS = "get_entity_details"
    GET_ENTITY_LINEAGE = "get_entity_lineage"

    GET_PERSONA_CONTEXT = "get_persona_context"
    GET_USER_CONTEXT = "get_user_context"
    FIND_CONTEXT = "find_context"
    GET_CONCEPT_CONTEXT = "get_concept_context"
    COMPANY_CONTEXT = "company_context"
    CREATE_ENTITY = "create_entity"
    DESCRIBE_ENTITY_TYPE = "describe_entity_type"
    CREATE_LINEAGE = "create_lineage"
    SPARQL_QUERY = "sparql_query"
    ENTITY_NEIGHBORHOOD = "entity_neighborhood"
    FIND_BY_TAG = "find_by_tag"
    SHACL_VALIDATE = "shacl_validate"
    ONTOLOGY_DESCRIBE = "ontology_describe"
    NLQ_SEARCH = "nlq_search"

    # Governance & data quality
    PATCH_ENTITY = "patch_entity"
    GET_TEST_DEFINITIONS = "get_test_definitions"
    CREATE_TEST_CASE = "create_test_case"
    ROOT_CAUSE_ANALYSIS = "root_cause_analysis"


@dataclass
class ToolInfo:
    """Metadata about an MCP tool."""

    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class ToolCallResult:
    """Result from calling an MCP tool."""

    success: bool
    data: dict | None
    error: str | None
