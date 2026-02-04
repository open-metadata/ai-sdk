"""Tests for the MetadataConfig configuration module."""

import pytest

from metadata_ai.config import MetadataConfig


class TestMetadataConfigInit:
    """Tests for MetadataConfig initialization."""

    def test_default_values(self):
        """Config provides sensible defaults."""
        config = MetadataConfig(
            host="https://metadata.example.com",
            token="test-token",
        )

        assert config.host == "https://metadata.example.com"
        assert config.token == "test-token"
        assert config.timeout == 120.0
        assert config.verify_ssl is True
        assert config.enable_async is False
        assert config.max_retries == 3

    def test_strips_trailing_slash(self):
        """Config strips trailing slash from host."""
        config = MetadataConfig(host="https://metadata.example.com/", token="test-token")
        assert config.host == "https://metadata.example.com"

    def test_validation_errors(self):
        """Config validates required fields and constraints."""
        with pytest.raises(ValueError, match="host cannot be empty"):
            MetadataConfig(host="", token="test-token")

        with pytest.raises(ValueError, match="token cannot be empty"):
            MetadataConfig(host="https://example.com", token="")

        with pytest.raises(ValueError, match="timeout must be positive"):
            MetadataConfig(host="https://example.com", token="test", timeout=-1)

        with pytest.raises(ValueError, match="max_retries cannot be negative"):
            MetadataConfig(host="https://example.com", token="test", max_retries=-1)


class TestMetadataConfigFromEnv:
    """Tests for MetadataConfig.from_env()."""

    def test_from_env_reads_env_vars(self, monkeypatch):
        """from_env reads required and optional env vars."""
        monkeypatch.setenv("METADATA_HOST", "https://metadata.example.com")
        monkeypatch.setenv("METADATA_TOKEN", "env-token")
        monkeypatch.setenv("METADATA_TIMEOUT", "60")
        monkeypatch.setenv("METADATA_VERIFY_SSL", "false")
        monkeypatch.setenv("METADATA_DEBUG", "true")

        config = MetadataConfig.from_env()

        assert config.host == "https://metadata.example.com"
        assert config.token == "env-token"
        assert config.timeout == 60.0
        assert config.verify_ssl is False
        assert config.debug is True

    def test_from_env_custom_prefix(self, monkeypatch):
        """from_env supports custom prefix."""
        monkeypatch.setenv("MY_APP_HOST", "https://my.example.com")
        monkeypatch.setenv("MY_APP_TOKEN", "my-token")

        config = MetadataConfig.from_env(prefix="MY_APP")

        assert config.host == "https://my.example.com"
        assert config.token == "my-token"

    def test_from_env_with_overrides(self, monkeypatch):
        """from_env allows explicit overrides over env vars."""
        monkeypatch.setenv("METADATA_HOST", "https://env.example.com")
        monkeypatch.setenv("METADATA_TOKEN", "env-token")
        monkeypatch.setenv("METADATA_TIMEOUT", "60")

        config = MetadataConfig.from_env(timeout=30.0)

        assert config.timeout == 30.0  # Override takes precedence

    def test_from_env_missing_required_vars(self, monkeypatch):
        """from_env raises on missing required env vars."""
        monkeypatch.delenv("METADATA_HOST", raising=False)
        monkeypatch.delenv("METADATA_TOKEN", raising=False)

        with pytest.raises(ValueError, match="Missing METADATA_HOST"):
            MetadataConfig.from_env()

        monkeypatch.setenv("METADATA_HOST", "https://example.com")
        with pytest.raises(ValueError, match="Missing METADATA_TOKEN"):
            MetadataConfig.from_env()


class TestMetadataConfigWithOverrides:
    """Tests for MetadataConfig.with_overrides()."""

    def test_creates_new_immutable_config(self):
        """with_overrides creates new config without modifying original."""
        config = MetadataConfig(
            host="https://example.com",
            token="original-token",
            timeout=120.0,
            verify_ssl=False,
        )

        new_config = config.with_overrides(timeout=60.0, enable_async=True)

        assert new_config is not config
        assert new_config.timeout == 60.0
        assert new_config.enable_async is True
        assert new_config.verify_ssl is False  # Preserved
        assert config.timeout == 120.0  # Original unchanged


class TestMetadataConfigUserAgent:
    """Tests for user_agent configuration."""

    def test_user_agent_passed_through_from_config(self):
        """Test that user_agent from config is passed to HTTP clients."""
        from metadata_ai.client import MetadataAI

        config = MetadataConfig(
            host="https://test.com",
            token="test-token",
            user_agent="my-custom-agent/1.0",
        )

        client = MetadataAI.from_config(config)

        assert client._http._user_agent == "my-custom-agent/1.0"
        assert client._admin_http._user_agent == "my-custom-agent/1.0"
        assert client._personas_http._user_agent == "my-custom-agent/1.0"
        assert client._bots_http._user_agent == "my-custom-agent/1.0"

    def test_user_agent_default_when_not_specified(self):
        """Test that default user_agent is used when not specified."""
        from metadata_ai.client import MetadataAI

        config = MetadataConfig(
            host="https://test.com",
            token="test-token",
        )

        client = MetadataAI.from_config(config)

        # Default user agent should be used
        assert "metadata-ai-sdk" in client._http._user_agent

    def test_user_agent_from_env(self, monkeypatch):
        """Test that user_agent can be set from environment variable."""
        monkeypatch.setenv("METADATA_HOST", "https://test.com")
        monkeypatch.setenv("METADATA_TOKEN", "test-token")
        monkeypatch.setenv("METADATA_USER_AGENT", "env-custom-agent/2.0")

        config = MetadataConfig.from_env()

        assert config.user_agent == "env-custom-agent/2.0"

    def test_user_agent_passed_to_async_clients(self):
        """Test that user_agent is passed to async HTTP clients when enabled."""
        from metadata_ai.client import MetadataAI

        config = MetadataConfig(
            host="https://test.com",
            token="test-token",
            user_agent="async-custom-agent/1.0",
            enable_async=True,
        )

        client = MetadataAI.from_config(config)

        assert client._async_http._user_agent == "async-custom-agent/1.0"
        assert client._async_admin_http._user_agent == "async-custom-agent/1.0"
        assert client._async_personas_http._user_agent == "async-custom-agent/1.0"
        assert client._async_bots_http._user_agent == "async-custom-agent/1.0"
