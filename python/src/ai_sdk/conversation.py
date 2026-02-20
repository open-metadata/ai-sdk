"""Conversation management for the AI SDK.

This module provides a high-level interface for managing multi-turn
conversations with agents without requiring external frameworks.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable
from typing import Any

from ai_sdk.agent import AgentHandle
from ai_sdk.models import InvokeResponse, StreamEvent


class Conversation:
    """
    Manages a multi-turn conversation with an agent.

    This class provides a simple, self-contained way to interact with
    agents without needing LangChain or other frameworks.

    Usage:
        from ai_sdk.client import AiSdk
        from ai_sdk.conversation import Conversation

        client = AiSdk(host="...", token="...")
        agent = client.agent("DataQualityPlannerAgent")

        # Create a conversation
        conv = Conversation(agent)

        # Send messages and maintain context automatically
        response1 = conv.send("Analyze the customers table")
        print(response1)

        response2 = conv.send("Now create tests for the issues you found")
        print(response2)

        # Access conversation history
        for user_msg, assistant_msg in conv.history:
            print(f"User: {user_msg}")
            print(f"Assistant: {assistant_msg}")

        # Start fresh
        conv.reset()
    """

    def __init__(self, agent: AgentHandle):
        """
        Initialize a conversation with an agent.

        Args:
            agent: AgentHandle from AiSdk.agent()
        """
        self._agent = agent
        self._conversation_id: str | None = None
        self._history: list[tuple[str, str]] = []
        self._responses: list[InvokeResponse] = []

    @property
    def agent(self) -> AgentHandle:
        """Get the agent handle."""
        return self._agent

    @property
    def id(self) -> str | None:
        """Get the current conversation ID."""
        return self._conversation_id

    @property
    def history(self) -> list[tuple[str, str]]:
        """
        Get conversation history as (user_message, assistant_response) pairs.

        Returns:
            List of (user, assistant) message tuples
        """
        return self._history.copy()

    @property
    def messages(self) -> list[dict[str, str]]:
        """
        Get conversation history in chat message format.

        Returns:
            List of message dicts with 'role' and 'content' keys
        """
        messages = []
        for user_msg, assistant_msg in self._history:
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": assistant_msg})
        return messages

    @property
    def responses(self) -> list[InvokeResponse]:
        """
        Get all raw InvokeResponse objects from this conversation.

        Returns:
            List of InvokeResponse objects
        """
        return self._responses.copy()

    @property
    def tools_used(self) -> list[str]:
        """
        Get all tools used across the conversation.

        Returns:
            List of unique tool names used
        """
        tools = set()
        for response in self._responses:
            tools.update(response.tools_used)
        return sorted(tools)

    def send(
        self,
        message: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> str:
        """
        Send a message and get the response.

        The conversation context is automatically maintained.

        Args:
            message: The message to send. Optional if the agent has a default prompt.
            parameters: Optional additional parameters

        Returns:
            The agent's response text
        """
        response = self._agent.call(
            message=message,
            conversation_id=self._conversation_id,
            parameters=parameters,
        )

        self._conversation_id = response.conversation_id
        # Only add to history if message was provided
        if message is not None:
            self._history.append((message, response.response))
        self._responses.append(response)

        return response.response

    async def asend(
        self,
        message: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> str:
        """
        Send a message asynchronously and get the response.

        Args:
            message: The message to send. Optional if the agent has a default prompt.
            parameters: Optional additional parameters

        Returns:
            The agent's response text

        Raises:
            RuntimeError: If async client is not available
        """
        response = await self._agent.acall(
            message=message,
            conversation_id=self._conversation_id,
            parameters=parameters,
        )

        self._conversation_id = response.conversation_id
        # Only add to history if message was provided
        if message is not None:
            self._history.append((message, response.response))
        self._responses.append(response)

        return response.response

    def stream(
        self,
        message: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> Iterable[StreamEvent]:
        """
        Send a message and stream the response.

        Note: Streaming responses are not added to history automatically.
        Use send() for conversations that need to maintain history.

        Args:
            message: The message to send. Optional if the agent has a default prompt.
            parameters: Optional additional parameters

        Yields:
            StreamEvent objects as they arrive
        """
        return self._agent.stream(
            message=message,
            conversation_id=self._conversation_id,
            parameters=parameters,
        )

    def astream(
        self,
        message: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """
        Send a message and stream the response asynchronously.

        Args:
            message: The message to send. Optional if the agent has a default prompt.
            parameters: Optional additional parameters

        Yields:
            StreamEvent objects as they arrive

        Raises:
            RuntimeError: If async client is not available
        """
        return self._agent.astream(
            message=message,
            conversation_id=self._conversation_id,
            parameters=parameters,
        )

    def reset(self) -> None:
        """
        Reset the conversation to start fresh.

        Clears conversation ID and history.
        """
        self._conversation_id = None
        self._history = []
        self._responses = []

    def __len__(self) -> int:
        """Get the number of turns in the conversation."""
        return len(self._history)

    def __repr__(self) -> str:
        return (
            f"Conversation(agent={self._agent.name!r}, "
            f"turns={len(self._history)}, "
            f"id={self._conversation_id!r})"
        )
