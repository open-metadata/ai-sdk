"""
Metadata AI SDK - Semantic Intelligence for AI builders.

This SDK provides a simple interface to invoke Metadata AI Agents
from your AI applications. Use it standalone or integrate with
LangChain, LlamaIndex, CrewAI, and other AI frameworks.

Standalone Usage:
    from ai_sdk.client import MetadataAI
    from ai_sdk.conversation import Conversation

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
    from ai_sdk.config import MetadataConfig
    from ai_sdk.client import MetadataAI

    # Load from METADATA_HOST and METADATA_TOKEN env vars
    config = MetadataConfig.from_env()
    client = MetadataAI.from_config(config)

Async Usage:
    from ai_sdk.client import MetadataAI

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
    # LangChain (pip install ai-sdk[langchain])
    from ai_sdk.integrations.langchain import MetadataAgentTool
    tool = MetadataAgentTool.from_client(client, "MyAgent")

    # More integrations coming: llamaindex, crewai, etc.

Import Guide:
    # Client and agent
    from ai_sdk.client import MetadataAI
    from ai_sdk.agent import AgentHandle

    # Configuration
    from ai_sdk.config import MetadataConfig

    # Conversation
    from ai_sdk.conversation import Conversation

    # Models
    from ai_sdk.models import (
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
    from ai_sdk.exceptions import (
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
    from ai_sdk._logging import set_debug, get_logger, configure_logging

    # Protocols (for mocking/testing)
    from ai_sdk.protocols import AgentProtocol
"""

from __future__ import annotations

__version__ = "0.1.0"

# Re-export main classes for convenient imports
from ai_sdk.client import MetadataAI
from ai_sdk.config import MetadataConfig
from ai_sdk.conversation import Conversation
from ai_sdk.exceptions import AbilityNotFoundError, BotNotFoundError, PersonaNotFoundError
from ai_sdk.models import (
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
    "Conversation",
    "CreateAgentRequest",
    "CreatePersonaRequest",
    "KnowledgeScope",
    "MetadataAI",
    "MetadataConfig",
    "PersonaInfo",
    "PersonaNotFoundError",
    "__version__",
]
