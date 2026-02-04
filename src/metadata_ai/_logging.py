"""Logging configuration for the Metadata AI SDK.

This module provides proper Python logging integration.

Usage:
    # Get the SDK logger
    from metadata_ai._logging import get_logger

    logger = get_logger(__name__)
    logger.info("Processing request")
    logger.debug("Request details: %s", details)

    # Enable debug logging globally
    from metadata_ai._logging import set_debug
    set_debug(True)

    # Or configure logging directly
    import logging
    logging.getLogger("metadata_ai").setLevel(logging.DEBUG)
"""

from __future__ import annotations

import logging
import sys

# Create the SDK root logger
_SDK_LOGGER_NAME = "metadata_ai"
_sdk_logger = logging.getLogger(_SDK_LOGGER_NAME)

# Default handler (only added if no handlers exist)
_default_handler: logging.Handler | None = None

# Legacy debug flag for backward compatibility
_debug_enabled = False


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a module within the SDK.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("Starting operation")
    """
    # Ensure it's a child of the SDK logger
    if not name.startswith(_SDK_LOGGER_NAME):
        name = f"{_SDK_LOGGER_NAME}.{name}"
    return logging.getLogger(name)


def set_debug(enabled: bool) -> None:
    """
    Enable or disable debug logging for the SDK.

    This is the recommended way to enable verbose logging during development.

    Args:
        enabled: True to enable debug logging, False to disable

    Example:
        from metadata_ai._logging import set_debug
        set_debug(True)  # Enable debug logging
    """
    global _debug_enabled, _default_handler

    _debug_enabled = enabled

    if enabled:
        _sdk_logger.setLevel(logging.DEBUG)

        # Add a default handler if none exists
        if not _sdk_logger.handlers and _default_handler is None:
            _default_handler = logging.StreamHandler(sys.stderr)
            _default_handler.setLevel(logging.DEBUG)
            _default_handler.setFormatter(
                logging.Formatter("[%(name)s] %(levelname)s: %(message)s")
            )
            _sdk_logger.addHandler(_default_handler)
    else:
        _sdk_logger.setLevel(logging.WARNING)

        # Remove default handler if we added it
        if _default_handler is not None:
            _sdk_logger.removeHandler(_default_handler)
            _default_handler = None


def is_debug_enabled() -> bool:
    """
    Check if debug logging is enabled.

    Returns:
        True if debug logging is enabled
    """
    return _debug_enabled


def debug(prefix: str, msg: str) -> None:
    """
    Legacy debug function for backward compatibility.

    New code should use get_logger() instead.

    Args:
        prefix: Debug message prefix (e.g., "HTTP DEBUG")
        msg: Debug message
    """
    if _debug_enabled:
        _sdk_logger.debug("[%s] %s", prefix, msg)


def configure_logging(
    level: int = logging.INFO,
    format_string: str | None = None,
    handler: logging.Handler | None = None,
) -> None:
    """
    Configure SDK logging with custom settings.

    This is useful for integrating with your application's logging setup.

    Args:
        level: Logging level (default: INFO)
        format_string: Custom format string (optional)
        handler: Custom handler to use (optional)

    Example:
        from metadata_ai._logging import configure_logging
        import logging

        # Use custom format
        configure_logging(
            level=logging.DEBUG,
            format_string="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Or use your own handler
        handler = logging.FileHandler("metadata.log")
        configure_logging(handler=handler)
    """
    global _default_handler

    _sdk_logger.setLevel(level)

    # Remove existing default handler
    if _default_handler is not None:
        _sdk_logger.removeHandler(_default_handler)
        _default_handler = None

    if handler is not None:
        _sdk_logger.addHandler(handler)
    elif not _sdk_logger.handlers:
        # Add default handler with custom format
        _default_handler = logging.StreamHandler(sys.stderr)
        _default_handler.setLevel(level)

        fmt = format_string or "[%(name)s] %(levelname)s: %(message)s"
        _default_handler.setFormatter(logging.Formatter(fmt))

        _sdk_logger.addHandler(_default_handler)
