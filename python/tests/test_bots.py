"""Tests for bot operations in the Metadata AI SDK."""

import pytest
from pytest_httpx import HTTPXMock

from metadata_ai.client import MetadataAI
from metadata_ai.exceptions import BotNotFoundError
from metadata_ai.models import BotInfo


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
def sample_bot_info_dict():
    """Sample bot info as returned by API."""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "ingestion-bot",
        "displayName": "Ingestion Bot",
        "description": "Bot for data ingestion pipelines",
        "botUser": {
            "id": "user-123",
            "name": "ingestion-bot-user",
            "type": "user",
        },
    }


@pytest.fixture
def sample_bots_list_response(sample_bot_info_dict):
    """Sample list bots response as returned by API."""
    return {
        "data": [
            sample_bot_info_dict,
            {
                "id": "660e8400-e29b-41d4-a716-446655440001",
                "name": "dq-bot",
                "displayName": "Data Quality Bot",
                "description": "Bot for data quality operations",
                "botUser": None,
            },
        ]
    }


class TestListBots:
    """Tests for MetadataAI.list_bots() method."""

    def test_list_bots_returns_bot_info(
        self, client, httpx_mock: HTTPXMock, sample_bots_list_response
    ):
        """list_bots returns list of BotInfo objects."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/bots/?limit=10",
            json=sample_bots_list_response,
        )

        bots = client.list_bots()

        assert len(bots) == 2
        assert all(isinstance(b, BotInfo) for b in bots)
        assert bots[0].name == "ingestion-bot"
        assert bots[0].display_name == "Ingestion Bot"
        assert bots[1].name == "dq-bot"

    def test_list_bots_with_limit(self, client, httpx_mock: HTTPXMock):
        """list_bots passes limit param to API."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/bots/?limit=5",
            json={"data": []},
        )

        client.list_bots(limit=5)

        request = httpx_mock.get_request()
        assert "limit=5" in str(request.url)

    def test_list_bots_empty_response(self, client, httpx_mock: HTTPXMock):
        """list_bots handles empty response."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/bots/?limit=10",
            json={"data": []},
        )

        bots = client.list_bots()

        assert bots == []


class TestGetBot:
    """Tests for MetadataAI.get_bot() method."""

    def test_get_bot_returns_bot_info(self, client, httpx_mock: HTTPXMock, sample_bot_info_dict):
        """get_bot returns BotInfo object."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/bots/name/ingestion-bot",
            json=sample_bot_info_dict,
        )

        bot = client.get_bot("ingestion-bot")

        assert isinstance(bot, BotInfo)
        assert bot.name == "ingestion-bot"
        assert bot.display_name == "Ingestion Bot"
        assert bot.description == "Bot for data ingestion pipelines"
        assert bot.bot_user is not None

    def test_get_bot_not_found(self, client, httpx_mock: HTTPXMock):
        """get_bot raises BotNotFoundError on 404."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/bots/name/nonexistent-bot",
            status_code=404,
            json={"message": "Bot not found"},
        )

        with pytest.raises(BotNotFoundError) as exc_info:
            client.get_bot("nonexistent-bot")

        assert exc_info.value.bot_name == "nonexistent-bot"
        assert exc_info.value.status_code == 404


class TestAsyncListBots:
    """Tests for MetadataAI.alist_bots() method."""

    @pytest.mark.asyncio
    async def test_alist_bots_returns_bot_info(
        self, async_client, httpx_mock: HTTPXMock, sample_bots_list_response
    ):
        """alist_bots returns list of BotInfo objects."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/bots/?limit=10",
            json=sample_bots_list_response,
        )

        bots = await async_client.alist_bots()

        assert len(bots) == 2
        assert all(isinstance(b, BotInfo) for b in bots)
        assert bots[0].name == "ingestion-bot"

    @pytest.mark.asyncio
    async def test_alist_bots_without_async_enabled(self, client, httpx_mock: HTTPXMock):
        """alist_bots raises RuntimeError when async not enabled."""
        with pytest.raises(RuntimeError) as exc_info:
            await client.alist_bots()

        assert "enable_async=True" in str(exc_info.value)


class TestAsyncGetBot:
    """Tests for MetadataAI.aget_bot() method."""

    @pytest.mark.asyncio
    async def test_aget_bot_returns_bot_info(
        self, async_client, httpx_mock: HTTPXMock, sample_bot_info_dict
    ):
        """aget_bot returns BotInfo object."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/bots/name/ingestion-bot",
            json=sample_bot_info_dict,
        )

        bot = await async_client.aget_bot("ingestion-bot")

        assert isinstance(bot, BotInfo)
        assert bot.name == "ingestion-bot"

    @pytest.mark.asyncio
    async def test_aget_bot_not_found(self, async_client, httpx_mock: HTTPXMock):
        """aget_bot raises BotNotFoundError on 404."""
        httpx_mock.add_response(
            url="https://metadata.example.com/api/v1/bots/name/nonexistent-bot",
            status_code=404,
            json={"message": "Bot not found"},
        )

        with pytest.raises(BotNotFoundError) as exc_info:
            await async_client.aget_bot("nonexistent-bot")

        assert exc_info.value.bot_name == "nonexistent-bot"

    @pytest.mark.asyncio
    async def test_aget_bot_without_async_enabled(self, client, httpx_mock: HTTPXMock):
        """aget_bot raises RuntimeError when async not enabled."""
        with pytest.raises(RuntimeError) as exc_info:
            await client.aget_bot("any-bot")

        assert "enable_async=True" in str(exc_info.value)
