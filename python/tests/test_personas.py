"""Tests for persona operations in the Metadata AI SDK."""

import pytest
from pytest_httpx import HTTPXMock

from metadata_ai.client import MetadataAI
from metadata_ai.exceptions import PersonaNotFoundError
from metadata_ai.models import CreatePersonaRequest, PersonaInfo


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
    """MetadataAI client fixture with async enabled."""
    c = MetadataAI(
        host="https://metadata.example.com",
        token="test-jwt-token",
        enable_async=True,
    )
    yield c
    c.close()


@pytest.fixture
def sample_persona_info_dict():
    """Sample persona info as returned by API."""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "name": "DataAnalyst",
        "displayName": "Data Analyst",
        "description": "An AI persona specialized in data analysis",
        "prompt": "You are a data analyst who helps users understand their data.",
        "provider": "user",
    }


@pytest.fixture
def sample_personas_list_response(sample_persona_info_dict):
    """Sample list personas response as returned by API."""
    return {
        "data": [
            sample_persona_info_dict,
            {
                "id": "550e8400-e29b-41d4-a716-446655440002",
                "name": "DataEngineer",
                "displayName": "Data Engineer",
                "description": "An AI persona specialized in data engineering",
                "prompt": "You are a data engineer who helps with data pipelines.",
                "provider": "system",
            },
        ]
    }


class TestListPersonas:
    """Tests for list_personas method."""

    def test_list_personas_returns_persona_info(
        self, client, httpx_mock: HTTPXMock, sample_personas_list_response
    ):
        """list_personas returns list of PersonaInfo objects."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/personas/?limit=100",
            json=sample_personas_list_response,
        )

        personas = client.list_personas()

        assert len(personas) == 2
        assert all(isinstance(p, PersonaInfo) for p in personas)
        assert personas[0].name == "DataAnalyst"
        assert personas[0].display_name == "Data Analyst"
        assert personas[1].name == "DataEngineer"

    def test_list_personas_with_limit(
        self, client, httpx_mock: HTTPXMock, sample_personas_list_response
    ):
        """list_personas respects user limit parameter."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/personas/?limit=100",
            json=sample_personas_list_response,
        )

        # Request only 1 persona, even though API returns 2
        personas = client.list_personas(limit=1)

        assert len(personas) == 1
        assert personas[0].name == "DataAnalyst"

    @pytest.mark.asyncio
    async def test_alist_personas_returns_persona_info(
        self, async_client, httpx_mock: HTTPXMock, sample_personas_list_response
    ):
        """alist_personas returns list of PersonaInfo objects."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/personas/?limit=100",
            json=sample_personas_list_response,
        )

        personas = await async_client.alist_personas()

        assert len(personas) == 2
        assert all(isinstance(p, PersonaInfo) for p in personas)
        assert personas[0].name == "DataAnalyst"


class TestGetPersona:
    """Tests for get_persona method."""

    def test_get_persona_returns_persona_info(
        self, client, httpx_mock: HTTPXMock, sample_persona_info_dict
    ):
        """get_persona returns PersonaInfo object."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/personas/name/DataAnalyst",
            json=sample_persona_info_dict,
        )

        persona = client.get_persona("DataAnalyst")

        assert isinstance(persona, PersonaInfo)
        assert persona.name == "DataAnalyst"
        assert persona.display_name == "Data Analyst"
        assert persona.description == "An AI persona specialized in data analysis"
        assert persona.prompt == "You are a data analyst who helps users understand their data."
        assert persona.provider == "user"

    def test_get_persona_not_found_raises_error(self, client, httpx_mock: HTTPXMock):
        """get_persona raises PersonaNotFoundError on 404."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/personas/name/NonExistentPersona",
            status_code=404,
            json={"message": "Persona not found"},
        )

        with pytest.raises(PersonaNotFoundError) as exc_info:
            client.get_persona("NonExistentPersona")

        assert exc_info.value.persona_name == "NonExistentPersona"
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_aget_persona_returns_persona_info(
        self, async_client, httpx_mock: HTTPXMock, sample_persona_info_dict
    ):
        """aget_persona returns PersonaInfo object."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/personas/name/DataAnalyst",
            json=sample_persona_info_dict,
        )

        persona = await async_client.aget_persona("DataAnalyst")

        assert isinstance(persona, PersonaInfo)
        assert persona.name == "DataAnalyst"

    @pytest.mark.asyncio
    async def test_aget_persona_not_found_raises_error(self, async_client, httpx_mock: HTTPXMock):
        """aget_persona raises PersonaNotFoundError on 404."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/personas/name/NonExistentPersona",
            status_code=404,
            json={"message": "Persona not found"},
        )

        with pytest.raises(PersonaNotFoundError) as exc_info:
            await async_client.aget_persona("NonExistentPersona")

        assert exc_info.value.persona_name == "NonExistentPersona"


class TestCreatePersona:
    """Tests for create_persona method."""

    def test_create_persona_returns_persona_info(
        self, client, httpx_mock: HTTPXMock, sample_persona_info_dict
    ):
        """create_persona returns PersonaInfo object."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/personas/",
            method="POST",
            json=sample_persona_info_dict,
        )

        request = CreatePersonaRequest(
            name="DataAnalyst",
            description="An AI persona specialized in data analysis",
            prompt="You are a data analyst who helps users understand their data.",
            display_name="Data Analyst",
        )

        persona = client.create_persona(request)

        assert isinstance(persona, PersonaInfo)
        assert persona.name == "DataAnalyst"
        assert persona.display_name == "Data Analyst"

    def test_create_persona_sends_correct_body(self, client, httpx_mock: HTTPXMock):
        """create_persona sends correct request body."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/personas/",
            method="POST",
            json={
                "id": "new-persona-id",
                "name": "NewPersona",
                "displayName": "New Persona",
                "description": "A new persona",
                "prompt": "You are a helpful assistant.",
                "provider": "user",
            },
        )

        request = CreatePersonaRequest(
            name="NewPersona",
            description="A new persona",
            prompt="You are a helpful assistant.",
            display_name="New Persona",
        )

        client.create_persona(request)

        http_request = httpx_mock.get_request()
        assert http_request.method == "POST"
        body = http_request.read().decode()
        assert "NewPersona" in body
        assert "A new persona" in body
        assert "You are a helpful assistant." in body

    @pytest.mark.asyncio
    async def test_acreate_persona_returns_persona_info(
        self, async_client, httpx_mock: HTTPXMock, sample_persona_info_dict
    ):
        """acreate_persona returns PersonaInfo object."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/agents/personas/",
            method="POST",
            json=sample_persona_info_dict,
        )

        request = CreatePersonaRequest(
            name="DataAnalyst",
            description="An AI persona specialized in data analysis",
            prompt="You are a data analyst who helps users understand their data.",
        )

        persona = await async_client.acreate_persona(request)

        assert isinstance(persona, PersonaInfo)
        assert persona.name == "DataAnalyst"


class TestAsyncClientRequirement:
    """Tests for async client requirement."""

    def test_alist_personas_without_async_raises_error(self, client):
        """alist_personas raises RuntimeError without async enabled."""
        with pytest.raises(RuntimeError) as exc_info:
            import asyncio

            asyncio.get_event_loop().run_until_complete(client.alist_personas())

        assert "enable_async=True" in str(exc_info.value)

    def test_aget_persona_without_async_raises_error(self, client):
        """aget_persona raises RuntimeError without async enabled."""
        with pytest.raises(RuntimeError) as exc_info:
            import asyncio

            asyncio.get_event_loop().run_until_complete(client.aget_persona("test"))

        assert "enable_async=True" in str(exc_info.value)

    def test_acreate_persona_without_async_raises_error(self, client):
        """acreate_persona raises RuntimeError without async enabled."""
        with pytest.raises(RuntimeError) as exc_info:
            import asyncio

            request = CreatePersonaRequest(
                name="Test",
                description="Test",
                prompt="Test",
            )
            asyncio.get_event_loop().run_until_complete(client.acreate_persona(request))

        assert "enable_async=True" in str(exc_info.value)
