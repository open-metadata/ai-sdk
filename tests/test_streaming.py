"""Tests for the Metadata AI SDK streaming functionality."""

from metadata_ai._streaming import SSEIterator


class TestSSEIterator:
    """Tests for SSEIterator."""

    def test_parses_single_event(self):
        """SSEIterator parses a single complete event."""
        stream = iter([b'event: message\ndata: {"content": "Hello"}\n\n'])
        events = list(SSEIterator(stream))

        assert len(events) == 1
        assert events[0].type == "content"
        assert events[0].content == "Hello"

    def test_parses_multiple_events(self, sample_sse_stream):
        """SSEIterator parses multiple events correctly."""
        events = list(SSEIterator(iter(sample_sse_stream)))

        assert len(events) == 6
        assert events[0].type == "start"
        assert events[0].conversation_id == "550e8400-e29b-41d4-a716-446655440000"
        assert events[1].type == "content"
        assert events[1].content == "The customers "
        assert events[3].type == "tool_use"
        assert events[3].tool_name == "search_metadata"
        assert events[5].type == "end"

    def test_handles_chunked_stream(self):
        """SSEIterator handles events split across chunks."""
        stream = iter(
            [
                b"event: mes",
                b'sage\ndata: {"con',
                b'tent": "Chunked"}\n\n',
            ]
        )
        events = list(SSEIterator(stream))

        assert len(events) == 1
        assert events[0].content == "Chunked"

    def test_handles_multiple_events_in_single_chunk(self):
        """SSEIterator handles multiple events in one chunk."""
        stream = iter(
            [
                b'event: message\ndata: {"content": "First"}\n\nevent: message\ndata: {"content": "Second"}\n\n'
            ]
        )
        events = list(SSEIterator(stream))

        assert len(events) == 2
        assert events[0].content == "First"
        assert events[1].content == "Second"

    def test_maps_event_types_correctly(self):
        """SSEIterator maps SSE event types to StreamEvent types."""
        test_cases = [
            (b"event: stream-start\ndata: {}\n\n", "start"),
            (b"event: message\ndata: {}\n\n", "content"),
            (b"event: tool-use\ndata: {}\n\n", "tool_use"),
            (b"event: stream-completed\ndata: {}\n\n", "end"),
            (b"event: error\ndata: {}\n\n", "error"),
            (b"event: fatal-error\ndata: {}\n\n", "error"),
        ]

        for sse_bytes, expected_type in test_cases:
            events = list(SSEIterator(iter([sse_bytes])))
            assert events[0].type == expected_type

    def test_handles_event_without_event_field(self):
        """SSEIterator defaults to content type when event field missing."""
        stream = iter([b'data: {"content": "No event type"}\n\n'])
        events = list(SSEIterator(stream))

        assert len(events) == 1
        assert events[0].type == "content"
        assert events[0].content == "No event type"

    def test_handles_non_json_data(self):
        """SSEIterator handles non-JSON data as plain text content."""
        stream = iter([b"event: message\ndata: Plain text message\n\n"])
        events = list(SSEIterator(stream))

        assert len(events) == 1
        assert events[0].content == "Plain text message"

    def test_skips_empty_data(self):
        """SSEIterator skips events with no data field."""
        stream = iter(
            [
                b"event: ping\n\n",
                b'event: message\ndata: {"content": "Real event"}\n\n',
            ]
        )
        events = list(SSEIterator(stream))

        assert len(events) == 1
        assert events[0].content == "Real event"

    def test_handles_error_event(self):
        """SSEIterator parses error events."""
        stream = iter([b'event: error\ndata: {"error": "Something broke"}\n\n'])
        events = list(SSEIterator(stream))

        assert events[0].type == "error"
        assert events[0].error == "Something broke"

    def test_handles_error_with_message_field_fallback(self):
        """SSEIterator uses message field for error if error field missing."""
        stream = iter([b'event: error\ndata: {"message": "Error via message"}\n\n'])
        events = list(SSEIterator(stream))

        assert events[0].error == "Error via message"

    def test_handles_trailing_content_without_newlines(self):
        """SSEIterator handles content after last double newline."""
        stream = iter(
            [
                b'event: message\ndata: {"content": "First"}\n\n',
                b'event: message\ndata: {"content": "Last"}',
            ]
        )
        events = list(SSEIterator(stream))

        assert len(events) == 2
        assert events[1].content == "Last"
