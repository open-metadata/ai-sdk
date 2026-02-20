"""Tests for the AiSdkConfig configuration module."""

import pytest

from ai_sdk.config import AiSdkConfig


class TestAiSdkConfigInit:
    """Tests for AiSdkConfig initialization."""

    def test_default_values(self):
        """Config provides sensible defaults."""
        config = AiSdkConfig(
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
        config = AiSdkConfig(host="https://metadata.example.com/", token="test-token")
        assert config.host == "https://metadata.example.com"

    def test_validation_errors(self):
        """Config validates required fields and constraints."""
        with pytest.raises(ValueError, match="host cannot be empty"):
            AiSdkConfig(host="", token="test-token")

        with pytest.raises(ValueError, match="token cannot be empty"):
            AiSdkConfig(host="https://example.com", token="")

        with pytest.raises(ValueError, match="timeout must be positive"):
            AiSdkConfig(host="https://example.com", token="test", timeout=-1)

        with pytest.raises(ValueError, match="max_retries cannot be negative"):
            AiSdkConfig(host="https://example.com", token="test", max_retries=-1)


class TestAiSdkConfigFromEnv:
    """Tests for AiSdkConfig.from_env()."""

    def test_from_env_reads_env_vars(self, monkeypatch):
        """from_env reads required and optional env vars."""
        monkeypatch.setenv("AI_SDK_HOST", "https://metadata.example.com")
        monkeypatch.setenv("AI_SDK_TOKEN", "env-token")
        monkeypatch.setenv("AI_SDK_TIMEOUT", "60")
        monkeypatch.setenv("AI_SDK_VERIFY_SSL", "false")
        monkeypatch.setenv("AI_SDK_DEBUG", "true")

        config = AiSdkConfig.from_env()

        assert config.host == "https://metadata.example.com"
        assert config.token == "env-token"
        assert config.timeout == 60.0
        assert config.verify_ssl is False
        assert config.debug is True

    def test_from_env_custom_prefix(self, monkeypatch):
        """from_env supports custom prefix."""
        monkeypatch.setenv("MY_APP_HOST", "https://my.example.com")
        monkeypatch.setenv("MY_APP_TOKEN", "my-token")

        config = AiSdkConfig.from_env(prefix="MY_APP")

        assert config.host == "https://my.example.com"
        assert config.token == "my-token"

    def test_from_env_with_overrides(self, monkeypatch):
        """from_env allows explicit overrides over env vars."""
        monkeypatch.setenv("AI_SDK_HOST", "https://env.example.com")
        monkeypatch.setenv("AI_SDK_TOKEN", "env-token")
        monkeypatch.setenv("AI_SDK_TIMEOUT", "60")

        config = AiSdkConfig.from_env(timeout=30.0)

        assert config.timeout == 30.0  # Override takes precedence

    def test_from_env_missing_required_vars(self, monkeypatch):
        """from_env raises on missing required env vars."""
        monkeypatch.delenv("AI_SDK_HOST", raising=False)
        monkeypatch.delenv("AI_SDK_TOKEN", raising=False)

        with pytest.raises(ValueError, match="Missing AI_SDK_HOST"):
            AiSdkConfig.from_env()

        monkeypatch.setenv("AI_SDK_HOST", "https://example.com")
        with pytest.raises(ValueError, match="Missing AI_SDK_TOKEN"):
            AiSdkConfig.from_env()


class TestAiSdkConfigWithOverrides:
    """Tests for AiSdkConfig.with_overrides()."""

    def test_creates_new_immutable_config(self):
        """with_overrides creates new config without modifying original."""
        config = AiSdkConfig(
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


class TestAiSdkConfigUserAgent:
    """Tests for user_agent configuration."""

    def test_user_agent_passed_through_from_config(self):
        """Test that user_agent from config is passed to HTTP clients."""
        from ai_sdk.client import AiSdk

        config = AiSdkConfig(
            host="https://test.com",
            token="test-token",
            user_agent="my-custom-agent/1.0",
        )

        client = AiSdk.from_config(config)

        assert client._http._user_agent == "my-custom-agent/1.0"
        assert client._personas_http._user_agent == "my-custom-agent/1.0"
        assert client._bots_http._user_agent == "my-custom-agent/1.0"

    def test_user_agent_default_when_not_specified(self):
        """Test that default user_agent is used when not specified."""
        from ai_sdk.client import AiSdk

        config = AiSdkConfig(
            host="https://test.com",
            token="test-token",
        )

        client = AiSdk.from_config(config)

        # Default user agent should be used
        assert "ai-sdk-sdk" in client._http._user_agent

    def test_user_agent_from_env(self, monkeypatch):
        """Test that user_agent can be set from environment variable."""
        monkeypatch.setenv("AI_SDK_HOST", "https://test.com")
        monkeypatch.setenv("AI_SDK_TOKEN", "test-token")
        monkeypatch.setenv("AI_SDK_USER_AGENT", "env-custom-agent/2.0")

        config = AiSdkConfig.from_env()

        assert config.user_agent == "env-custom-agent/2.0"

    def test_user_agent_passed_to_async_clients(self):
        """Test that user_agent is passed to async HTTP clients when enabled."""
        from ai_sdk.client import AiSdk

        config = AiSdkConfig(
            host="https://test.com",
            token="test-token",
            user_agent="async-custom-agent/1.0",
            enable_async=True,
        )

        client = AiSdk.from_config(config)

        assert client._async_http._user_agent == "async-custom-agent/1.0"
        assert client._async_personas_http._user_agent == "async-custom-agent/1.0"
        assert client._async_bots_http._user_agent == "async-custom-agent/1.0"
