"""Test URL encoding for name-based endpoints."""

import pytest
from unittest.mock import MagicMock
from metadata_ai.client import MetadataAI


def test_get_bot_encodes_name_with_slash():
    """Test that bot names with slashes are URL-encoded."""
    client = MetadataAI(host="https://test.com", token="test-token")
    client._bots_http = MagicMock()
    client._bots_http.get.return_value = {"id": "123", "name": "test/bot"}

    client.get_bot("test/bot")

    client._bots_http.get.assert_called_once()
    call_args = client._bots_http.get.call_args
    # The path should contain %2F (encoded slash)
    assert "test%2Fbot" in call_args[0][0]


def test_get_bot_encodes_name_with_spaces():
    """Test that bot names with spaces are URL-encoded."""
    client = MetadataAI(host="https://test.com", token="test-token")
    client._bots_http = MagicMock()
    client._bots_http.get.return_value = {"id": "123", "name": "my bot"}

    client.get_bot("my bot")

    client._bots_http.get.assert_called_once()
    call_args = client._bots_http.get.call_args
    # The path should contain %20 (encoded space)
    assert "my%20bot" in call_args[0][0]


def test_get_persona_encodes_name_with_special_chars():
    """Test that persona names with special chars are URL-encoded."""
    client = MetadataAI(host="https://test.com", token="test-token")
    client._personas_http = MagicMock()
    client._personas_http.get.return_value = {"id": "123", "name": "test&persona", "provider": "user"}

    client.get_persona("test&persona")

    client._personas_http.get.assert_called_once()
    call_args = client._personas_http.get.call_args
    # The path should contain %26 (encoded ampersand)
    assert "test%26persona" in call_args[0][0]
