"""Tests for the Metadata AI SDK authentication."""

import pytest

from ai_sdk.auth import TokenAuth


class TestTokenAuth:
    """Tests for TokenAuth."""

    def test_empty_token_raises(self):
        """TokenAuth rejects empty token."""
        with pytest.raises(ValueError, match="empty"):
            TokenAuth("")

    def test_get_headers_returns_bearer_format(self):
        """get_headers returns properly formatted Bearer token."""
        auth = TokenAuth("my-jwt-token")
        headers = auth.get_headers()

        assert headers == {"Authorization": "Bearer my-jwt-token"}
