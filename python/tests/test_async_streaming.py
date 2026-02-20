"""Test that async streaming works correctly."""

from unittest.mock import MagicMock

import pytest

from ai_sdk.agent import AgentHandle


class MockAsyncByteStream:
    """Mock async byte stream that yields SSE events."""

    def __init__(self, events: list[bytes]):
        self._events = iter(events)

    def __aiter__(self):
        return self

    async def __anext__(self) -> bytes:
        try:
            return next(self._events)
        except StopIteration:
            raise StopAsyncIteration


@pytest.mark.asyncio
async def test_astream_is_async_iterable():
    """Test that astream returns something that works with async for."""
    mock_http = MagicMock()
    mock_async_http = MagicMock()

    sse_data = [
        b'event: stream-start\ndata: {"conversationId": "test-123"}\n\n',
        b'event: message\ndata: {"content": "Hello"}\n\n',
        b'event: stream-completed\ndata: {"conversationId": "test-123"}\n\n',
    ]
    mock_async_http.post_stream.return_value = MockAsyncByteStream(sse_data)

    agent = AgentHandle(name="TestAgent", http=mock_http, async_http=mock_async_http)

    events = []
    async for event in agent.astream("test message"):
        events.append(event)

    assert len(events) == 3
    assert events[0].type == "start"
    assert events[1].type == "content"
    assert events[1].content == "Hello"
    assert events[2].type == "end"


@pytest.mark.asyncio
async def test_astream_content_yields_only_strings():
    """Test that astream_content yields only content strings."""
    mock_http = MagicMock()
    mock_async_http = MagicMock()

    sse_data = [
        b'event: stream-start\ndata: {"conversationId": "test-123"}\n\n',
        b'event: message\ndata: {"content": "Hello "}\n\n',
        b'event: tool-use\ndata: {"toolName": "search"}\n\n',
        b'event: message\ndata: {"content": "world"}\n\n',
        b'event: stream-completed\ndata: {"conversationId": "test-123"}\n\n',
    ]
    mock_async_http.post_stream.return_value = MockAsyncByteStream(sse_data)

    agent = AgentHandle(name="TestAgent", http=mock_http, async_http=mock_async_http)

    chunks = []
    async for chunk in agent.astream_content("test message"):
        chunks.append(chunk)

    assert chunks == ["Hello ", "world"]
    assert all(isinstance(c, str) for c in chunks)
