"""Tests for the Metadata AI SDK exceptions."""

from ai_sdk.exceptions import (
    AgentExecutionError,
    AgentNotEnabledError,
    AgentNotFoundError,
    AuthenticationError,
    MetadataError,
    RateLimitError,
)


class TestMetadataError:
    """Tests for base MetadataError."""

    def test_stores_message_and_status_code(self):
        """MetadataError stores message and status code."""
        error = MetadataError("Something went wrong", status_code=500)

        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.status_code == 500


class TestAuthenticationError:
    """Tests for AuthenticationError."""

    def test_defaults(self):
        """AuthenticationError has sensible defaults."""
        error = AuthenticationError()

        assert error.status_code == 401
        assert "authentication" in str(error).lower() or "token" in str(error).lower()


class TestAgentNotFoundError:
    """Tests for AgentNotFoundError."""

    def test_includes_agent_name(self):
        """AgentNotFoundError includes agent name in message."""
        error = AgentNotFoundError("DataQualityAgent")

        assert "DataQualityAgent" in str(error)
        assert error.agent_name == "DataQualityAgent"
        assert error.status_code == 404


class TestAgentNotEnabledError:
    """Tests for AgentNotEnabledError."""

    def test_includes_agent_name_and_hint(self):
        """AgentNotEnabledError includes agent name and apiEnabled hint."""
        error = AgentNotEnabledError("InternalAgent")

        assert "InternalAgent" in str(error)
        assert "apiEnabled" in str(error)
        assert error.agent_name == "InternalAgent"
        assert error.status_code == 403


class TestRateLimitError:
    """Tests for RateLimitError."""

    def test_stores_retry_after(self):
        """RateLimitError stores retry_after value."""
        error = RateLimitError("Slow down", retry_after=60)

        assert error.retry_after == 60
        assert error.status_code == 429


class TestAgentExecutionError:
    """Tests for AgentExecutionError."""

    def test_stores_agent_name(self):
        """AgentExecutionError stores optional agent name."""
        error = AgentExecutionError("Execution failed", agent_name="FailingAgent")

        assert str(error) == "Execution failed"
        assert error.agent_name == "FailingAgent"
        assert error.status_code == 500
