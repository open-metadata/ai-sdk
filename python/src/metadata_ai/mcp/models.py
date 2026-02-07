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
    """Available MCP tools from OpenMetadata."""

    SEARCH_METADATA = "search_metadata"
    GET_ENTITY_DETAILS = "get_entity_details"
    GET_ENTITY_LINEAGE = "get_entity_lineage"
    CREATE_GLOSSARY = "create_glossary"
    CREATE_GLOSSARY_TERM = "create_glossary_term"
    CREATE_LINEAGE = "create_lineage"
    PATCH_ENTITY = "patch_entity"


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
