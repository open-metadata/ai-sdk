"""LangChain integration for the Metadata AI SDK.

This module provides adapters for using Metadata agents as LangChain tools.

Usage:
    from metadata_ai.client import MetadataAI
    from metadata_ai.integrations.langchain import MetadataAgentTool, create_metadata_tools
    from langchain_openai import ChatOpenAI
    from langchain.agents import AgentExecutor, create_openai_functions_agent
    from langchain_core.prompts import ChatPromptTemplate

    # Create Metadata client
    client = MetadataAI(host="...", token="...")

    # Create tools for specific agents
    tools = [
        MetadataAgentTool.from_client(client, "DataQualityPlannerAgent"),
        MetadataAgentTool.from_client(client, "SqlQueryAgent"),
    ]

    # Or create tools for all API-enabled agents
    # tools = create_metadata_tools(client)

    # Set up LangChain agent
    llm = ChatOpenAI(model="gpt-4")
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a data analyst. Use tools to help with data tasks."),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    agent = create_openai_functions_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    # Run
    result = executor.invoke({"input": "Check data quality of customers table"})
"""

from __future__ import annotations

from typing import Any

from metadata_ai._logging import debug as _log_debug
from metadata_ai.exceptions import MetadataError

try:
    from langchain_core.callbacks import CallbackManagerForToolRun
    from langchain_core.tools import BaseTool
    from pydantic import BaseModel, Field
except ImportError as e:
    raise ImportError(
        "LangChain integration requires langchain-core. "
        "Install with: pip install metadata-ai[langchain]"
    ) from e

from metadata_ai.agent import AgentHandle
from metadata_ai.client import MetadataAI
from metadata_ai.models import AgentInfo


def _debug(msg: str) -> None:
    """Print debug message if debug is enabled."""
    _log_debug("LANGCHAIN DEBUG", msg)


class MetadataAgentInput(BaseModel):
    """Input schema for Metadata agent tool."""

    query: str = Field(description="The query or instruction for the Metadata agent")


class MetadataAgentTool(BaseTool):
    """
    LangChain tool that wraps a Metadata AI Agent.

    This tool allows using Metadata agents within LangChain pipelines,
    enabling semantic intelligence capabilities in your AI workflows.

    Example:
        from metadata_ai.client import MetadataAI
        from metadata_ai.integrations.langchain import MetadataAgentTool

        client = MetadataAI(host="...", token="...")
        tool = MetadataAgentTool.from_client(client, "DataQualityPlannerAgent")

        # Use in LangChain agent
        from langchain.agents import AgentExecutor, create_openai_functions_agent

        agent = create_openai_functions_agent(llm, [tool], prompt)
        executor = AgentExecutor(agent=agent, tools=[tool])
        result = executor.invoke({"input": "Check data quality"})
    """

    name: str = ""
    description: str = ""
    args_schema: type[BaseModel] = MetadataAgentInput

    # Agent handle - using private attribute pattern
    _agent_handle: AgentHandle
    _conversation_id: str | None = None

    def __init__(
        self,
        agent_handle: AgentHandle,
        name: str | None = None,
        description: str | None = None,
        **kwargs: Any,
    ):
        """
        Initialize the tool.

        Args:
            agent_handle: AgentHandle from MetadataAI client
            name: Optional custom tool name (defaults to agent name)
            description: Optional custom description
            **kwargs: Additional BaseTool arguments
        """
        # Try to get agent info, use fallback if not available
        agent_info = self._fetch_agent_info_safe(agent_handle)

        if agent_info is not None:
            default_name = f"metadata_{agent_info.name}"
            default_description = self._build_description(agent_info)
        else:
            default_name = f"metadata_{agent_handle.name}"
            default_description = f"Invoke Metadata agent: {agent_handle.name}"

        super().__init__(
            name=name or default_name,
            description=description or default_description,
            **kwargs,
        )
        self._agent_handle = agent_handle
        self._conversation_id = None

    @staticmethod
    def _fetch_agent_info_safe(agent_handle: AgentHandle) -> AgentInfo | None:
        """
        Fetch agent info with graceful fallback.

        Returns:
            AgentInfo if available, None otherwise
        """
        try:
            return agent_handle.get_info()
        except MetadataError:
            # Agent not found, not enabled, or network error
            return None

    @classmethod
    def from_agent(
        cls,
        agent_handle: AgentHandle,
        name: str | None = None,
        description: str | None = None,
    ) -> MetadataAgentTool:
        """
        Create a LangChain tool from a Metadata agent handle.

        Args:
            agent_handle: AgentHandle from MetadataAI.agent()
            name: Optional custom tool name
            description: Optional custom description

        Returns:
            MetadataAgentTool instance
        """
        return cls(agent_handle=agent_handle, name=name, description=description)

    @classmethod
    def from_client(
        cls,
        client: MetadataAI,
        agent_name: str,
        name: str | None = None,
        description: str | None = None,
    ) -> MetadataAgentTool:
        """
        Create a LangChain tool from client and agent name.

        Args:
            client: MetadataAI client instance
            agent_name: Name of the agent to wrap
            name: Optional custom tool name
            description: Optional custom description

        Returns:
            MetadataAgentTool instance
        """
        return cls(
            agent_handle=client.agent(agent_name),
            name=name,
            description=description,
        )

    def _build_description(self, info: AgentInfo) -> str:
        """Build tool description from agent info."""
        abilities_str = ", ".join(info.abilities) if info.abilities else "general"
        base_desc = info.description or f"Metadata agent: {info.display_name}"
        return f"{base_desc} Capabilities: {abilities_str}."

    def _run(
        self,
        query: str,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> str:
        """
        Execute the agent synchronously.

        Args:
            query: The query to send to the agent
            run_manager: LangChain callback manager

        Returns:
            Agent response as string
        """
        _debug("=== MetadataAgentTool._run() START ===")
        _debug(f"Tool name: {self.name}")
        _debug(f"Query received from LangChain: {query}")
        _debug(f"Current conversation_id: {self._conversation_id}")

        response = self._agent_handle.call(
            message=query,
            conversation_id=self._conversation_id,
        )

        _debug("Response from Metadata agent:")
        _debug(f"  conversation_id: {response.conversation_id}")
        _debug(f"  tools_used: {response.tools_used}")
        _debug(
            f"  response (first 500 chars): "
            f"{response.response[:500] if len(response.response) > 500 else response.response}"
        )
        _debug(f"  response (FULL):\n{response.response}")
        _debug("=== MetadataAgentTool._run() END ===")

        # Store conversation ID for multi-turn
        self._conversation_id = response.conversation_id
        return response.response

    async def _arun(
        self,
        query: str,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> str:
        """
        Execute the agent asynchronously.

        Args:
            query: The query to send to the agent
            run_manager: LangChain callback manager

        Returns:
            Agent response as string

        Note:
            For true async, the MetadataAI client must be created with
            enable_async=True. Otherwise falls back to sync execution.
        """
        # Check if async is available on the agent handle
        if self._agent_handle._async_http is not None:
            response = await self._agent_handle.acall(
                message=query,
                conversation_id=self._conversation_id,
            )
            self._conversation_id = response.conversation_id
            return response.response

        # Fallback to sync if async not available
        return self._run(query, run_manager)

    def reset_conversation(self) -> None:
        """Reset the conversation context for fresh interactions."""
        self._conversation_id = None


def create_metadata_tools(
    client: MetadataAI,
    agent_names: list[str] | None = None,
) -> list[MetadataAgentTool]:
    """
    Create LangChain tools for multiple Metadata agents.

    Args:
        client: MetadataAI client instance
        agent_names: List of agent names. If None, creates tools
            for all API-enabled agents.

    Returns:
        List of MetadataAgentTool instances

    Example:
        from metadata_ai.client import MetadataAI
        from metadata_ai.integrations.langchain import create_metadata_tools

        client = MetadataAI(host="...", token="...")

        # All API-enabled agents
        tools = create_metadata_tools(client)

        # Specific agents only
        tools = create_metadata_tools(client, [
            "DataQualityPlannerAgent",
            "SqlQueryAgent",
        ])
    """
    if agent_names is None:
        # Get all API-enabled agents
        agents = client.list_agents(limit=100)
        agent_names = [a.name for a in agents if a.api_enabled]

    return [MetadataAgentTool.from_client(client, name) for name in agent_names]
