"""Models for MCP integration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MCPTool(StrEnum):
    """Available MCP tools from OpenMetadata."""

    SEARCH_METADATA = "search_metadata"
    GET_ENTITY_DETAILS = "get_entity_details"
    GET_ENTITY_LINEAGE = "get_entity_lineage"
    CREATE_GLOSSARY = "create_glossary"
    CREATE_GLOSSARY_TERM = "create_glossary_term"
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
