"""Tests for the Metadata AI SDK models."""

from ai_sdk.models import (
    AgentInfo,
    InvokeRequest,
    InvokeResponse,
    StreamEvent,
    Usage,
)


class TestInvokeRequest:
    """Tests for InvokeRequest model."""

    def test_to_api_dict_serialization(self):
        """to_api_dict produces correct API format with camelCase keys."""
        request = InvokeRequest(
            message="Full request",
            conversation_id="conv-456",
            parameters={"key": "value"},
        )
        result = request.to_api_dict()

        assert result == {
            "message": "Full request",
            "conversationId": "conv-456",
            "parameters": {"key": "value"},
        }

    def test_to_api_dict_excludes_none_and_empty(self):
        """to_api_dict excludes None values and empty parameters."""
        request = InvokeRequest(message="Test", parameters={})
        result = request.to_api_dict()

        assert result == {"message": "Test"}
        assert "conversationId" not in result
        assert "parameters" not in result

    def test_to_api_dict_without_message(self):
        """to_api_dict excludes message when None."""
        request = InvokeRequest(parameters={})
        result = request.to_api_dict()

        assert result == {}
        assert "message" not in result
        assert "conversationId" not in result
        assert "parameters" not in result

    def test_to_api_dict_with_only_conversation_id(self):
        """to_api_dict includes conversationId without message."""
        request = InvokeRequest(conversation_id="conv-123")
        result = request.to_api_dict()

        assert result == {"conversationId": "conv-123"}
        assert "message" not in result

    def test_message_is_optional(self):
        """InvokeRequest can be created without a message."""
        request = InvokeRequest()

        assert request.message is None
        assert request.conversation_id is None
        assert request.parameters == {}


class TestUsage:
    """Tests for Usage model."""

    def test_from_dict_parses_camel_case(self):
        """Usage.from_dict parses camelCase API response."""
        data = {
            "promptTokens": 100,
            "completionTokens": 50,
            "totalTokens": 150,
        }
        usage = Usage.from_dict(data)

        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150

    def test_from_dict_defaults_missing_fields(self):
        """Usage.from_dict defaults missing fields to zero."""
        usage = Usage.from_dict({})

        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0


class TestInvokeResponse:
    """Tests for InvokeResponse model."""

    def test_from_dict_parses_full_response(self, sample_invoke_response_dict):
        """InvokeResponse.from_dict parses complete API response."""
        response = InvokeResponse.from_dict(sample_invoke_response_dict)

        assert response.conversation_id == "550e8400-e29b-41d4-a716-446655440000"
        assert response.response == "The customers table has 3 data quality issues."
        assert response.tools_used == ["search_metadata", "analyze_quality"]
        assert response.usage.prompt_tokens == 150
        assert response.usage.total_tokens == 200


class TestStreamEvent:
    """Tests for StreamEvent model."""

    def test_from_sse_parses_content_event(self):
        """StreamEvent.from_sse parses content event."""
        event = StreamEvent.from_sse("message", {"content": "Hello world"})

        assert event.type == "message"
        assert event.content == "Hello world"

    def test_from_sse_parses_tool_use_event(self):
        """StreamEvent.from_sse parses tool use event."""
        event = StreamEvent.from_sse("tool-use", {"toolName": "search_metadata"})

        assert event.type == "tool-use"
        assert event.tool_name == "search_metadata"

    def test_from_sse_parses_start_event(self):
        """StreamEvent.from_sse parses start event with conversation ID."""
        event = StreamEvent.from_sse("stream-start", {"conversationId": "conv-123"})

        assert event.type == "stream-start"
        assert event.conversation_id == "conv-123"


class TestAgentInfo:
    """Tests for AgentInfo model."""

    def test_from_dict_parses_full_response(self, sample_agent_info_dict):
        """AgentInfo.from_dict parses complete API response."""
        info = AgentInfo.from_dict(sample_agent_info_dict)

        assert info.name == "DataQualityPlannerAgent"
        assert info.display_name == "Data Quality Planner"
        assert info.description == "Analyzes data quality and suggests improvements"
        assert info.abilities == ["search_metadata", "analyze_quality", "create_tests"]
        assert info.api_enabled is True

    def test_from_dict_defaults_missing_fields(self):
        """AgentInfo.from_dict provides defaults for missing fields."""
        info = AgentInfo.from_dict({"name": "TestAgent"})

        assert info.name == "TestAgent"
        assert info.display_name is None  # None when not provided
        assert info.description is None  # None when not provided
        assert info.abilities == []
        assert info.api_enabled is False
