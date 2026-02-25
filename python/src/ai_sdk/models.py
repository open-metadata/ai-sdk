"""Data models for the Metadata AI SDK.

This module uses Pydantic v2 for validation, serialization, and schema generation.
All models support both camelCase (API format) and snake_case (Python format).
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EventType(str, Enum):
    """Event types for streaming responses."""

    START = "start"
    CONTENT = "content"
    TOOL_USE = "tool_use"
    END = "end"
    ERROR = "error"


class InvokeRequest(BaseModel):
    """Request to invoke an agent."""

    model_config = ConfigDict(populate_by_name=True)

    message: str | None = Field(
        default=None,
        description="The message to send to the agent. Optional if the agent has a default prompt.",
    )
    conversation_id: str | None = Field(
        default=None,
        alias="conversationId",
        description="Optional conversation ID for multi-turn conversations",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional parameters to pass to the agent",
    )

    def to_api_dict(self) -> dict[str, Any]:
        """Convert to API request format (camelCase keys)."""
        d: dict[str, Any] = {}
        if self.message is not None:
            d["message"] = self.message
        if self.conversation_id:
            d["conversationId"] = self.conversation_id
        if self.parameters:
            d["parameters"] = self.parameters
        return d


class Usage(BaseModel):
    """Token usage statistics."""

    model_config = ConfigDict(populate_by_name=True)

    prompt_tokens: int = Field(
        default=0,
        alias="promptTokens",
        description="Number of tokens in the prompt",
    )
    completion_tokens: int = Field(
        default=0,
        alias="completionTokens",
        description="Number of tokens in the completion",
    )
    total_tokens: int = Field(
        default=0,
        alias="totalTokens",
        description="Total number of tokens used",
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Usage:
        """Create from API response format."""
        return cls.model_validate(data)


class InvokeResponse(BaseModel):
    """Response from invoking an agent."""

    model_config = ConfigDict(populate_by_name=True)

    conversation_id: str = Field(
        ...,
        alias="conversationId",
        description="The conversation ID for multi-turn conversations",
    )
    response: str = Field(..., description="The agent's response text")
    tools_used: list[str] = Field(
        default_factory=list,
        alias="toolsUsed",
        description="List of tools used by the agent",
    )
    usage: Usage | None = Field(
        default=None,
        description="Token usage statistics",
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InvokeResponse:
        """Create from API response format."""
        return cls.model_validate(data)


class StreamEvent(BaseModel):
    """Event from streaming agent response."""

    model_config = ConfigDict(populate_by_name=True)

    type: EventType = Field(..., description="Event type: start, content, tool_use, end, error")
    content: str | None = Field(default=None, description="Content for content events")
    tool_name: str | None = Field(
        default=None,
        alias="toolName",
        description="Tool name for tool_use events",
    )
    conversation_id: str | None = Field(
        default=None,
        alias="conversationId",
        description="Conversation ID",
    )
    error: str | None = Field(default=None, description="Error message for error events")

    @classmethod
    def from_sse(cls, event_type: str, data: dict[str, Any]) -> StreamEvent:
        """Create from SSE event data.

        Maps raw SSE event type strings to EventType enum values.
        Note: The fallback from 'message' to 'error' field is handled
        in SSEIterator._parse_event, not here.
        """
        type_mapping: dict[str, EventType] = {
            "stream-start": EventType.START,
            "message": EventType.CONTENT,
            "tool-use": EventType.TOOL_USE,
            "stream-completed": EventType.END,
            "error": EventType.ERROR,
            "fatal-error": EventType.ERROR,
        }
        mapped_type = type_mapping.get(event_type, EventType.CONTENT)

        return cls(
            type=mapped_type,
            content=data.get("content"),
            tool_name=data.get("toolName"),
            conversation_id=data.get("conversationId"),
            error=data.get("error"),
        )


class AgentInfo(BaseModel):
    """Agent metadata for SDK discovery."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., description="Agent name (identifier)")
    display_name: str | None = Field(
        default=None,
        alias="displayName",
        description="Human-readable display name",
    )
    description: str | None = Field(default=None, description="Agent description")
    abilities: list[str] = Field(
        default_factory=list,
        description="List of agent abilities/capabilities",
    )
    api_enabled: bool = Field(
        default=False,
        alias="apiEnabled",
        description="Whether the agent is enabled for API access",
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentInfo:
        """Create from API response format."""
        # Handle abilities that might be EntityReferences or strings
        abilities = data.get("abilities", [])
        if abilities and isinstance(abilities[0], dict):
            # Extract names from EntityReferences
            data = {**data, "abilities": [a.get("name", a.get("id", "")) for a in abilities]}
        return cls.model_validate(data)


class EntityReference(BaseModel):
    """A reference to another entity."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., description="Unique identifier of the referenced entity")
    type: str = Field(..., description="Type of the referenced entity")
    name: str | None = Field(default=None, description="Name of the referenced entity")
    display_name: str | None = Field(
        default=None,
        alias="displayName",
        description="Display name of the referenced entity",
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EntityReference:
        """Create from API response format."""
        return cls.model_validate(data)

    def to_api_dict(self) -> dict[str, Any]:
        """Convert to API request format (camelCase keys)."""
        d: dict[str, Any] = {"id": self.id, "type": self.type}
        if self.name is not None:
            d["name"] = self.name
        if self.display_name is not None:
            d["displayName"] = self.display_name
        return d


class BotInfo(BaseModel):
    """Represents a bot entity."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., description="Unique identifier of the bot")
    name: str = Field(..., description="Name of the bot")
    display_name: str | None = Field(
        default=None,
        alias="displayName",
        description="Human-readable display name",
    )
    description: str | None = Field(default=None, description="Description of the bot")
    bot_user: dict[str, Any] | None = Field(
        default=None,
        alias="botUser",
        description="Reference to the user this bot acts as",
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BotInfo:
        """Create from API response format."""
        return cls.model_validate(data)

    def to_api_dict(self) -> dict[str, Any]:
        """Convert to API request format (camelCase keys)."""
        d: dict[str, Any] = {"id": self.id, "name": self.name}
        if self.display_name is not None:
            d["displayName"] = self.display_name
        if self.description is not None:
            d["description"] = self.description
        if self.bot_user is not None:
            d["botUser"] = self.bot_user
        return d


class PersonaInfo(BaseModel):
    """Represents an AI Persona."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., description="Unique identifier of the persona")
    name: str = Field(..., description="Name of the persona")
    display_name: str | None = Field(
        default=None,
        alias="displayName",
        description="Human-readable display name",
    )
    description: str | None = Field(default=None, description="Description of the persona")
    prompt: str | None = Field(
        default=None, description="System prompt that defines the persona's behavior"
    )
    provider: str = Field(
        default="system",
        description="Provider of the persona (e.g., 'system' or 'user')",
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PersonaInfo:
        """Create from API response format."""
        return cls.model_validate(data)

    def to_api_dict(self) -> dict[str, Any]:
        """Convert to API request format (camelCase keys)."""
        d: dict[str, Any] = {"id": self.id, "name": self.name, "provider": self.provider}
        if self.display_name is not None:
            d["displayName"] = self.display_name
        if self.description is not None:
            d["description"] = self.description
        if self.prompt is not None:
            d["prompt"] = self.prompt
        return d


class KnowledgeScope(BaseModel):
    """Defines what data an agent can access."""

    model_config = ConfigDict(populate_by_name=True)

    entity_types: list[str] | None = Field(
        default=None,
        alias="entityTypes",
        description="List of entity types the agent can access",
    )
    services: list[EntityReference] | None = Field(
        default=None,
        description="List of services the agent can access",
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KnowledgeScope:
        """Create from API response format."""
        return cls.model_validate(data)

    def to_api_dict(self) -> dict[str, Any]:
        """Convert to API request format (camelCase keys)."""
        d: dict[str, Any] = {}
        if self.entity_types is not None:
            d["entityTypes"] = self.entity_types
        if self.services is not None:
            d["services"] = [s.to_api_dict() for s in self.services]
        return d


class CreatePersonaRequest(BaseModel):
    """Request to create a persona."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., description="Name of the persona")
    description: str = Field(..., description="Description of the persona")
    prompt: str = Field(..., description="System prompt that defines the persona's behavior")
    display_name: str | None = Field(
        default=None,
        alias="displayName",
        description="Human-readable display name",
    )
    provider: str = Field(
        default="user",
        description="Provider of the persona (e.g., 'system' or 'user')",
    )
    owners: list[EntityReference] | None = Field(
        default=None,
        description="List of owners for the persona",
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CreatePersonaRequest:
        """Create from API response format."""
        return cls.model_validate(data)

    def to_api_dict(self) -> dict[str, Any]:
        """Convert to API request format (camelCase keys)."""
        d: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "prompt": self.prompt,
            "provider": self.provider,
        }
        if self.display_name is not None:
            d["displayName"] = self.display_name
        if self.owners is not None:
            d["owners"] = [o.to_api_dict() for o in self.owners]
        return d


class CreateAgentRequest(BaseModel):
    """Request to create a dynamic agent."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., description="Name of the agent")
    description: str = Field(..., description="Description of the agent")
    persona: str = Field(..., description="Name of the persona to use")
    mode: str = Field(..., description="Agent mode: 'chat', 'agent', or 'both'")
    display_name: str | None = Field(
        default=None,
        alias="displayName",
        description="Human-readable display name",
    )
    icon: str | None = Field(default=None, description="Icon for the agent")
    bot_name: str | None = Field(
        default=None,
        alias="botName",
        description="Name of the bot that executes this agent",
    )
    abilities: list[str] | None = Field(
        default=None,
        description="List of abilities/capabilities for the agent",
    )
    knowledge: KnowledgeScope | None = Field(
        default=None,
        description="Knowledge scope defining what data the agent can access",
    )
    prompt: str | None = Field(default=None, description="Workflow definition for the agent")
    schedule: str | None = Field(
        default=None, description="Cron expression for scheduled execution"
    )
    api_enabled: bool = Field(
        default=False,
        alias="apiEnabled",
        description="Whether the agent is enabled for API access",
    )
    provider: str = Field(
        default="user",
        description="Provider of the agent (e.g., 'system' or 'user')",
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CreateAgentRequest:
        """Create from API response format."""
        return cls.model_validate(data)

    def to_api_dict(self) -> dict[str, Any]:
        """Convert to API request format (camelCase keys)."""
        d: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "persona": {"name": self.persona, "type": "persona"},  # EntityReference format
            "mode": self.mode,
            "apiEnabled": self.api_enabled,
            "provider": self.provider,
        }
        if self.display_name is not None:
            d["displayName"] = self.display_name
        if self.icon is not None:
            d["icon"] = self.icon
        if self.bot_name is not None:
            d["botName"] = self.bot_name
        if self.abilities is not None:
            d["abilities"] = self.abilities
        if self.knowledge is not None:
            d["knowledge"] = self.knowledge.to_api_dict()
        if self.prompt is not None:
            d["prompt"] = self.prompt
        if self.schedule is not None:
            d["schedule"] = self.schedule
        return d


class AbilityInfo(BaseModel):
    """Represents an Ability."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., description="Unique identifier of the ability")
    name: str = Field(..., description="Name of the ability")
    display_name: str | None = Field(
        default=None,
        alias="displayName",
        description="Human-readable display name",
    )
    description: str | None = Field(default=None, description="Description of the ability")
    provider: str | None = Field(
        default=None,
        description="Provider of the ability (e.g., 'system' or 'user')",
    )
    fully_qualified_name: str | None = Field(
        default=None,
        alias="fullyQualifiedName",
        description="Fully qualified name of the ability",
    )
    tools: list[str] = Field(
        default_factory=list,
        description="List of tools provided by this ability",
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AbilityInfo:
        """Create from API response format."""
        return cls.model_validate(data)

    def to_api_dict(self) -> dict[str, Any]:
        """Convert to API request format (camelCase keys)."""
        d: dict[str, Any] = {"id": self.id, "name": self.name, "tools": self.tools}
        if self.display_name is not None:
            d["displayName"] = self.display_name
        if self.description is not None:
            d["description"] = self.description
        if self.provider is not None:
            d["provider"] = self.provider
        if self.fully_qualified_name is not None:
            d["fullyQualifiedName"] = self.fully_qualified_name
        return d
