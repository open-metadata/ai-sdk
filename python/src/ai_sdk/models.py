"""Data models for the Metadata AI SDK.

This module uses Pydantic v2 for validation, serialization, and schema generation.
All models support both camelCase (API format) and snake_case (Python format).
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class EventType(str, Enum):
    """Event types for streaming responses."""

    START = "start"
    CONTENT = "content"
    TOOL_USE = "tool_use"
    END = "end"
    ERROR = "error"


class InvokeRequest(BaseModel):
    """Request to invoke an agent."""

    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True)

    message: str | None = Field(
        default=None,
        description="The message to send to the agent. Optional if the agent has a default prompt.",
    )
    conversation_id: str | None = Field(
        default=None,
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

    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True)

    prompt_tokens: int = Field(
        default=0,
        description="Number of tokens in the prompt",
    )
    completion_tokens: int = Field(
        default=0,
        description="Number of tokens in the completion",
    )
    total_tokens: int = Field(
        default=0,
        description="Total number of tokens used",
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Usage:
        """Create from API response format."""
        return cls.model_validate(data)


class InvokeResponse(BaseModel):
    """Response from invoking an agent."""

    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True)

    conversation_id: str = Field(
        ...,
        description="The conversation ID for multi-turn conversations",
    )
    response: str = Field(..., description="The agent's response text")
    tools_used: list[str] = Field(
        default_factory=list,
        description="List of tools used by the agent",
    )
    thinking_steps: list[str] = Field(
        default_factory=list,
        description="Intermediate reasoning steps emitted by the agent (Sender.SYSTEM messages)",
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

    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True)

    type: EventType = Field(..., description="Event type: start, content, tool_use, end, error")
    content: str | None = Field(default=None, description="Content for content events")
    tool_name: str | None = Field(
        default=None,
        description="Tool name for tool_use events",
    )
    conversation_id: str | None = Field(
        default=None,
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

    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True)

    name: str = Field(..., description="Agent name (identifier)")
    display_name: str | None = Field(
        default=None,
        description="Human-readable display name",
    )
    description: str | None = Field(default=None, description="Agent description")
    abilities: list[str] = Field(
        default_factory=list,
        description="List of agent abilities/capabilities",
    )
    api_enabled: bool = Field(
        default=False,
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

    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True)

    id: str = Field(..., description="Unique identifier of the referenced entity")
    type: str = Field(..., description="Type of the referenced entity")
    name: str | None = Field(default=None, description="Name of the referenced entity")
    display_name: str | None = Field(
        default=None,
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

    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True)

    id: str = Field(..., description="Unique identifier of the bot")
    name: str = Field(..., description="Name of the bot")
    display_name: str | None = Field(
        default=None,
        description="Human-readable display name",
    )
    description: str | None = Field(default=None, description="Description of the bot")
    bot_user: dict[str, Any] | None = Field(
        default=None,
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

    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True)

    id: str = Field(..., description="Unique identifier of the persona")
    name: str = Field(..., description="Name of the persona")
    display_name: str | None = Field(
        default=None,
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

    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True)

    entity_types: list[str] | None = Field(
        default=None,
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

    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True)

    name: str = Field(..., description="Name of the persona")
    description: str = Field(..., description="Description of the persona")
    prompt: str = Field(..., description="System prompt that defines the persona's behavior")
    display_name: str | None = Field(
        default=None,
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

    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True)

    name: str = Field(..., description="Name of the agent")
    description: str = Field(..., description="Description of the agent")
    persona: str = Field(..., description="Name of the persona to use")
    mode: str = Field(..., description="Agent mode: 'chat', 'agent', or 'both'")
    display_name: str | None = Field(
        default=None,
        description="Human-readable display name",
    )
    icon: str | None = Field(default=None, description="Icon for the agent")
    bot_name: str | None = Field(
        default=None,
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


class MemoryType(str, Enum):
    """High-level type of reusable memory."""

    PREFERENCE = "Preference"
    USE_CASE = "UseCase"
    NOTE = "Note"
    RUNBOOK = "Runbook"
    FAQ = "Faq"


class MemoryScope(str, Enum):
    """Scope where the memory applies."""

    USER_GLOBAL = "UserGlobal"
    ENTITY_SCOPED = "EntityScoped"


class MemoryVisibility(str, Enum):
    """Visibility level for a memory."""

    PRIVATE = "Private"
    ENTITY = "Entity"
    SHARED = "Shared"


class CreateContextMemoryRequest(BaseModel):
    """Request to create a Context Center memory."""

    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True)

    name: str = Field(..., description="Stable system name for the memory")
    question: str = Field(..., description="Canonical question / instruction")
    answer: str = Field(..., description="Canonical answer / retained guidance")
    title: str | None = Field(default=None, description="Short title shown in Context Center")
    description: str | None = Field(default=None, description="Optional markdown description")
    memory_type: MemoryType = Field(
        default=MemoryType.NOTE,
        description="High-level memory type",
    )
    memory_scope: MemoryScope = Field(
        default=MemoryScope.ENTITY_SCOPED,
        description="Scope the memory applies to",
    )
    visibility: MemoryVisibility = Field(
        default=MemoryVisibility.PRIVATE,
        description="Visibility level (Private/Entity/Shared)",
    )
    primary_entity: EntityReference | None = Field(
        default=None,
        description="Primary entity this memory attaches to",
    )
    related_entities: list[EntityReference] | None = Field(
        default=None,
        description="Additional related entities",
    )
    tags: list[str] | None = Field(
        default=None,
        description="Tag FQN strings; wrapped to TagLabel on the wire",
    )

    def to_api_dict(self) -> dict[str, Any]:
        """Convert to API request format (camelCase keys)."""
        d: dict[str, Any] = {
            "name": self.name,
            "question": self.question,
            "answer": self.answer,
            "memoryType": self.memory_type.value,
            "memoryScope": self.memory_scope.value,
            "shareConfig": {"visibility": self.visibility.value},
        }
        if self.title is not None:
            d["title"] = self.title
        if self.description is not None:
            d["description"] = self.description
        if self.primary_entity is not None:
            d["primaryEntity"] = self.primary_entity.to_api_dict()
        if self.related_entities is not None:
            d["relatedEntities"] = [e.to_api_dict() for e in self.related_entities]
        if self.tags is not None:
            d["tags"] = [
                {
                    "tagFQN": t,
                    "labelType": "Manual",
                    "state": "Confirmed",
                    "source": "Classification",
                }
                for t in self.tags
            ]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CreateContextMemoryRequest:
        """Create from API request format."""
        return cls.model_validate(data)


class ContextMemory(BaseModel):
    """A Context Center memory."""

    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True)

    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Stable system name")
    fully_qualified_name: str | None = Field(
        default=None,
        description="Fully qualified name",
    )
    title: str | None = Field(default=None, description="Short title")
    question: str = Field(default="", description="Canonical question / instruction")
    answer: str = Field(default="", description="Canonical answer / retained guidance")
    summary: str | None = Field(default=None, description="Optional summary")
    memory_type: MemoryType = Field(default=MemoryType.NOTE)
    memory_scope: MemoryScope = Field(default=MemoryScope.ENTITY_SCOPED)
    visibility: MemoryVisibility = Field(
        default=MemoryVisibility.PRIVATE,
        description="Visibility (extracted from shareConfig.visibility)",
    )
    primary_entity: EntityReference | None = Field(default=None)
    usage_count: int = Field(default=0)
    last_used_at: int | None = Field(
        default=None,
        description="Last-used timestamp in epoch milliseconds",
    )
    deleted: bool = Field(default=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContextMemory:
        """Create from API response format. Flattens shareConfig.visibility."""
        share_config = data.get("shareConfig") or {}
        if isinstance(share_config, dict):
            visibility = share_config.get("visibility", "Private")
        else:
            visibility = "Private"
        flattened = {**data, "visibility": visibility}
        return cls.model_validate(flattened)


class MemorySearchHit(BaseModel):
    """A single hit from a hybrid memory search."""

    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True)

    memory: ContextMemory = Field(..., description="The matched memory")
    score: float = Field(..., description="Relevance score from the search engine")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemorySearchHit:
        """Create from an OpenSearch hit."""
        return cls(
            memory=ContextMemory.from_dict(data.get("_source", {})),
            score=float(data.get("_score", 0.0)),
        )


class MemorySearchResults(BaseModel):
    """Results from a hybrid memory search."""

    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True)

    total: int = Field(default=0, description="Total number of matching memories")
    hits: list[MemorySearchHit] = Field(
        default_factory=list,
        description="Ranked search hits",
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemorySearchResults:
        """Create from an OpenSearch response shape."""
        hits_block = data.get("hits") or {}
        total_block = hits_block.get("total", 0)
        if isinstance(total_block, dict):
            total = int(total_block.get("value", 0))
        else:
            total = int(total_block)
        raw_hits = hits_block.get("hits") or []
        return cls(
            total=total,
            hits=[MemorySearchHit.from_dict(h) for h in raw_hits],
        )


class AbilityInfo(BaseModel):
    """Represents an Ability."""

    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True)

    id: str = Field(..., description="Unique identifier of the ability")
    name: str = Field(..., description="Name of the ability")
    display_name: str | None = Field(
        default=None,
        description="Human-readable display name",
    )
    description: str | None = Field(default=None, description="Description of the ability")
    provider: str | None = Field(
        default=None,
        description="Provider of the ability (e.g., 'system' or 'user')",
    )
    fully_qualified_name: str | None = Field(
        default=None,
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
