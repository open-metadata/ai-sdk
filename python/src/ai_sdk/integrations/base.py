"""Base classes for framework integrations.

This module provides the foundation for integrating Metadata agents
with various AI frameworks (LangChain, LlamaIndex, CrewAI, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ai_sdk.agent import AgentHandle
from ai_sdk.client import MetadataAI
from ai_sdk.exceptions import MetadataError
from ai_sdk.models import AgentInfo


class BaseAgentWrapper(ABC):
    """
    Base class for all framework integrations.

    Provides common functionality for wrapping Metadata agents:
    - Agent info fetching with fallback
    - Description building from abilities
    - Conversation ID management
    - Sync and async invocation

    Subclasses only need to implement framework-specific details.

    Example:
        class MyFrameworkTool(BaseAgentWrapper):
            def _default_name(self, info: AgentInfo) -> str:
                return f"myframework_{info.name}"

            # Implement framework-specific interface methods
    """

    def __init__(
        self,
        agent_handle: AgentHandle,
        name: str | None = None,
        description: str | None = None,
    ):
        """
        Initialize the wrapper.

        Args:
            agent_handle: AgentHandle from MetadataAI client
            name: Optional custom name (defaults to framework-specific naming)
            description: Optional custom description (defaults to agent info)
        """
        self._agent_handle = agent_handle
        self._conversation_id: str | None = None
        self._agent_info: AgentInfo | None = None

        # Try to get agent info, use fallback if not available
        self._agent_info = self._fetch_agent_info_safe()

        if self._agent_info is not None:
            self._name = name or self._default_name(self._agent_info)
            self._description = description or self._build_description(self._agent_info)
        else:
            self._name = name or f"metadata_{agent_handle.name}"
            self._description = description or f"Invoke Metadata agent: {agent_handle.name}"

    def _fetch_agent_info_safe(self) -> AgentInfo | None:
        """
        Fetch agent info with graceful fallback.

        Returns:
            AgentInfo if available, None otherwise
        """
        try:
            return self._agent_handle.get_info()
        except MetadataError:
            # Agent not found, not enabled, or network error
            return None

    @classmethod
    def from_client(
        cls,
        client: MetadataAI,
        agent_name: str,
        name: str | None = None,
        description: str | None = None,
        **kwargs: Any,
    ) -> BaseAgentWrapper:
        """
        Create wrapper from MetadataAI client and agent name.

        Args:
            client: MetadataAI client instance
            agent_name: Name of the agent to wrap
            name: Optional custom name
            description: Optional custom description
            **kwargs: Additional framework-specific arguments

        Returns:
            Wrapper instance
        """
        return cls(
            agent_handle=client.agent(agent_name),
            name=name,
            description=description,
            **kwargs,
        )

    @classmethod
    def from_agent(
        cls,
        agent_handle: AgentHandle,
        name: str | None = None,
        description: str | None = None,
        **kwargs: Any,
    ) -> BaseAgentWrapper:
        """
        Create wrapper from an existing AgentHandle.

        Args:
            agent_handle: AgentHandle instance
            name: Optional custom name
            description: Optional custom description
            **kwargs: Additional framework-specific arguments

        Returns:
            Wrapper instance
        """
        return cls(
            agent_handle=agent_handle,
            name=name,
            description=description,
            **kwargs,
        )

    @abstractmethod
    def _default_name(self, info: AgentInfo) -> str:
        """
        Return the default tool name for this framework.

        Args:
            info: Agent metadata

        Returns:
            Default name string
        """
        ...

    def _build_description(self, info: AgentInfo) -> str:
        """
        Build tool description from agent info.

        Args:
            info: Agent metadata

        Returns:
            Description string including abilities
        """
        abilities_str = ", ".join(info.abilities) if info.abilities else "general"
        base_desc = info.description or f"Metadata agent: {info.display_name}"
        return f"{base_desc} Capabilities: {abilities_str}."

    @property
    def name(self) -> str:
        """Get the tool name."""
        return self._name

    @property
    def description(self) -> str:
        """Get the tool description."""
        return self._description

    @property
    def agent_info(self) -> AgentInfo | None:
        """Get the cached agent info, if available."""
        return self._agent_info

    @property
    def conversation_id(self) -> str | None:
        """Get the current conversation ID."""
        return self._conversation_id

    def invoke(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> str:
        """
        Invoke the agent synchronously and return response string.

        Args:
            query: The message/query for the agent
            parameters: Optional additional parameters

        Returns:
            Agent response as string
        """
        response = self._agent_handle.call(
            message=query,
            conversation_id=self._conversation_id,
            parameters=parameters,
        )
        self._conversation_id = response.conversation_id
        return response.response

    async def ainvoke(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> str:
        """
        Invoke the agent asynchronously and return response string.

        Args:
            query: The message/query for the agent
            parameters: Optional additional parameters

        Returns:
            Agent response as string

        Raises:
            RuntimeError: If async client is not available
        """
        response = await self._agent_handle.acall(
            message=query,
            conversation_id=self._conversation_id,
            parameters=parameters,
        )
        self._conversation_id = response.conversation_id
        return response.response

    def reset_conversation(self) -> None:
        """Reset conversation context for fresh interactions."""
        self._conversation_id = None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self._name!r})"
