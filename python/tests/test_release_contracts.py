"""Regressions for the OpenMetadata and Collate 2.1 wire contracts."""

import json

import pytest

from ai_sdk._streaming import SSEIterator
from ai_sdk.client import AISdk
from ai_sdk.models import (
    ContextMemory,
    CreateAgentRequest,
    CreateContextMemoryRequest,
    InvokeRequest,
    StreamEvent,
)


def test_current_memory_values_and_lifecycle():
    memory = ContextMemory.from_dict(
        {
            "id": "m1",
            "name": "learning",
            "memoryType": "Learning",
            "shareConfig": {"visibility": "Public"},
            "entityStatus": "Unprocessed",
            "statusReason": "Awaiting review",
        }
    )
    assert memory.memory_type == "Learning"
    assert memory.visibility == "Public"
    assert memory.entity_status == "Unprocessed"
    assert memory.status_reason == "Awaiting review"
    request = CreateContextMemoryRequest(
        name="learning", question="q", answer="a", entity_status="Approved"
    )
    assert request.to_api_dict()["entityStatus"] == "Approved"


def test_agent_creation_uses_current_modes():
    request = CreateAgentRequest(name="agent", description="d", persona="p", mode="standalone")
    assert request.to_api_dict()["mode"] == "standalone"
    assert "schedule" not in request.to_api_dict()
    with pytest.raises(ValueError):
        CreateAgentRequest(name="agent", description="d", persona="p", mode="chat")


def test_worker_creation_retains_required_planner_instructions():
    with pytest.raises(ValueError):
        CreateAgentRequest(name="worker", description="d", persona="p", mode="worker")
    request = CreateAgentRequest(
        name="worker",
        description="d",
        persona="p",
        mode="worker",
        planner_description={"description": "d", "input": "i", "output": "o", "prompt": "do work"},
    )
    assert request.to_api_dict()["plannerDescription"]["prompt"] == "do work"


def test_prompt_only_invocation_still_sends_required_message():
    assert InvokeRequest().to_api_dict() == {"message": ""}


def test_memory_filter_uses_primary_entity_uuid(httpx_mock):
    httpx_mock.add_response(
        url="https://example.com/api/v1/contextCenter/memories/?limit=100&primaryEntityId=asset-id",
        json={"data": [], "paging": {}},
    )
    with AISdk(host="https://example.com", token="test") as client:
        assert client.memories.list(primary_entity_id="asset-id") == []


def test_terminal_stream_error_is_observable():
    event = next(
        iter(
            SSEIterator(
                iter(
                    [b'event: stream-error\ndata: {"message":"run failed","severity":"fatal"}\n\n']
                )
            )
        )
    )
    assert event.type == "error"
    assert event.error == "run failed"
    assert StreamEvent.from_sse("stream-error", {"message": "run failed"}).error == "run failed"


@pytest.mark.parametrize("adapter", ["openai", "langchain"])
def test_mcp_discovery_preserves_names_and_nested_schema(httpx_mock, adapter):
    schema = {
        "type": "object",
        "properties": {
            "entityType": {"type": "string", "enum": ["glossaryTerm", "metric"]},
            "tags": {"type": "array", "items": {"type": "string"}},
            "attributes": {"type": "object", "properties": {"parent": {"type": "string"}}},
        },
        "required": ["entityType"],
        "additionalProperties": False,
    }
    httpx_mock.add_response(
        url="https://example.com/mcp",
        json={"result": {"tools": [{"name": "create_entity", "inputSchema": schema}]}},
    )
    with AISdk(host="https://example.com", token="test") as client:
        if adapter == "openai":
            tool = client.mcp.as_openai_tools()[0]["function"]
            assert tool["name"] == "create_entity"
            assert tool["parameters"] == schema
        else:
            from langchain_core.utils.function_calling import convert_to_openai_tool

            tool = client.mcp.as_langchain_tools()[0]
            assert tool.name == "create_entity"
            assert tool.args_schema == schema
            exported = convert_to_openai_tool(tool)["function"]["parameters"]
            assert exported["properties"] == schema["properties"]
            assert exported["additionalProperties"] is False


def test_structured_invoke_output_is_retained(httpx_mock):
    components = [{"type": "chart", "content": {"title": "Revenue"}}]
    httpx_mock.add_response(
        url="https://example.com/api/v1/agents/dynamic/name/agent/invoke",
        json={"conversationId": "c1", "response": "", "components": components},
    )
    with AISdk(host="https://example.com", token="test") as client:
        response = client.agent("agent").call("chart")
        assert response.components == components
        assert json.loads(httpx_mock.get_request().content)["message"] == "chart"
