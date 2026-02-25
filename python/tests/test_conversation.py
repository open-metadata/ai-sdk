"""Tests for the Conversation class."""

import json

import pytest
from pytest_httpx import HTTPXMock

from ai_sdk.client import AISdk
from ai_sdk.conversation import Conversation


@pytest.fixture
def client():
    """AISdk client fixture with retries disabled."""
    c = AISdk(
        host="https://metadata.example.com",
        token="test-jwt-token",
        max_retries=0,
    )
    yield c
    c.close()


class TestConversationSend:
    """Tests for Conversation.send()."""

    def test_send_returns_response_and_stores_id(self, client, httpx_mock: HTTPXMock):
        """send() returns response text and stores conversation ID."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/TestAgent/invoke",
            json={
                "conversationId": "conv-123",
                "response": "Hello, this is the response.",
                "toolsUsed": [],
            },
        )

        agent = client.agent("TestAgent")
        conv = Conversation(agent)

        assert conv.id is None
        result = conv.send("Hello")

        assert result == "Hello, this is the response."
        assert conv.id == "conv-123"

    def test_send_uses_stored_conversation_id(self, client, httpx_mock: HTTPXMock):
        """send() uses stored conversation ID in subsequent calls."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/TestAgent/invoke",
            json={"conversationId": "conv-xyz", "response": "First", "toolsUsed": []},
        )
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/TestAgent/invoke",
            json={"conversationId": "conv-xyz", "response": "Second", "toolsUsed": []},
        )

        conv = Conversation(client.agent("TestAgent"))
        conv.send("First")
        conv.send("Second")

        requests = httpx_mock.get_requests()
        first_body = json.loads(requests[0].content)
        second_body = json.loads(requests[1].content)

        assert "conversationId" not in first_body
        assert second_body.get("conversationId") == "conv-xyz"

    def test_send_with_parameters(self, client, httpx_mock: HTTPXMock):
        """send() passes parameters to agent."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/TestAgent/invoke",
            json={"conversationId": "conv-123", "response": "OK", "toolsUsed": []},
        )

        conv = Conversation(client.agent("TestAgent"))
        conv.send("Query", parameters={"key": "value"})

        request = httpx_mock.get_request()
        body = json.loads(request.content)
        assert body.get("parameters") == {"key": "value"}

    def test_send_without_message(self, client, httpx_mock: HTTPXMock):
        """send() works without providing a message (uses agent's default prompt)."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/TestAgent/invoke",
            json={
                "conversationId": "conv-123",
                "response": "Default task executed.",
                "toolsUsed": [],
            },
        )

        conv = Conversation(client.agent("TestAgent"))
        result = conv.send()

        assert result == "Default task executed."
        assert conv.id == "conv-123"

        request = httpx_mock.get_request()
        body = json.loads(request.content)
        assert "message" not in body

    def test_send_without_message_does_not_add_to_history(self, client, httpx_mock: HTTPXMock):
        """send() without message does not add entry to history."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/TestAgent/invoke",
            json={"conversationId": "conv-123", "response": "OK", "toolsUsed": []},
        )

        conv = Conversation(client.agent("TestAgent"))
        conv.send()

        assert conv.history == []
        assert len(conv.responses) == 1


class TestConversationHistory:
    """Tests for Conversation history tracking."""

    def test_history_records_exchanges(self, client, httpx_mock: HTTPXMock):
        """history records user and assistant message pairs."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/TestAgent/invoke",
            json={"conversationId": "conv-123", "response": "Response 1", "toolsUsed": []},
        )
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/TestAgent/invoke",
            json={"conversationId": "conv-123", "response": "Response 2", "toolsUsed": []},
        )

        conv = Conversation(client.agent("TestAgent"))
        conv.send("Message 1")
        conv.send("Message 2")

        assert conv.history == [
            ("Message 1", "Response 1"),
            ("Message 2", "Response 2"),
        ]

    def test_messages_in_chat_format(self, client, httpx_mock: HTTPXMock):
        """messages returns chat format with roles."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/TestAgent/invoke",
            json={"conversationId": "conv-123", "response": "Hello there!", "toolsUsed": []},
        )

        conv = Conversation(client.agent("TestAgent"))
        conv.send("Hello")

        assert conv.messages == [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hello there!"},
        ]


class TestConversationReset:
    """Tests for Conversation.reset()."""

    def test_reset_clears_state(self, client, httpx_mock: HTTPXMock):
        """reset() clears conversation ID and history."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/TestAgent/invoke",
            json={"conversationId": "conv-123", "response": "OK", "toolsUsed": []},
        )

        conv = Conversation(client.agent("TestAgent"))
        conv.send("Message")

        assert conv.id == "conv-123"
        assert len(conv.history) == 1

        conv.reset()

        assert conv.id is None
        assert conv.history == []


class TestConversationAsync:
    """Tests for async Conversation methods."""

    @pytest.mark.asyncio
    async def test_asend_returns_response_and_stores_id(self, httpx_mock: HTTPXMock):
        """asend() returns response text and stores conversation ID."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/TestAgent/invoke",
            json={"conversationId": "async-conv-id", "response": "Async response", "toolsUsed": []},
        )

        client = AISdk(
            host="https://metadata.example.com",
            token="test-jwt-token",
            enable_async=True,
            max_retries=0,
        )

        try:
            conv = Conversation(client.agent("TestAgent"))
            result = await conv.asend("Hello")

            assert result == "Async response"
            assert conv.id == "async-conv-id"
        finally:
            await client.aclose()
            client.close()
