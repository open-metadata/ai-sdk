"""Tests for the AI SDK agent handle."""

import json

import pytest
from pytest_httpx import HTTPXMock

from ai_sdk.client import AiSdk
from ai_sdk.exceptions import (
    AgentNotEnabledError,
    AgentNotFoundError,
    AuthenticationError,
)
from ai_sdk.models import AgentInfo, InvokeResponse


@pytest.fixture
def client():
    """AiSdk client fixture."""
    c = AiSdk(
        host="https://metadata.example.com",
        token="test-jwt-token",
    )
    yield c
    c.close()


@pytest.fixture
def agent(client):
    """Agent handle fixture."""
    return client.agent("DataQualityAgent")


class TestAgentHandleCall:
    """Tests for AgentHandle.call() method."""

    def test_call_returns_invoke_response(
        self, agent, httpx_mock: HTTPXMock, sample_invoke_response_dict
    ):
        """call() returns InvokeResponse with conversation_id and response."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/DataQualityAgent/invoke",
            json=sample_invoke_response_dict,
        )

        response = agent.call("What tables have issues?")

        assert isinstance(response, InvokeResponse)
        assert response.conversation_id == "550e8400-e29b-41d4-a716-446655440000"
        assert "customers table" in response.response

    def test_call_sends_message_and_optional_params(self, agent, httpx_mock: HTTPXMock):
        """call() sends message, conversation_id, and parameters in request."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/DataQualityAgent/invoke",
            json={"conversationId": "conv-1", "response": "OK"},
        )

        agent.call(
            "Analyze",
            conversation_id="existing-conv",
            parameters={"table": "customers"},
        )

        request = httpx_mock.get_request()
        body = json.loads(request.content)
        assert body["message"] == "Analyze"
        assert body["conversationId"] == "existing-conv"
        assert body["parameters"] == {"table": "customers"}

    def test_call_without_message(self, agent, httpx_mock: HTTPXMock):
        """call() works without providing a message."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/DataQualityAgent/invoke",
            json={"conversationId": "conv-1", "response": "Default task executed"},
        )

        response = agent.call()

        assert isinstance(response, InvokeResponse)
        assert response.response == "Default task executed"

        request = httpx_mock.get_request()
        body = json.loads(request.content)
        assert "message" not in body

    def test_call_with_none_message_and_parameters(self, agent, httpx_mock: HTTPXMock):
        """call() sends parameters but not message when message is None."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/DataQualityAgent/invoke",
            json={"conversationId": "conv-1", "response": "OK"},
        )

        agent.call(parameters={"key": "value"})

        request = httpx_mock.get_request()
        body = json.loads(request.content)
        assert "message" not in body
        assert body["parameters"] == {"key": "value"}

    def test_call_401_raises_authentication_error(self, agent, httpx_mock: HTTPXMock):
        """call() raises AuthenticationError on 401."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/DataQualityAgent/invoke",
            status_code=401,
        )

        with pytest.raises(AuthenticationError):
            agent.call("Test")

    def test_call_403_raises_agent_not_enabled_error(self, agent, httpx_mock: HTTPXMock):
        """call() raises AgentNotEnabledError on 403."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/DataQualityAgent/invoke",
            status_code=403,
        )

        with pytest.raises(AgentNotEnabledError) as exc_info:
            agent.call("Test")

        assert exc_info.value.agent_name == "DataQualityAgent"

    def test_call_404_raises_agent_not_found_error(self, agent, httpx_mock: HTTPXMock):
        """call() raises AgentNotFoundError on 404."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/DataQualityAgent/invoke",
            status_code=404,
        )

        with pytest.raises(AgentNotFoundError) as exc_info:
            agent.call("Test")

        assert exc_info.value.agent_name == "DataQualityAgent"


class TestAgentHandleStream:
    """Tests for AgentHandle.stream() method."""

    def test_stream_yields_events(self, agent, httpx_mock: HTTPXMock):
        """stream() yields StreamEvent objects with correct types."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/DataQualityAgent/stream",
            content=b'event: stream-start\ndata: {"conversationId": "conv-1"}\n\n'
            b'event: message\ndata: {"content": "Hello"}\n\n'
            b"event: stream-completed\ndata: {}\n\n",
        )

        events = list(agent.stream("Test"))

        assert len(events) == 3
        assert events[0].type == "start"
        assert events[0].conversation_id == "conv-1"
        assert events[1].type == "content"
        assert events[1].content == "Hello"
        assert events[2].type == "end"

    def test_stream_sends_conversation_id(self, agent, httpx_mock: HTTPXMock):
        """stream() sends conversation_id in request body."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/DataQualityAgent/stream",
            content=b'event: message\ndata: {"content": "OK"}\n\n',
        )

        list(agent.stream("Continue", conversation_id="existing-conv"))

        request = httpx_mock.get_request()
        body = json.loads(request.content)
        assert body["conversationId"] == "existing-conv"

    def test_stream_without_message(self, agent, httpx_mock: HTTPXMock):
        """stream() works without providing a message."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/DataQualityAgent/stream",
            content=b'event: stream-start\ndata: {"conversationId": "conv-1"}\n\n'
            b'event: message\ndata: {"content": "Default response"}\n\n'
            b"event: stream-completed\ndata: {}\n\n",
        )

        events = list(agent.stream())

        assert len(events) == 3
        assert events[1].content == "Default response"

        request = httpx_mock.get_request()
        body = json.loads(request.content)
        assert "message" not in body


class TestAgentHandleStreamContent:
    """Tests for AgentHandle.stream_content() method."""

    def test_stream_content_yields_only_strings(self, agent, httpx_mock: HTTPXMock):
        """stream_content() yields only content strings, not StreamEvent objects."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/DataQualityAgent/stream",
            content=b'event: stream-start\ndata: {"conversationId": "conv-1"}\n\n'
            b'event: message\ndata: {"content": "Hello "}\n\n'
            b'event: tool-use\ndata: {"toolName": "search"}\n\n'
            b'event: message\ndata: {"content": "world"}\n\n'
            b"event: stream-completed\ndata: {}\n\n",
        )

        chunks = list(agent.stream_content("Test"))

        assert chunks == ["Hello ", "world"]
        assert all(isinstance(c, str) for c in chunks)

    def test_stream_content_empty_for_no_content_events(self, agent, httpx_mock: HTTPXMock):
        """stream_content() yields nothing when there are no content events."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/DataQualityAgent/stream",
            content=b'event: stream-start\ndata: {"conversationId": "conv-1"}\n\n'
            b"event: stream-completed\ndata: {}\n\n",
        )

        chunks = list(agent.stream_content("Test"))

        assert chunks == []

    def test_stream_content_passes_conversation_id(self, agent, httpx_mock: HTTPXMock):
        """stream_content() forwards conversation_id to stream()."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/DataQualityAgent/stream",
            content=b'event: message\ndata: {"content": "OK"}\n\n',
        )

        list(agent.stream_content("Continue", conversation_id="existing-conv"))

        request = httpx_mock.get_request()
        body = json.loads(request.content)
        assert body["conversationId"] == "existing-conv"

    def test_stream_content_without_message(self, agent, httpx_mock: HTTPXMock):
        """stream_content() works without providing a message."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/DataQualityAgent/stream",
            content=b'event: message\ndata: {"content": "Default"}\n\n',
        )

        chunks = list(agent.stream_content())

        assert chunks == ["Default"]


class TestAgentHandleGetInfo:
    """Tests for AgentHandle.get_info() method."""

    def test_get_info_returns_agent_info(
        self, agent, httpx_mock: HTTPXMock, sample_agent_info_dict
    ):
        """get_info() returns AgentInfo with all fields."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/DataQualityAgent",
            json=sample_agent_info_dict,
        )

        info = agent.get_info()

        assert isinstance(info, AgentInfo)
        assert info.name == "DataQualityPlannerAgent"
        assert info.display_name == "Data Quality Planner"
        assert "search_metadata" in info.abilities
        assert info.api_enabled is True

    def test_get_info_404_raises_agent_not_found_error(self, agent, httpx_mock: HTTPXMock):
        """get_info() raises AgentNotFoundError on 404."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/name/DataQualityAgent",
            status_code=404,
        )

        with pytest.raises(AgentNotFoundError):
            agent.get_info()
