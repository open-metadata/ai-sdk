"""Abstract base classes for the Metadata AI SDK.

This module provides ABC classes that enable:
- Type-safe mocking in tests
- Custom implementations of core interfaces
- Dependency injection patterns

Example:
    from metadata_ai.protocols import AgentBase

    class MockAgent(AgentBase):
        '''Mock agent for testing.'''

        def __init__(self, responses: list[str]):
            self._responses = iter(responses)
            self._name = "MockAgent"

        @property
        def name(self) -> str:
            return self._name

        def call(self, message: str, **kwargs) -> InvokeResponse:
            return InvokeResponse(
                conversation_id="mock-123",
                response=next(self._responses),
                tools_used=[],
            )

        # ... implement other abstract methods

    # Use in tests
    def test_my_code(mock_agent: AgentBase):
        result = my_function_that_uses_agent(mock_agent)
        assert result == expected
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from metadata_ai.models import AgentInfo, InvokeResponse, StreamEvent


class AgentProtocol(ABC):
    """
    Abstract base class for agent invocation.

    This ABC defines the interface that any agent implementation must satisfy.
    Use this for type hints when you want to accept any agent-like object,
    including mocks for testing.

    Example:
        def analyze_data(agent: AgentProtocol, query: str) -> str:
            response = agent.call(query)
            return response.response
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the agent name."""
        ...

    @abstractmethod
    def call(
        self,
        message: str | None = None,
        *,
        conversation_id: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> InvokeResponse:
        """
        Invoke the agent synchronously.

        Args:
            message: The query or instruction for the agent. Optional if the agent
                has a default prompt configured.
            conversation_id: Optional ID for multi-turn conversations
            parameters: Optional parameters to pass to the agent

        Returns:
            InvokeResponse with the complete response
        """
        ...

    @abstractmethod
    async def acall(
        self,
        message: str | None = None,
        *,
        conversation_id: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> InvokeResponse:
        """
        Invoke the agent asynchronously.

        Args:
            message: The query or instruction for the agent. Optional if the agent
                has a default prompt configured.
            conversation_id: Optional ID for multi-turn conversations
            parameters: Optional parameters to pass to the agent

        Returns:
            InvokeResponse with the complete response
        """
        ...

    @abstractmethod
    def stream(
        self,
        message: str | None = None,
        *,
        conversation_id: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> Iterator[StreamEvent]:
        """
        Invoke the agent with streaming response.

        Args:
            message: The query or instruction for the agent. Optional if the agent
                has a default prompt configured.
            conversation_id: Optional ID for multi-turn conversations
            parameters: Optional parameters to pass to the agent

        Yields:
            StreamEvent objects as they arrive
        """
        ...

    @abstractmethod
    def astream(
        self,
        message: str | None = None,
        *,
        conversation_id: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """
        Invoke the agent with async streaming response.

        Args:
            message: The query or instruction for the agent. Optional if the agent
                has a default prompt configured.
            conversation_id: Optional ID for multi-turn conversations
            parameters: Optional parameters to pass to the agent

        Yields:
            StreamEvent objects as they arrive
        """
        ...

    @abstractmethod
    def get_info(self) -> AgentInfo:
        """
        Get agent metadata including abilities and description.

        Returns:
            AgentInfo with agent metadata
        """
        ...

    @abstractmethod
    async def aget_info(self) -> AgentInfo:
        """
        Get agent metadata asynchronously.

        Returns:
            AgentInfo with agent metadata
        """
        ...


class HTTPClientProtocol(ABC):
    """
    Abstract base class for HTTP client operations.

    Use this for mocking HTTP operations in tests without hitting real endpoints.
    """

    @abstractmethod
    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        agent_name: str | None = None,
    ) -> dict[str, Any]:
        """Make a GET request."""
        ...

    @abstractmethod
    def post(
        self,
        path: str,
        json: dict[str, Any],
        agent_name: str | None = None,
    ) -> dict[str, Any]:
        """Make a POST request."""
        ...

    @abstractmethod
    def post_stream(
        self,
        path: str,
        json: dict[str, Any],
        agent_name: str | None = None,
    ) -> Iterator[bytes]:
        """Make a streaming POST request."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Close the HTTP client."""
        ...


class AsyncHTTPClientProtocol(ABC):
    """Abstract base class for async HTTP client operations."""

    @abstractmethod
    async def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        agent_name: str | None = None,
    ) -> dict[str, Any]:
        """Make an async GET request."""
        ...

    @abstractmethod
    async def post(
        self,
        path: str,
        json: dict[str, Any],
        agent_name: str | None = None,
    ) -> dict[str, Any]:
        """Make an async POST request."""
        ...

    @abstractmethod
    async def post_stream(
        self,
        path: str,
        json: dict[str, Any],
        agent_name: str | None = None,
    ) -> AsyncIterator[bytes]:
        """Make an async streaming POST request."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the async HTTP client."""
        ...
