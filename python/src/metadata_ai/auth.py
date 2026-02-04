"""Authentication handling for the Metadata AI SDK."""

from __future__ import annotations


class TokenAuth:
    """JWT token authentication."""

    def __init__(self, token: str):
        """
        Initialize with a JWT token.

        Args:
            token: The JWT bot token for authentication
        """
        if not token:
            raise ValueError("Token cannot be empty")
        self._token = token

    @property
    def token(self) -> str:
        """Get the authentication token."""
        return self._token

    def get_headers(self) -> dict[str, str]:
        """Get authentication headers for API requests."""
        return {
            "Authorization": f"Bearer {self._token}",
        }
