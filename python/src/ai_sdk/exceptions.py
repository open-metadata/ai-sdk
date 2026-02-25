"""Exceptions for the AI SDK."""

from __future__ import annotations


class AISdkError(Exception):
    """Base exception for AI SDK."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AuthenticationError(AISdkError):
    """Invalid or expired token."""

    def __init__(self, message: str = "Invalid or expired authentication token"):
        super().__init__(message, status_code=401)


class AgentNotFoundError(AISdkError):
    """Agent does not exist."""

    def __init__(self, agent_name: str):
        super().__init__(f"Agent not found: {agent_name}", status_code=404)
        self.agent_name = agent_name


class AgentNotEnabledError(AISdkError):
    """Agent exists but is not API-enabled."""

    def __init__(self, agent_name: str):
        super().__init__(
            f"Agent '{agent_name}' is not enabled for API access. "
            "Set apiEnabled=true on the agent to enable SDK access.",
            status_code=403,
        )
        self.agent_name = agent_name


class RateLimitError(AISdkError):
    """Rate limit exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int | None = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class AgentExecutionError(AISdkError):
    """Error during agent execution."""

    def __init__(self, message: str, agent_name: str | None = None, status_code: int = 500):
        super().__init__(message, status_code=status_code)
        self.agent_name = agent_name


class BotNotFoundError(AISdkError):
    """Bot does not exist."""

    def __init__(self, bot_name: str):
        super().__init__(f"Bot not found: {bot_name}", status_code=404)
        self.bot_name = bot_name


class PersonaNotFoundError(AISdkError):
    """Raised when a persona is not found."""

    def __init__(self, persona_name: str):
        super().__init__(f"Persona not found: {persona_name}", status_code=404)
        self.persona_name = persona_name


class AbilityNotFoundError(AISdkError):
    """Raised when an ability is not found."""

    def __init__(self, ability_name: str):
        super().__init__(
            f"Ability not found: {ability_name}",
            status_code=404,
        )
        self.ability_name = ability_name


class MCPError(AISdkError):
    """Base error for MCP operations."""


class MCPToolExecutionError(MCPError):
    """Tool execution failed."""

    def __init__(self, tool: str, message: str) -> None:
        self.tool = tool
        super().__init__(f"Tool '{tool}' failed: {message}")
