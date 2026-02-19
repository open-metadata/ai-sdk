"""SSE streaming internals for the Metadata AI SDK."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterator

from ai_sdk.models import StreamEvent


def _parse_event(event_str: str) -> StreamEvent | None:
    """
    Parse a single SSE event.

    Args:
        event_str: Raw SSE event string

    Returns:
        Parsed StreamEvent or None if invalid
    """
    event_type: str | None = None
    data: str | None = None

    for line in event_str.split("\n"):
        line = line.strip()
        if line.startswith("event:"):
            event_type = line[6:].strip()
        elif line.startswith("data:"):
            data = line[5:].strip()
        elif line.startswith("id:"):
            # Event ID, currently not used
            pass

    if not data:
        return None

    # Parse JSON data
    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        # If not valid JSON, treat as plain text content
        payload = {"content": data}

    # Map SSE event types to StreamEvent types
    mapped_type = _map_event_type(event_type)

    # Extract content from the nested message structure
    # The API returns: {"data": {"message": {"content": [{"textMessage": {"message": "..."}}]}}}
    content = None
    tool_name = None
    conversation_id = payload.get("conversationId")

    if message_data := payload.get("data"):
        if (
            isinstance(message_data, dict)
            and (message := message_data.get("message"))
            and isinstance(message, dict)
        ):
            if not conversation_id:
                conversation_id = message.get("conversationId")
            # Extract text content from content blocks
            if content_blocks := message.get("content"):
                text_parts = []
                for block in content_blocks:
                    if not isinstance(block, dict):
                        continue
                    # Extract text message
                    if text_msg := block.get("textMessage"):
                        if isinstance(text_msg, dict) and "message" in text_msg:
                            text_parts.append(text_msg["message"])
                        elif isinstance(text_msg, str):
                            text_parts.append(text_msg)
                    # Extract tool names
                    if tools := block.get("tools"):
                        for tool in tools:
                            if isinstance(tool, dict) and "name" in tool:
                                tool_name = tool["name"]
                if text_parts:
                    content = "".join(text_parts)
    elif "content" in payload:
        # Fallback to direct content field
        content = payload.get("content")

    # Fallback for simple format toolName
    if tool_name is None:
        tool_name = payload.get("toolName")

    return StreamEvent(
        type=mapped_type,
        content=content,
        tool_name=tool_name,
        conversation_id=conversation_id,
        error=payload.get("error") or payload.get("message") if mapped_type == "error" else None,
    )


def _map_event_type(event_type: str | None) -> str:
    """
    Map SSE event type to StreamEvent type.

    Args:
        event_type: Raw SSE event type

    Returns:
        Mapped event type string
    """
    if event_type is None:
        return "content"

    type_mapping = {
        "stream-start": "start",
        "message": "content",
        "tool-use": "tool_use",
        "stream-completed": "end",
        "error": "error",
        "fatal-error": "error",
    }

    return type_mapping.get(event_type, event_type)


class SSEIterator:
    """Parse Server-Sent Events into StreamEvent objects."""

    def __init__(self, byte_stream: Iterator[bytes]):
        """
        Initialize the SSE iterator.

        Args:
            byte_stream: Iterator of response bytes
        """
        self._stream = byte_stream
        self._buffer = ""

    def __iter__(self) -> Iterator[StreamEvent]:
        """Iterate over stream events."""
        for chunk in self._stream:
            self._buffer += chunk.decode("utf-8")

            # Process complete events (delimited by double newlines)
            while "\n\n" in self._buffer:
                event_str, self._buffer = self._buffer.split("\n\n", 1)
                event = _parse_event(event_str)
                if event:
                    yield event

        # Process any remaining buffer content
        if self._buffer.strip():
            event = _parse_event(self._buffer)
            if event:
                yield event


class AsyncSSEIterator:
    """Async parser for Server-Sent Events into StreamEvent objects."""

    def __init__(self, byte_stream: AsyncIterator[bytes]):
        """
        Initialize the async SSE iterator.

        Args:
            byte_stream: Async iterator of response bytes
        """
        self._stream = byte_stream
        self._buffer = ""

    def __aiter__(self) -> AsyncSSEIterator:
        return self

    async def __anext__(self) -> StreamEvent:
        """Get the next stream event."""
        while True:
            # Check if we have a complete event in buffer
            while "\n\n" in self._buffer:
                event_str, self._buffer = self._buffer.split("\n\n", 1)
                event = _parse_event(event_str)
                if event:
                    return event

            # Need more data from stream
            try:
                chunk = await self._stream.__anext__()
                self._buffer += chunk.decode("utf-8")
            except StopAsyncIteration:
                # Process any remaining buffer content
                if self._buffer.strip():
                    event = _parse_event(self._buffer)
                    self._buffer = ""
                    if event:
                        return event
                raise StopAsyncIteration
