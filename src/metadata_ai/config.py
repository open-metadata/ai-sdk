"""Configuration for the Metadata AI SDK.

This module provides a configuration object pattern for cleaner
client initialization and environment-based configuration.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass
class MetadataConfig:
    """
    Configuration for MetadataAI client.

    This provides a cleaner way to configure the client, especially
    when loading from environment variables or configuration files.

    Usage:
        # From environment variables
        config = MetadataConfig.from_env()
        client = MetadataAI.from_config(config)

        # Explicit configuration
        config = MetadataConfig(
            host="https://metadata.example.com",
            token="your-token",
            timeout=60.0,
        )
        client = MetadataAI.from_config(config)

        # Override environment with explicit values
        config = MetadataConfig.from_env(timeout=30.0, enable_async=True)
    """

    host: str
    token: str
    timeout: float = 120.0
    verify_ssl: bool = True
    enable_async: bool = False
    max_retries: int = 3
    retry_delay: float = 1.0
    user_agent: str | None = None
    debug: bool = False

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if not self.host:
            raise ValueError("host cannot be empty")
        if not self.token:
            raise ValueError("token cannot be empty")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")

        # Normalize host
        self.host = self.host.rstrip("/")

    @classmethod
    def from_env(
        cls,
        prefix: str = "METADATA",
        **overrides: Any,
    ) -> MetadataConfig:
        """
        Create configuration from environment variables.

        Environment variables:
            {PREFIX}_HOST: Metadata server URL (required)
            {PREFIX}_TOKEN: JWT bot token (required)
            {PREFIX}_TIMEOUT: Request timeout in seconds (default: 120)
            {PREFIX}_VERIFY_SSL: Verify SSL certificates (default: true)
            {PREFIX}_DEBUG: Enable debug logging (default: false)

        Args:
            prefix: Environment variable prefix (default: "METADATA")
            **overrides: Explicit values that override environment

        Returns:
            MetadataConfig instance

        Raises:
            ValueError: If required environment variables are missing
        """

        def get_env(name: str, default: str | None = None) -> str | None:
            return os.environ.get(f"{prefix}_{name}", default)

        def get_bool(name: str, default: bool) -> bool:
            value = get_env(name)
            if value is None:
                return default
            return value.lower() in ("true", "1", "yes")

        def get_float(name: str, default: float) -> float:
            value = get_env(name)
            if value is None:
                return default
            return float(value)

        def get_int(name: str, default: int) -> int:
            value = get_env(name)
            if value is None:
                return default
            return int(value)

        # Get values from environment, allow overrides
        host = overrides.get("host") or get_env("HOST")
        token = overrides.get("token") or get_env("TOKEN")

        if not host:
            raise ValueError(
                f"Missing {prefix}_HOST environment variable. Set it to your Metadata server URL."
            )
        if not token:
            raise ValueError(
                f"Missing {prefix}_TOKEN environment variable. Set it to your bot JWT token."
            )

        return cls(
            host=host,
            token=token,
            timeout=overrides.get("timeout", get_float("TIMEOUT", 120.0)),
            verify_ssl=overrides.get("verify_ssl", get_bool("VERIFY_SSL", True)),
            enable_async=overrides.get("enable_async", get_bool("ASYNC", False)),
            max_retries=overrides.get("max_retries", get_int("MAX_RETRIES", 3)),
            retry_delay=overrides.get("retry_delay", get_float("RETRY_DELAY", 1.0)),
            user_agent=overrides.get("user_agent", get_env("USER_AGENT")),
            debug=overrides.get("debug", get_bool("DEBUG", False)),
        )

    def with_overrides(self, **kwargs: Any) -> MetadataConfig:
        """
        Create a new config with some values overridden.

        Args:
            **kwargs: Values to override

        Returns:
            New MetadataConfig with overrides applied
        """
        return MetadataConfig(
            host=kwargs.get("host", self.host),
            token=kwargs.get("token", self.token),
            timeout=kwargs.get("timeout", self.timeout),
            verify_ssl=kwargs.get("verify_ssl", self.verify_ssl),
            enable_async=kwargs.get("enable_async", self.enable_async),
            max_retries=kwargs.get("max_retries", self.max_retries),
            retry_delay=kwargs.get("retry_delay", self.retry_delay),
            user_agent=kwargs.get("user_agent", self.user_agent),
            debug=kwargs.get("debug", self.debug),
        )
