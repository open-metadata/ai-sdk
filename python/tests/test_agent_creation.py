"""Tests for agent creation functionality."""

import pytest
from pytest_httpx import HTTPXMock

from ai_sdk.client import MetadataAI
from ai_sdk.models import AgentInfo, CreateAgentRequest, KnowledgeScope


@pytest.fixture
def client():
    """MetadataAI client fixture."""
    c = MetadataAI(
        host="https://metadata.example.com",
        token="test-jwt-token",
    )
    yield c
    c.close()


@pytest.fixture
def async_client():
    """MetadataAI async client fixture."""
    c = MetadataAI(
        host="https://metadata.example.com",
        token="test-jwt-token",
        enable_async=True,
    )
    yield c
    c.close()


@pytest.fixture
def sample_agent_response():
    """Sample agent creation response from API."""
    return {
        "name": "MyTestAgent",
        "displayName": "My Test Agent",
        "description": "An agent for testing",
        "abilities": ["search_metadata", "analyze_quality"],
        "apiEnabled": True,
    }


@pytest.fixture
def sample_agent_response_all_fields():
    """Sample agent creation response with all fields from API."""
    return {
        "name": "FullAgent",
        "displayName": "Full Featured Agent",
        "description": "An agent with all configuration options",
        "abilities": ["search_metadata", "analyze_quality", "create_tests"],
        "apiEnabled": True,
    }


class TestCreateAgentRequest:
    """Tests for CreateAgentRequest model."""

    def test_minimal_request(self):
        """CreateAgentRequest works with minimal required fields."""
        request = CreateAgentRequest(
            name="MyAgent",
            description="A test agent",
            persona="DataAnalyst",
            mode="chat",
        )

        assert request.name == "MyAgent"
        assert request.description == "A test agent"
        assert request.persona == "DataAnalyst"
        assert request.mode == "chat"
        assert request.api_enabled is False  # Default value

    def test_request_with_all_fields(self):
        """CreateAgentRequest works with all fields."""
        knowledge = KnowledgeScope(entity_types=["table", "database"])
        request = CreateAgentRequest(
            name="FullAgent",
            description="Full featured agent",
            persona="DataAnalyst",
            mode="agent",
            display_name="Full Featured Agent",
            icon="bot-icon",
            bot_name="my-bot",
            abilities=["search", "analyze"],
            knowledge=knowledge,
            prompt="workflow: step1 -> step2",
            schedule="0 0 * * *",
            api_enabled=True,
            provider="user",
        )

        assert request.name == "FullAgent"
        assert request.display_name == "Full Featured Agent"
        assert request.icon == "bot-icon"
        assert request.bot_name == "my-bot"
        assert request.abilities == ["search", "analyze"]
        assert request.knowledge is not None
        assert request.knowledge.entity_types == ["table", "database"]
        assert request.prompt == "workflow: step1 -> step2"
        assert request.schedule == "0 0 * * *"
        assert request.api_enabled is True
        assert request.provider == "user"

    def test_to_api_dict_minimal(self):
        """to_api_dict produces correct output for minimal request."""
        request = CreateAgentRequest(
            name="MyAgent",
            description="A test agent",
            persona="DataAnalyst",
            mode="chat",
        )

        api_dict = request.to_api_dict()

        assert api_dict["name"] == "MyAgent"
        assert api_dict["description"] == "A test agent"
        assert api_dict["persona"] == {
            "name": "DataAnalyst",
            "type": "persona",
        }  # EntityReference format
        assert api_dict["mode"] == "chat"
        assert api_dict["apiEnabled"] is False
        assert api_dict["provider"] == "user"
        # Optional fields should not be present
        assert "displayName" not in api_dict
        assert "icon" not in api_dict
        assert "botName" not in api_dict

    def test_to_api_dict_all_fields(self):
        """to_api_dict produces correct output with all fields."""
        knowledge = KnowledgeScope(entity_types=["table"])
        request = CreateAgentRequest(
            name="FullAgent",
            description="Full agent",
            persona="Analyst",
            mode="both",
            display_name="Full Agent",
            icon="robot",
            bot_name="test-bot",
            abilities=["search"],
            knowledge=knowledge,
            prompt="workflow",
            schedule="* * * * *",
            api_enabled=True,
        )

        api_dict = request.to_api_dict()

        assert api_dict["displayName"] == "Full Agent"
        assert api_dict["icon"] == "robot"
        assert api_dict["botName"] == "test-bot"
        assert api_dict["abilities"] == ["search"]
        assert api_dict["knowledge"] == {"entityTypes": ["table"]}
        assert api_dict["prompt"] == "workflow"
        assert api_dict["schedule"] == "* * * * *"
        assert api_dict["apiEnabled"] is True


class TestCreateAgent:
    """Tests for MetadataAI.create_agent() method."""

    def test_create_agent_minimal(self, client, httpx_mock: HTTPXMock, sample_agent_response):
        """create_agent works with minimal fields."""
        # Mock persona resolution
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/personas/name/DataAnalyst",
            method="GET",
            json={
                "id": "persona-123",
                "name": "DataAnalyst",
                "displayName": "Data Analyst",
                "provider": "system",
            },
        )
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/",
            method="POST",
            json=sample_agent_response,
        )

        request = CreateAgentRequest(
            name="MyTestAgent",
            description="An agent for testing",
            persona="DataAnalyst",
            mode="chat",
        )
        result = client.create_agent(request)

        assert isinstance(result, AgentInfo)
        assert result.name == "MyTestAgent"
        assert result.display_name == "My Test Agent"
        assert result.description == "An agent for testing"
        assert result.api_enabled is True

    def test_create_agent_all_fields(
        self, client, httpx_mock: HTTPXMock, sample_agent_response_all_fields
    ):
        """create_agent works with all fields."""
        # Mock persona resolution
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/personas/name/DataAnalyst",
            method="GET",
            json={
                "id": "persona-123",
                "name": "DataAnalyst",
                "displayName": "Data Analyst",
                "provider": "system",
            },
        )
        # Mock ability resolution
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/abilities/name/search_metadata",
            method="GET",
            json={"id": "ability-1", "name": "search_metadata", "tools": []},
        )
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/abilities/name/analyze_quality",
            method="GET",
            json={"id": "ability-2", "name": "analyze_quality", "tools": []},
        )
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/abilities/name/create_tests",
            method="GET",
            json={"id": "ability-3", "name": "create_tests", "tools": []},
        )
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/",
            method="POST",
            json=sample_agent_response_all_fields,
        )

        knowledge = KnowledgeScope(entity_types=["table", "database"])
        request = CreateAgentRequest(
            name="FullAgent",
            description="An agent with all configuration options",
            persona="DataAnalyst",
            mode="agent",
            display_name="Full Featured Agent",
            icon="bot-icon",
            bot_name="ingestion-bot",
            abilities=["search_metadata", "analyze_quality", "create_tests"],
            knowledge=knowledge,
            prompt="analyze -> report",
            schedule="0 */6 * * *",
            api_enabled=True,
        )
        result = client.create_agent(request)

        assert isinstance(result, AgentInfo)
        assert result.name == "FullAgent"
        assert result.display_name == "Full Featured Agent"
        assert result.abilities == ["search_metadata", "analyze_quality", "create_tests"]

    def test_create_agent_sends_correct_body(self, client, httpx_mock: HTTPXMock):
        """create_agent sends correct request body with resolved persona ID."""
        # Mock persona resolution
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/personas/name/TestPersona",
            method="GET",
            json={
                "id": "persona-456",
                "name": "TestPersona",
                "displayName": "Test Persona",
                "provider": "user",
            },
        )
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/",
            method="POST",
            json={"name": "TestAgent", "displayName": "TestAgent", "apiEnabled": True},
        )

        request = CreateAgentRequest(
            name="TestAgent",
            description="Test description",
            persona="TestPersona",
            mode="chat",
            api_enabled=True,
        )
        client.create_agent(request)

        # Get the POST request (second request, after persona GET)
        requests = httpx_mock.get_requests()
        post_request = next(r for r in requests if r.method == "POST")

        import json

        body = json.loads(post_request.content)
        assert body["name"] == "TestAgent"
        assert body["description"] == "Test description"
        # Persona should be resolved to EntityReference with ID
        assert body["persona"] == {"id": "persona-456", "type": "persona"}
        assert body["mode"] == "chat"
        assert body["apiEnabled"] is True


class TestAsyncCreateAgent:
    """Tests for MetadataAI.acreate_agent() method."""

    @pytest.mark.asyncio
    async def test_acreate_agent(self, async_client, httpx_mock: HTTPXMock, sample_agent_response):
        """acreate_agent works correctly."""
        # Mock persona resolution
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/personas/name/DataAnalyst",
            method="GET",
            json={
                "id": "persona-123",
                "name": "DataAnalyst",
                "displayName": "Data Analyst",
                "provider": "system",
            },
        )
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/dynamic/",
            method="POST",
            json=sample_agent_response,
        )

        request = CreateAgentRequest(
            name="MyTestAgent",
            description="An agent for testing",
            persona="DataAnalyst",
            mode="chat",
        )
        result = await async_client.acreate_agent(request)

        assert isinstance(result, AgentInfo)
        assert result.name == "MyTestAgent"
        assert result.display_name == "My Test Agent"

    @pytest.mark.asyncio
    async def test_acreate_agent_requires_async_enabled(self, client):
        """acreate_agent raises error when async not enabled."""
        request = CreateAgentRequest(
            name="TestAgent",
            description="Test",
            persona="TestPersona",
            mode="chat",
        )

        with pytest.raises(RuntimeError) as exc_info:
            await client.acreate_agent(request)

        assert "Async HTTP client not available" in str(exc_info.value)


class TestKnowledgeScope:
    """Tests for KnowledgeScope model."""

    def test_knowledge_scope_entity_types(self):
        """KnowledgeScope works with entity_types."""
        scope = KnowledgeScope(entity_types=["table", "database", "pipeline"])

        assert scope.entity_types == ["table", "database", "pipeline"]
        assert scope.services is None

    def test_knowledge_scope_to_api_dict(self):
        """KnowledgeScope.to_api_dict produces correct camelCase output."""
        scope = KnowledgeScope(entity_types=["table", "database"])

        api_dict = scope.to_api_dict()

        assert api_dict == {"entityTypes": ["table", "database"]}

    def test_knowledge_scope_empty(self):
        """KnowledgeScope works when empty."""
        scope = KnowledgeScope()

        assert scope.entity_types is None
        assert scope.services is None
        assert scope.to_api_dict() == {}
