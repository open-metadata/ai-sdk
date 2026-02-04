"""
Metadata AI SDK - Semantic Intelligence for AI builders.

This SDK provides a simple interface to invoke Metadata AI Agents
from your AI applications. Use it standalone or integrate with
LangChain, LlamaIndex, CrewAI, and other AI frameworks.

Standalone Usage:
    from metadata_ai.client import MetadataAI
    from metadata_ai.conversation import Conversation

    # Initialize client
    client = MetadataAI(
        host="https://metadata.example.com",
        token="your-bot-jwt-token"
    )

    # Simple invocation
    response = client.agent("DataQualityPlannerAgent").call(
        "What data quality tests should I add for the customers table?"
    )
    print(response.response)

    # Multi-turn conversation (self-service, no frameworks needed)
    conv = Conversation(client.agent("DataQualityPlannerAgent"))
    print(conv.send("Analyze the customers table"))
    print(conv.send("Now create tests for the issues you found"))

    # Streaming
    for event in client.agent("SqlQueryAgent").stream(
        "Generate a query to find duplicate customer records"
    ):
        if event.type == "content":
            print(event.content, end="", flush=True)

Environment-based Configuration:
    from metadata_ai.config import MetadataConfig
    from metadata_ai.client import MetadataAI

    # Load from METADATA_HOST and METADATA_TOKEN env vars
    config = MetadataConfig.from_env()
    client = MetadataAI.from_config(config)

Async Usage:
    from metadata_ai.client import MetadataAI

    client = MetadataAI(
        host="https://metadata.example.com",
        token="your-bot-jwt-token",
        enable_async=True
    )

    response = await client.agent("DataQualityPlannerAgent").acall(
        "What data quality tests should I add?"
    )
    print(response.response)

Framework Integrations:
    # LangChain (pip install metadata-ai[langchain])
    from metadata_ai.integrations.langchain import MetadataAgentTool
    tool = MetadataAgentTool.from_client(client, "MyAgent")

    # More integrations coming: llamaindex, crewai, etc.

Import Guide:
    # Client and agent
    from metadata_ai.client import MetadataAI
    from metadata_ai.agent import AgentHandle

    # Configuration
    from metadata_ai.config import MetadataConfig

    # Conversation
    from metadata_ai.conversation import Conversation

    # Models
    from metadata_ai.models import (
        AbilityInfo,
        AgentInfo,
        BotInfo,
        CreateAgentRequest,
        CreatePersonaRequest,
        EntityReference,
        EventType,
        InvokeRequest,
        InvokeResponse,
        KnowledgeScope,
        PersonaInfo,
        StreamEvent,
        Usage,
    )

    # Exceptions
    from metadata_ai.exceptions import (
        AbilityNotFoundError,
        AgentExecutionError,
        AgentNotEnabledError,
        AgentNotFoundError,
        AuthenticationError,
        BotNotFoundError,
        MetadataError,
        PersonaNotFoundError,
        RateLimitError,
    )

    # Logging
    from metadata_ai._logging import set_debug, get_logger, configure_logging

    # Protocols (for mocking/testing)
    from metadata_ai.protocols import AgentProtocol
"""

from __future__ import annotations

__version__ = "0.1.0"

# Re-export main classes for convenient imports
from metadata_ai.client import MetadataAI
from metadata_ai.config import MetadataConfig
from metadata_ai.conversation import Conversation
from metadata_ai.exceptions import AbilityNotFoundError, BotNotFoundError, PersonaNotFoundError
from metadata_ai.models import (
    AbilityInfo,
    BotInfo,
    CreateAgentRequest,
    CreatePersonaRequest,
    KnowledgeScope,
    PersonaInfo,
)

__all__ = [
    "AbilityInfo",
    "AbilityNotFoundError",
    "BotInfo",
    "BotNotFoundError",
    "MetadataAI",
    "MetadataConfig",
    "Conversation",
    "CreateAgentRequest",
    "CreatePersonaRequest",
    "KnowledgeScope",
    "PersonaInfo",
    "PersonaNotFoundError",
    "__version__",
]
