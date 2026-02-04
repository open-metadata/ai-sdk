"""
Integration tests for Metadata AI Python SDK.

These tests run against a real Metadata instance and require:
- METADATA_HOST: Base URL of the Metadata instance
- METADATA_TOKEN: JWT authentication token

Optional:
- METADATA_RUN_STREAMING_TESTS: Set to "true" to run streaming tests (uses tokens)

Run with: pytest tests/integration/ -v
"""

import os
import uuid

import pytest

from metadata_ai import MetadataAI
from metadata_ai.exceptions import (
    AgentNotFoundError,
    AuthenticationError,
    MetadataError,
    PersonaNotFoundError,
)
from metadata_ai.models import CreateAgentRequest, CreatePersonaRequest


# Skip all tests if credentials not configured
pytestmark = pytest.mark.skipif(
    not os.getenv("METADATA_HOST") or not os.getenv("METADATA_TOKEN"),
    reason="Integration tests require METADATA_HOST and METADATA_TOKEN environment variables",
)

# Check if streaming tests should run (they use tokens)
STREAMING_TESTS_ENABLED = os.getenv("METADATA_RUN_STREAMING_TESTS", "").lower() == "true"
skip_streaming = pytest.mark.skipif(
    not STREAMING_TESTS_ENABLED,
    reason="Streaming tests disabled (set METADATA_RUN_STREAMING_TESTS=true to enable)",
)


def unique_name(prefix: str) -> str:
    """Generate a unique name for test entities."""
    return f"{prefix}-test-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def client() -> MetadataAI:
    """Create a MetadataAI client from environment variables."""
    return MetadataAI(
        host=os.environ["METADATA_HOST"],
        token=os.environ["METADATA_TOKEN"],
    )


@pytest.fixture
def async_client() -> MetadataAI:
    """Create a MetadataAI client with async support."""
    return MetadataAI(
        host=os.environ["METADATA_HOST"],
        token=os.environ["METADATA_TOKEN"],
        enable_async=True,
    )


@pytest.fixture
def test_agent_name(client: MetadataAI) -> str | None:
    """Get or create a test agent for invoke/stream tests.
    
    Creates a new agent using an existing persona so it has LLM backend configured.
    Includes the discoveryAndSearch ability for proper testing.
    """
    # First check if there's a manually specified test agent
    if name := os.getenv("METADATA_TEST_AGENT"):
        return name
    
    # Get an existing persona to use (they have LLM configured)
    personas = client.list_personas()
    if not personas:
        return None
    
    # Create a test agent with this persona and discoveryAndSearch ability
    agent_name = unique_name("invoke-test-agent")
    try:
        request = CreateAgentRequest(
            name=agent_name,
            description="Auto-created agent for integration testing",
            persona=personas[0].name,
            mode="chat",
            abilities=["discoveryAndSearch"],
            api_enabled=True,
        )
        client.create_agent(request)
        return agent_name
    except Exception as e:
        print(f"Could not create test agent: {e}")
        # Fall back to first available agent
        agents = client.list_agents()
        if agents:
            return agents[0].name
        return None


class TestConnection:
    """Test basic connectivity to Metadata instance."""

    def test_client_creation(self, client: MetadataAI) -> None:
        """Test that client can be created with valid credentials."""
        assert client is not None
        assert client.host == os.environ["METADATA_HOST"].rstrip("/")

    def test_list_agents(self, client: MetadataAI) -> None:
        """Test that we can list agents (validates auth works)."""
        agents = client.list_agents()
        # Should return a list (may be empty, but shouldn't error)
        assert isinstance(agents, list)
        print(f"Found {len(agents)} API-enabled agents")

    def test_invalid_token_rejected(self) -> None:
        """Test that invalid tokens are rejected."""
        client = MetadataAI(
            host=os.environ["METADATA_HOST"],
            token="invalid-token-12345",
        )
        with pytest.raises(AuthenticationError):
            client.list_agents()


class TestAgentOperations:
    """Test agent operations against a real agent."""

    def test_get_agent_info(self, client: MetadataAI, test_agent_name: str | None) -> None:
        """Test getting agent info."""
        if not test_agent_name:
            pytest.skip("No test agent available")

        agent = client.agent(test_agent_name)
        info = agent.get_info()

        assert info is not None
        assert info.name == test_agent_name
        print(f"Agent '{test_agent_name}' info: {info.description or 'No description'}")

    def test_invoke_agent(self, client: MetadataAI, test_agent_name: str | None) -> None:
        """Test invoking an agent with a simple message."""
        if not test_agent_name:
            pytest.skip("No test agent available")

        agent = client.agent(test_agent_name)
        response = agent.call("Hello, this is an integration test. Please respond briefly.")

        assert response is not None
        assert response.response is not None
        assert len(response.response) > 0
        print(f"Agent response: {response.response[:200]}...")

    @skip_streaming
    def test_stream_agent(self, client: MetadataAI, test_agent_name: str | None) -> None:
        """Test streaming response from an agent."""
        if not test_agent_name:
            pytest.skip("No test agent available")

        agent = client.agent(test_agent_name)
        chunks = []

        # Use a prompt that triggers tool use with discoveryAndSearch ability
        for event in agent.stream("do we have any customer data"):
            if event.content:
                chunks.append(event.content)

        assert len(chunks) > 0, "Expected streaming content but got none"
        full_response = "".join(chunks)
        print(f"Streamed response: {full_response[:200]}...")


class TestAsyncOperations:
    """Test async operations."""

    @pytest.mark.asyncio
    async def test_async_list_agents(self, async_client: MetadataAI) -> None:
        """Test async agent listing."""
        agents = await async_client.alist_agents()
        assert isinstance(agents, list)

    @pytest.mark.asyncio
    async def test_async_invoke(
        self, async_client: MetadataAI, test_agent_name: str | None
    ) -> None:
        """Test async agent invocation."""
        if not test_agent_name:
            pytest.skip("No test agent available")

        agent = async_client.agent(test_agent_name)
        response = await agent.acall("Hello from async integration test!")

        assert response is not None
        assert response.response is not None

    @skip_streaming
    @pytest.mark.asyncio
    async def test_async_stream(
        self, async_client: MetadataAI, test_agent_name: str | None
    ) -> None:
        """Test async streaming."""
        if not test_agent_name:
            pytest.skip("No test agent available")

        agent = async_client.agent(test_agent_name)
        chunks = []

        # Use a prompt that triggers tool use with discoveryAndSearch ability
        async for event in agent.astream("do we have any customer data"):
            if event.content:
                chunks.append(event.content)

        assert len(chunks) > 0, "Expected async streaming content but got none"
        full_response = "".join(chunks)
        print(f"Async streamed response: {full_response[:200]}...")


class TestPersonaOperations:
    """Test persona CRUD operations."""

    def test_list_personas(self, client: MetadataAI) -> None:
        """Test listing personas."""
        personas = client.list_personas()
        assert isinstance(personas, list)
        print(f"Found {len(personas)} personas")

    def test_list_personas_with_limit(self, client: MetadataAI) -> None:
        """Test listing personas with limit."""
        personas = client.list_personas(limit=5)
        assert isinstance(personas, list)
        assert len(personas) <= 5

    def test_get_persona(self, client: MetadataAI) -> None:
        """Test getting a specific persona."""
        # First, list personas to get one that exists
        personas = client.list_personas()
        if not personas:
            pytest.skip("No personas available to test get_persona")

        persona_name = personas[0].name
        persona = client.get_persona(persona_name)

        assert persona is not None
        assert persona.name == persona_name
        print(f"Got persona: {persona.name} ({persona.display_name or 'No display name'})")

    def test_get_persona_not_found(self, client: MetadataAI) -> None:
        """Test that getting a non-existent persona raises error."""
        with pytest.raises(PersonaNotFoundError) as exc_info:
            client.get_persona("non-existent-persona-12345")
        assert exc_info.value.status_code == 404

    def test_create_persona(self, client: MetadataAI) -> None:
        """Test creating a new persona."""
        persona_name = unique_name("persona")
        request = CreatePersonaRequest(
            name=persona_name,
            description="Integration test persona",
            prompt="You are a helpful test assistant.",
            display_name="Test Persona",
        )

        created = client.create_persona(request)

        assert created is not None
        assert created.name == persona_name
        assert created.description == "Integration test persona"
        print(f"Created persona: {created.name}")

    @pytest.mark.asyncio
    async def test_async_list_personas(self, async_client: MetadataAI) -> None:
        """Test async listing personas."""
        personas = await async_client.alist_personas()
        assert isinstance(personas, list)

    @pytest.mark.asyncio
    async def test_async_get_persona(self, async_client: MetadataAI) -> None:
        """Test async getting a specific persona."""
        personas = await async_client.alist_personas()
        if not personas:
            pytest.skip("No personas available")

        persona = await async_client.aget_persona(personas[0].name)
        assert persona is not None

    @pytest.mark.asyncio
    async def test_async_create_persona(self, async_client: MetadataAI) -> None:
        """Test async creating a persona."""
        persona_name = unique_name("async-persona")
        request = CreatePersonaRequest(
            name=persona_name,
            description="Async integration test persona",
            prompt="You are a helpful async test assistant.",
        )

        created = await async_client.acreate_persona(request)
        assert created is not None
        assert created.name == persona_name


class TestBotOperations:
    """Test bot listing operations."""

    def test_list_bots(self, client: MetadataAI) -> None:
        """Test listing bots."""
        bots = client.list_bots()
        assert isinstance(bots, list)
        print(f"Found {len(bots)} bots")

    def test_list_bots_with_limit(self, client: MetadataAI) -> None:
        """Test listing bots with limit."""
        bots = client.list_bots(limit=5)
        assert isinstance(bots, list)
        assert len(bots) <= 5

    def test_get_bot(self, client: MetadataAI) -> None:
        """Test getting a specific bot."""
        bots = client.list_bots()
        if not bots:
            pytest.skip("No bots available to test get_bot")

        bot_name = bots[0].name
        bot = client.get_bot(bot_name)

        assert bot is not None
        assert bot.name == bot_name
        print(f"Got bot: {bot.name} ({bot.display_name or 'No display name'})")

    @pytest.mark.asyncio
    async def test_async_list_bots(self, async_client: MetadataAI) -> None:
        """Test async listing bots."""
        bots = await async_client.alist_bots()
        assert isinstance(bots, list)

    @pytest.mark.asyncio
    async def test_async_get_bot(self, async_client: MetadataAI) -> None:
        """Test async getting a specific bot."""
        bots = await async_client.alist_bots()
        if not bots:
            pytest.skip("No bots available")

        bot = await async_client.aget_bot(bots[0].name)
        assert bot is not None


class TestAbilityOperations:
    """Test ability listing operations."""

    def test_list_abilities(self, client: MetadataAI) -> None:
        """Test listing abilities."""
        abilities = client.list_abilities()
        assert isinstance(abilities, list)
        print(f"Found {len(abilities)} abilities")

    def test_list_abilities_with_limit(self, client: MetadataAI) -> None:
        """Test listing abilities with limit."""
        abilities = client.list_abilities(limit=5)
        assert isinstance(abilities, list)
        assert len(abilities) <= 5

    def test_ability_has_expected_fields(self, client: MetadataAI) -> None:
        """Test that abilities have expected fields."""
        abilities = client.list_abilities()
        if not abilities:
            pytest.skip("No abilities available")

        ability = abilities[0]
        assert hasattr(ability, "name")
        assert hasattr(ability, "description")
        print(f"Ability: {ability.name}")

    @pytest.mark.asyncio
    async def test_async_list_abilities(self, async_client: MetadataAI) -> None:
        """Test async listing abilities."""
        abilities = await async_client.alist_abilities()
        assert isinstance(abilities, list)


class TestAgentCRUDOperations:
    """Test agent CRUD operations."""

    def test_create_agent(self, client: MetadataAI) -> None:
        """Test creating a new agent."""
        # First, get a persona to use
        personas = client.list_personas()
        if not personas:
            pytest.skip("No personas available to create agent")

        agent_name = unique_name("agent")
        request = CreateAgentRequest(
            name=agent_name,
            description="Integration test agent",
            persona=personas[0].name,
            mode="chat",
            api_enabled=True,
        )

        created = client.create_agent(request)

        assert created is not None
        assert created.name == agent_name
        print(f"Created agent: {created.name}")

    def test_create_agent_with_abilities(self, client: MetadataAI) -> None:
        """Test creating an agent with abilities."""
        personas = client.list_personas()
        abilities = client.list_abilities()

        if not personas:
            pytest.skip("No personas available")
        if not abilities:
            pytest.skip("No abilities available")

        agent_name = unique_name("agent-abilities")
        ability_names = [a.name for a in abilities[:2]]  # Use first 2 abilities

        request = CreateAgentRequest(
            name=agent_name,
            description="Integration test agent with abilities",
            persona=personas[0].name,
            mode="agent",
            abilities=ability_names,
            api_enabled=True,
        )

        created = client.create_agent(request)

        assert created is not None
        assert created.name == agent_name
        print(f"Created agent with abilities: {created.name}")

    @pytest.mark.asyncio
    async def test_async_create_agent(self, async_client: MetadataAI) -> None:
        """Test async creating an agent."""
        personas = await async_client.alist_personas()
        if not personas:
            pytest.skip("No personas available")

        agent_name = unique_name("async-agent")
        request = CreateAgentRequest(
            name=agent_name,
            description="Async integration test agent",
            persona=personas[0].name,
            mode="chat",
            api_enabled=True,
        )

        created = await async_client.acreate_agent(request)
        assert created is not None
        assert created.name == agent_name
