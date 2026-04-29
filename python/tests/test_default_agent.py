"""Tests for the default-agent path (client.agent() with no name)."""

import json

import pytest
from pytest_httpx import HTTPXMock

from ai_sdk.client import AISdk
from ai_sdk.models import InvokeResponse


@pytest.fixture
def client():
    c = AISdk(host="https://metadata.example.com", token="test-jwt-token")
    yield c
    c.close()


def test_default_agent_call_creates_conversation_then_invokes(client, httpx_mock: HTTPXMock):
    """client.agent().call(msg) should create a conversation, then call invoke."""
    httpx_mock.add_response(
        method="POST",
        url="https://metadata.example.com/api/v1/assistants/chatConversations",
        json={"id": "11111111-1111-1111-1111-111111111111"},
    )
    httpx_mock.add_response(
        method="POST",
        url="https://metadata.example.com/api/v1/agents/invoke",
        json={
            "conversationId": "11111111-1111-1111-1111-111111111111",
            "response": "hello",
            "toolsUsed": [],
        },
    )

    response = client.agent().call("Say hi")

    assert isinstance(response, InvokeResponse)
    assert response.conversation_id == "11111111-1111-1111-1111-111111111111"
    assert response.response == "hello"

    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    create_body = json.loads(requests[0].content)
    assert create_body["title"] == "Say hi"  # first 50 chars
    invoke_body = json.loads(requests[1].content)
    assert invoke_body["message"] == "Say hi"
    assert invoke_body["conversationId"] == "11111111-1111-1111-1111-111111111111"
    assert invoke_body["agentType"] == "PLANNER"
    assert invoke_body["agentMode"] == "CHAT_MODE"


def test_default_agent_reuses_existing_conversation(client, httpx_mock: HTTPXMock):
    """Passing conversation_id skips conversation creation."""
    httpx_mock.add_response(
        method="POST",
        url="https://metadata.example.com/api/v1/agents/invoke",
        json={
            "conversationId": "22222222-2222-2222-2222-222222222222",
            "response": "ok",
        },
    )

    response = client.agent().call(
        "Hello again",
        conversation_id="22222222-2222-2222-2222-222222222222",
    )

    assert response.conversation_id == "22222222-2222-2222-2222-222222222222"
    requests = httpx_mock.get_requests()
    assert len(requests) == 1  # no conversation creation
    assert "/agents/invoke" in str(requests[0].url)


def test_default_agent_stream_content(client, httpx_mock: HTTPXMock, sample_sse_stream):
    """Streaming default agent: creates conversation, streams to /run."""
    httpx_mock.add_response(
        method="POST",
        url="https://metadata.example.com/api/v1/assistants/chatConversations",
        json={"id": "33333333-3333-3333-3333-333333333333"},
    )
    httpx_mock.add_response(
        method="POST",
        url="https://metadata.example.com/api/v1/agents/run",
        content=b"".join(sample_sse_stream),
        headers={"content-type": "text/event-stream"},
    )

    chunks = list(client.agent().stream_content("Stream please"))
    assert "".join(chunks) == "The customers table has 3 issues."


@pytest.mark.asyncio
async def test_default_agent_acall(httpx_mock: HTTPXMock):
    """Async default-agent call: creates conversation, then async invoke."""
    async_client = AISdk(
        host="https://metadata.example.com",
        token="test-jwt-token",
        enable_async=True,
    )
    try:
        httpx_mock.add_response(
            method="POST",
            url="https://metadata.example.com/api/v1/assistants/chatConversations",
            json={"id": "44444444-4444-4444-4444-444444444444"},
        )
        httpx_mock.add_response(
            method="POST",
            url="https://metadata.example.com/api/v1/agents/invoke",
            json={
                "conversationId": "44444444-4444-4444-4444-444444444444",
                "response": "async hi",
            },
        )
        response = await async_client.agent().acall("Async test")
        assert response.response == "async hi"
    finally:
        await async_client.aclose()
        async_client.close()
