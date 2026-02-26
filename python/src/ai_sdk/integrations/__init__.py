"""
Integrations for the AI SDK with popular AI frameworks.

Available integrations:

- **langchain**: LangChain tool wrapper
  Install: pip install data-ai-sdk[langchain]
  Usage:
      from ai_sdk.integrations.langchain import AISdkAgentTool

- **llamaindex**: LlamaIndex tool wrapper (coming soon)
  Install: pip install data-ai-sdk[llamaindex]

- **crewai**: CrewAI tool wrapper (coming soon)
  Install: pip install data-ai-sdk[crewai]

All integrations extend the BaseAgentWrapper class which provides:
- Agent info fetching with graceful fallback
- Automatic description building from abilities
- Conversation ID management for multi-turn
- Both sync and async invocation support

Creating a new integration:

    from ai_sdk.integrations.base import BaseAgentWrapper
    from ai_sdk.models import AgentInfo

    class MyFrameworkTool(BaseAgentWrapper):
        def _default_name(self, info: AgentInfo) -> str:
            return f"myframework_{info.name}"

        # Implement framework-specific interface methods
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# Base class is always available
from ai_sdk.integrations.base import BaseAgentWrapper as BaseAgentWrapper

if TYPE_CHECKING:
    # For type checking only - these may not be installed
    from ai_sdk.integrations import langchain as langchain

# Lazy loading of integrations to avoid import errors for missing deps
_INTEGRATION_MODULES = {
    "langchain": "ai_sdk.integrations.langchain",
    # "llamaindex": "ai_sdk.integrations.llamaindex",  # Coming soon
    # "crewai": "ai_sdk.integrations.crewai",          # Coming soon
}


def __getattr__(name: str) -> object:
    """
    Lazy import integrations to avoid import errors for missing dependencies.

    This allows users to import the integrations module without having
    all optional dependencies installed.
    """
    if name in _INTEGRATION_MODULES:
        import importlib

        try:
            module = importlib.import_module(_INTEGRATION_MODULES[name])
            globals()[name] = module
            return module
        except ImportError as e:
            raise ImportError(
                f"Integration '{name}' requires additional dependencies. "
                f"Install with: pip install data-ai-sdk[{name}]"
            ) from e

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
