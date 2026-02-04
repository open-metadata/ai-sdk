"""Agent handle for the Metadata AI SDK."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable
from typing import Any

from metadata_ai._http import AsyncHTTPClient, HTTPClient
from metadata_ai._logging import debug as _log_debug
from metadata_ai._streaming import AsyncSSEIterator, SSEIterator
from metadata_ai.models import AgentInfo, InvokeRequest, InvokeResponse, StreamEvent


def _debug(msg: str) -> None:
    """Print debug message if debug is enabled."""
    _log_debug("AGENT DEBUG", msg)


class AgentHandle:
    """
    Handle for invoking a specific agent.

    Usage:
        agent = client.agent("DataQualityPlannerAgent")

        # Synchronous call
        response = agent.call("What tables have issues?")
        print(response.response)

        # Streaming call
        for event in agent.stream("What tables have issues?"):
            if event.type == "content":
                print(event.content, end="", flush=True)
    """

    def __init__(
        self,
        name: str,
        http: HTTPClient,
        async_http: AsyncHTTPClient | None = None,
    ):
        """
        Initialize the agent handle.

        Args:
            name: The agent name
            http: HTTP client for API communication
            async_http: Optional async HTTP client for async operations
        """
        self._name = name
        self._http = http
        self._async_http = async_http

    @property
    def name(self) -> str:
        """Get the agent name."""
        return self._name

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

        Raises:
            AgentNotFoundError: If the agent does not exist
            AgentNotEnabledError: If the agent is not API-enabled
            AuthenticationError: If the token is invalid
            AgentExecutionError: If the agent execution fails
        """
        _debug("=== AgentHandle.call() START ===")
        _debug(f"Agent: {self._name}")
        _debug(f"Message: {message}")
        _debug(f"Conversation ID: {conversation_id}")

        request = InvokeRequest(
            message=message,
            conversation_id=conversation_id,
            parameters=parameters or {},
        )
        _debug(f"Request dict: {request.to_api_dict()}")

        data = self._http.post(
            f"/{self._name}/invoke",
            json=request.to_api_dict(),
            agent_name=self._name,
        )

        _debug(f"Raw API response data: {data}")

        response = InvokeResponse.from_dict(data)
        _debug(f"Parsed response.response: {response.response}")
        _debug(f"Parsed response.tools_used: {response.tools_used}")
        _debug("=== AgentHandle.call() END ===")

        return response

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

        Raises:
            AgentNotFoundError: If the agent does not exist
            AgentNotEnabledError: If the agent is not API-enabled
            AuthenticationError: If the token is invalid
            AgentExecutionError: If the agent execution fails
            RuntimeError: If async client is not available
        """
        if self._async_http is None:
            raise RuntimeError(
                "Async HTTP client not available. "
                "Use MetadataAI with enable_async=True for async operations."
            )

        request = InvokeRequest(
            message=message,
            conversation_id=conversation_id,
            parameters=parameters or {},
        )
        data = await self._async_http.post(
            f"/{self._name}/invoke",
            json=request.to_api_dict(),
            agent_name=self._name,
        )
        return InvokeResponse.from_dict(data)

    def stream(
        self,
        message: str | None = None,
        *,
        conversation_id: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> Iterable[StreamEvent]:
        """
        Invoke the agent with streaming response.

        Args:
            message: The query or instruction for the agent. Optional if the agent
                has a default prompt configured.
            conversation_id: Optional ID for multi-turn conversations
            parameters: Optional parameters to pass to the agent

        Yields:
            StreamEvent objects as they arrive

        Raises:
            AgentNotFoundError: If the agent does not exist
            AgentNotEnabledError: If the agent is not API-enabled
            AuthenticationError: If the token is invalid
            AgentExecutionError: If the agent execution fails
        """
        request = InvokeRequest(
            message=message,
            conversation_id=conversation_id,
            parameters=parameters or {},
        )
        byte_stream = self._http.post_stream(
            f"/{self._name}/stream",
            json=request.to_api_dict(),
            agent_name=self._name,
        )
        return SSEIterator(byte_stream)

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

        Raises:
            AgentNotFoundError: If the agent does not exist
            AgentNotEnabledError: If the agent is not API-enabled
            AuthenticationError: If the token is invalid
            AgentExecutionError: If the agent execution fails
            RuntimeError: If async client is not available
        """
        if self._async_http is None:
            raise RuntimeError(
                "Async HTTP client not available. "
                "Use MetadataAI with enable_async=True for async operations."
            )

        request = InvokeRequest(
            message=message,
            conversation_id=conversation_id,
            parameters=parameters or {},
        )
        byte_stream = self._async_http.post_stream(
            f"/{self._name}/stream",
            json=request.to_api_dict(),
            agent_name=self._name,
        )
        return AsyncSSEIterator(byte_stream)

    def get_info(self) -> AgentInfo:
        """
        Get agent metadata including abilities and description.

        Returns:
            AgentInfo with agent metadata

        Raises:
            AgentNotFoundError: If the agent does not exist
            AgentNotEnabledError: If the agent is not API-enabled
        """
        data = self._http.get(f"/{self._name}", agent_name=self._name)
        return AgentInfo.from_dict(data)

    async def aget_info(self) -> AgentInfo:
        """
        Get agent metadata asynchronously.

        Returns:
            AgentInfo with agent metadata

        Raises:
            AgentNotFoundError: If the agent does not exist
            AgentNotEnabledError: If the agent is not API-enabled
            RuntimeError: If async client is not available
        """
        if self._async_http is None:
            raise RuntimeError(
                "Async HTTP client not available. "
                "Use MetadataAI with enable_async=True for async operations."
            )

        data = await self._async_http.get(f"/{self._name}", agent_name=self._name)
        return AgentInfo.from_dict(data)

    def __repr__(self) -> str:
        return f"AgentHandle(name={self._name!r})"
