"""Default-agent handle — invokes the platform's default agent (PLANNER/CHAT_MODE).

The chat UI's flow is mirrored: when no conversation_id is supplied, the SDK
creates one via POST /api/v1/assistants/chatConversations, then calls
/v1/agents/invoke (sync) or /v1/agents/run (SSE).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable
from typing import Any

from ai_sdk._http import AsyncHTTPClient, HTTPClient
from ai_sdk._streaming import AsyncSSEIterator, SSEIterator
from ai_sdk.agent import AgentHandle
from ai_sdk.models import EventType, InvokeResponse, StreamEvent

DEFAULT_AGENT_TYPE = "PLANNER"
DEFAULT_AGENT_MODE = "CHAT_MODE"
_TITLE_MAX_LEN = 50


class DefaultAgentHandle(AgentHandle):
    """Handle for the platform's default agent.

    Auto-creates a chat conversation when none is supplied, then calls
    /v1/agents/invoke (sync) or /v1/agents/run (SSE) with agentType=PLANNER,
    agentMode=CHAT_MODE.
    """

    def __init__(
        self,
        chat_http: HTTPClient,
        chat_async_http: AsyncHTTPClient | None,
        default_http: HTTPClient,
        default_async_http: AsyncHTTPClient | None,
    ):
        # Bypass AgentHandle.__init__ — no agent name involved.
        self._name = "<default>"
        self._http = default_http
        self._async_http = default_async_http
        self._chat_http = chat_http
        self._chat_async_http = chat_async_http

    def _create_conversation(self, title: str) -> str:
        body = {"title": title[:_TITLE_MAX_LEN]}
        data = self._chat_http.post("/chatConversations", json=body)
        return data["id"]

    async def _acreate_conversation(self, title: str) -> str:
        if self._chat_async_http is None:
            raise RuntimeError(
                "Async HTTP client not available. "
                "Use AISdk with enable_async=True for async operations."
            )
        body = {"title": title[:_TITLE_MAX_LEN]}
        data = await self._chat_async_http.post("/chatConversations", json=body)
        return data["id"]

    def _build_payload(self, message: str | None, conversation_id: str) -> dict[str, Any]:
        return {
            "message": message or "",
            "conversationId": conversation_id,
            "agentType": DEFAULT_AGENT_TYPE,
            "agentMode": DEFAULT_AGENT_MODE,
        }

    def call(
        self,
        message: str | None = None,
        *,
        conversation_id: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> InvokeResponse:
        if conversation_id is None:
            conversation_id = self._create_conversation(message or "New conversation")
        payload = self._build_payload(message, conversation_id)
        data = self._http.post("/invoke", json=payload)
        return InvokeResponse.from_dict(data)

    async def acall(
        self,
        message: str | None = None,
        *,
        conversation_id: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> InvokeResponse:
        if self._async_http is None:
            raise RuntimeError(
                "Async HTTP client not available. "
                "Use AISdk with enable_async=True for async operations."
            )
        if conversation_id is None:
            conversation_id = await self._acreate_conversation(message or "New conversation")
        payload = self._build_payload(message, conversation_id)
        data = await self._async_http.post("/invoke", json=payload)
        return InvokeResponse.from_dict(data)

    def stream(
        self,
        message: str | None = None,
        *,
        conversation_id: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> Iterable[StreamEvent]:
        if conversation_id is None:
            conversation_id = self._create_conversation(message or "New conversation")
        payload = self._build_payload(message, conversation_id)
        byte_stream = self._http.post_stream("/run", json=payload)
        return SSEIterator(byte_stream)

    def astream(
        self,
        message: str | None = None,
        *,
        conversation_id: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        if self._async_http is None:
            raise RuntimeError(
                "Async HTTP client not available. "
                "Use AISdk with enable_async=True for async operations."
            )

        async_http = self._async_http
        chat_async_http = self._chat_async_http

        async def _gen() -> AsyncIterator[StreamEvent]:
            cid = conversation_id
            if cid is None:
                if chat_async_http is None:
                    raise RuntimeError("Async HTTP client not available.")
                body = {"title": (message or "New conversation")[:_TITLE_MAX_LEN]}
                data = await chat_async_http.post("/chatConversations", json=body)
                cid = data["id"]
            payload = {
                "message": message or "",
                "conversationId": cid,
                "agentType": DEFAULT_AGENT_TYPE,
                "agentMode": DEFAULT_AGENT_MODE,
            }
            byte_stream = async_http.post_stream("/run", json=payload)
            async for event in AsyncSSEIterator(byte_stream):
                yield event

        return _gen()

    def stream_content(
        self,
        message: str | None = None,
        *,
        conversation_id: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> Iterable[str]:
        for event in self.stream(message, conversation_id=conversation_id, parameters=parameters):
            if event.type == EventType.CONTENT and event.content is not None:
                yield event.content

    async def astream_content(
        self,
        message: str | None = None,
        *,
        conversation_id: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> AsyncIterator[str]:
        async for event in self.astream(
            message, conversation_id=conversation_id, parameters=parameters
        ):
            if event.type == EventType.CONTENT and event.content is not None:
                yield event.content

    def get_info(self):
        raise NotImplementedError("Default agent has no metadata endpoint")

    async def aget_info(self):
        raise NotImplementedError("Default agent has no metadata endpoint")

    def __repr__(self) -> str:
        return "DefaultAgentHandle()"
