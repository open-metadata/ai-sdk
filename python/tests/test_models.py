"""Tests for the AI SDK models."""

from ai_sdk.models import (
    AgentInfo,
    ContextMemory,
    CreateContextMemoryRequest,
    EntityReference,
    EventType,
    InvokeRequest,
    InvokeResponse,
    MemoryScope,
    MemorySearchHit,
    MemorySearchResults,
    MemoryType,
    MemoryVisibility,
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
        """StreamEvent.from_sse maps 'message' to EventType.CONTENT."""
        event = StreamEvent.from_sse("message", {"content": "Hello world"})

        assert event.type == EventType.CONTENT
        assert event.content == "Hello world"

    def test_from_sse_parses_tool_use_event(self):
        """StreamEvent.from_sse maps 'tool-use' to EventType.TOOL_USE."""
        event = StreamEvent.from_sse("tool-use", {"toolName": "search_metadata"})

        assert event.type == EventType.TOOL_USE
        assert event.tool_name == "search_metadata"

    def test_from_sse_parses_start_event(self):
        """StreamEvent.from_sse maps 'stream-start' to EventType.START."""
        event = StreamEvent.from_sse("stream-start", {"conversationId": "conv-123"})

        assert event.type == EventType.START
        assert event.conversation_id == "conv-123"


class TestAgentInfo:
    """Tests for AgentInfo model."""

    def test_from_dict_parses_full_response(self, sample_agent_info_dict):
        """AgentInfo.from_dict parses complete API response."""
        info = AgentInfo.from_dict(sample_agent_info_dict)

        assert info.name == "DataQualityPlannerAgent"
        assert info.display_name == "Data Quality Planner"
        assert info.description == "Analyzes data quality and suggests improvements"
        assert info.skills == ["search_metadata", "analyze_quality", "create_tests"]
        assert info.api_enabled is True

    def test_from_dict_defaults_missing_fields(self):
        """AgentInfo.from_dict provides defaults for missing fields."""
        info = AgentInfo.from_dict({"name": "TestAgent"})

        assert info.name == "TestAgent"
        assert info.display_name is None  # None when not provided
        assert info.description is None  # None when not provided
        assert info.skills == []
        assert info.api_enabled is False


class TestCreateContextMemoryRequest:
    """Tests for CreateContextMemoryRequest serialization."""

    def test_minimal_to_api_dict(self):
        req = CreateContextMemoryRequest(
            name="my-memory",
            question="What does X mean?",
            answer="X means Y.",
        )
        d = req.to_api_dict()
        assert d["name"] == "my-memory"
        assert d["question"] == "What does X mean?"
        assert d["answer"] == "X means Y."
        assert d["memoryType"] == "Note"
        assert d["memoryScope"] == "EntityScoped"
        assert d["shareConfig"] == {"visibility": "Private"}

    def test_with_primary_entity_and_tags(self):
        req = CreateContextMemoryRequest(
            name="m1",
            question="q",
            answer="a",
            memory_type=MemoryType.PREFERENCE,
            visibility=MemoryVisibility.SHARED,
            primary_entity=EntityReference(id="abc", type="table"),
            tags=["PII.Sensitive"],
        )
        d = req.to_api_dict()
        assert d["memoryType"] == "Preference"
        assert d["shareConfig"] == {"visibility": "Shared"}
        assert d["primaryEntity"] == {"id": "abc", "type": "table"}
        assert d["tags"] == [
            {
                "tagFQN": "PII.Sensitive",
                "labelType": "Manual",
                "state": "Confirmed",
                "source": "Classification",
            }
        ]


class TestContextMemory:
    """Tests for ContextMemory parsing."""

    def test_from_dict_extracts_visibility_from_share_config(self):
        data = {
            "id": "11111111-1111-1111-1111-111111111111",
            "name": "m1",
            "fullyQualifiedName": "m1",
            "title": "T",
            "question": "q",
            "answer": "a",
            "summary": None,
            "memoryType": "Note",
            "memoryScope": "EntityScoped",
            "shareConfig": {"visibility": "Entity"},
            "primaryEntity": {"id": "abc", "type": "table"},
            "usageCount": 3,
            "lastUsedAt": 1700000000000,
            "deleted": False,
        }
        m = ContextMemory.from_dict(data)
        assert m.id == "11111111-1111-1111-1111-111111111111"
        assert m.visibility == MemoryVisibility.ENTITY
        assert m.memory_scope == MemoryScope.ENTITY_SCOPED
        assert m.usage_count == 3
        assert m.last_used_at == 1700000000000

    def test_from_dict_defaults_visibility_when_share_config_missing(self):
        data = {"id": "x", "name": "m1"}
        m = ContextMemory.from_dict(data)
        assert m.visibility == MemoryVisibility.PRIVATE


class TestMemorySearchResults:
    """Tests for MemorySearchResults parsing."""

    def test_from_opensearch_response(self):
        resp = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {
                        "_score": 1.5,
                        "_source": {
                            "id": "11111111-1111-1111-1111-111111111111",
                            "name": "m1",
                            "fullyQualifiedName": "m1",
                            "title": "T",
                            "question": "q",
                            "answer": "a",
                            "summary": None,
                            "memoryType": "Note",
                            "memoryScope": "EntityScoped",
                            "shareConfig": {"visibility": "Private"},
                            "primaryEntity": None,
                            "usageCount": 0,
                            "lastUsedAt": None,
                            "deleted": False,
                        },
                    }
                ],
            }
        }
        results = MemorySearchResults.from_dict(resp)
        assert results.total == 2
        assert len(results.hits) == 1
        assert isinstance(results.hits[0], MemorySearchHit)
        assert results.hits[0].score == 1.5
        assert results.hits[0].memory.name == "m1"

    def test_from_dict_handles_empty_hits(self):
        results = MemorySearchResults.from_dict({"hits": {"total": {"value": 0}, "hits": []}})
        assert results.total == 0
        assert results.hits == []
