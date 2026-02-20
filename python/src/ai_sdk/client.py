"""Main client for the AI SDK."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

if TYPE_CHECKING:
    from ai_sdk._http import AsyncHTTPClient as AsyncHttpClient, HTTPClient as HttpClient
    from ai_sdk.config import AiSdkConfig

from ai_sdk._http import AsyncHTTPClient, HTTPClient
from ai_sdk.agent import AgentHandle
from ai_sdk.auth import TokenAuth
from ai_sdk.exceptions import (
    AbilityNotFoundError,
    AiSdkError,
    PersonaNotFoundError,
)
from ai_sdk.mcp._client import MCPClient
from ai_sdk.models import (
    AbilityInfo,
    AgentInfo,
    BotInfo,
    CreateAgentRequest,
    CreatePersonaRequest,
    PersonaInfo,
)


class AiSdk:
    """
    Main client for interacting with AI agents.

    This client provides access to AI Agents, enabling you to
    leverage semantic intelligence capabilities in your AI applications.

    Usage:
        from ai_sdk.client import AiSdk

        client = AiSdk(
            host="https://metadata.example.com",
            token="your-bot-jwt-token"
        )

        # Get an agent handle
        agent = client.agent("DataQualityPlannerAgent")

        # Invoke synchronously
        response = agent.call("Analyze the customers table")
        print(response.response)

        # Or stream the response
        for event in agent.stream("Analyze the customers table"):
            if event.type == "content":
                print(event.content, end="", flush=True)

    Multi-turn conversations:
        # Start a conversation
        response1 = agent.call("Analyze the orders table")

        # Continue with context
        response2 = agent.call(
            "Now create tests for the issues you found",
            conversation_id=response1.conversation_id
        )

    Async usage:
        client = AiSdk(
            host="https://metadata.example.com",
            token="your-bot-jwt-token",
            enable_async=True
        )

        agent = client.agent("DataQualityPlannerAgent")
        response = await agent.acall("Analyze the customers table")

    From environment:
        from ai_sdk.client import AiSdk
        from ai_sdk.config import AiSdkConfig

        config = AiSdkConfig.from_env()  # Uses AI_SDK_HOST, AI_SDK_TOKEN
        client = AiSdk.from_config(config)
    """

    def __init__(
        self,
        host: str,
        token: str,
        timeout: float = 120.0,
        verify_ssl: bool = True,
        enable_async: bool = False,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        user_agent: str | None = None,
    ):
        """
        Initialize the AI SDK client.

        Args:
            host: The server URL (e.g., "https://metadata.example.com")
            token: JWT bot token for authentication
            timeout: Request timeout in seconds (default: 120)
            verify_ssl: Whether to verify SSL certificates (default: True)
            enable_async: Enable async operations (default: False)
            max_retries: Maximum number of retry attempts for transient errors (default: 3)
            retry_delay: Base delay between retries in seconds (default: 1.0)
            user_agent: Custom User-Agent string for HTTP requests

        Raises:
            ValueError: If token is empty
        """
        self._host = host.rstrip("/")
        self._auth = TokenAuth(token)
        self._enable_async = enable_async

        # Unified HTTP client for all agent operations (consolidated API)
        agents_base_url = f"{self._host}/api/v1/agents/dynamic"
        self._http = HTTPClient(
            base_url=agents_base_url,
            auth=self._auth,
            timeout=timeout,
            verify_ssl=verify_ssl,
            max_retries=max_retries,
            retry_delay=retry_delay,
            user_agent=user_agent,
        )

        # HTTP client for persona operations
        personas_base_url = f"{self._host}/api/v1/agents/personas"
        self._personas_http = HTTPClient(
            base_url=personas_base_url,
            auth=self._auth,
            timeout=timeout,
            verify_ssl=verify_ssl,
            max_retries=max_retries,
            retry_delay=retry_delay,
            user_agent=user_agent,
        )

        # HTTP client for bot operations
        bots_base_url = f"{self._host}/api/v1/bots"
        self._bots_http = HTTPClient(
            base_url=bots_base_url,
            auth=self._auth,
            timeout=timeout,
            verify_ssl=verify_ssl,
            max_retries=max_retries,
            retry_delay=retry_delay,
            user_agent=user_agent,
        )

        # HTTP client for ability operations
        abilities_base_url = f"{self._host}/api/v1/agents/abilities"
        self._abilities_http = HTTPClient(
            base_url=abilities_base_url,
            auth=self._auth,
            timeout=timeout,
            verify_ssl=verify_ssl,
            max_retries=max_retries,
            retry_delay=retry_delay,
            user_agent=user_agent,
        )

        self._async_http: AsyncHTTPClient | None = None
        self._async_personas_http: AsyncHTTPClient | None = None
        self._async_bots_http: AsyncHTTPClient | None = None
        self._async_abilities_http: AsyncHTTPClient | None = None
        if enable_async:
            self._async_http = AsyncHTTPClient(
                base_url=agents_base_url,
                auth=self._auth,
                timeout=timeout,
                verify_ssl=verify_ssl,
                max_retries=max_retries,
                retry_delay=retry_delay,
                user_agent=user_agent,
            )
            self._async_personas_http = AsyncHTTPClient(
                base_url=personas_base_url,
                auth=self._auth,
                timeout=timeout,
                verify_ssl=verify_ssl,
                max_retries=max_retries,
                retry_delay=retry_delay,
                user_agent=user_agent,
            )
            self._async_bots_http = AsyncHTTPClient(
                base_url=bots_base_url,
                auth=self._auth,
                timeout=timeout,
                verify_ssl=verify_ssl,
                max_retries=max_retries,
                retry_delay=retry_delay,
                user_agent=user_agent,
            )
            self._async_abilities_http = AsyncHTTPClient(
                base_url=abilities_base_url,
                auth=self._auth,
                timeout=timeout,
                verify_ssl=verify_ssl,
                max_retries=max_retries,
                retry_delay=retry_delay,
                user_agent=user_agent,
            )

        self._mcp_client: MCPClient | None = None

    # -------------------------------------------------------------------------
    # Pagination Helpers
    # -------------------------------------------------------------------------

    def _paginate_list(
        self,
        http: HttpClient,
        path: str,
        mapper: Callable[[dict], Any],
        limit: int | None = None,
        page_size: int = 100,
        extra_params: dict[str, Any] | None = None,
    ) -> list:
        """
        Paginate through all results from a list endpoint.

        Args:
            http: HTTP client to use
            path: API path
            mapper: Function to map response items to model objects
            limit: Maximum number of items to return (None for all)
            page_size: Number of items per page
            extra_params: Additional query parameters to include in each request

        Returns:
            List of all items
        """
        results: list = []
        after: str | None = None

        while True:
            params: dict[str, Any] = {"limit": page_size}
            if extra_params:
                params.update(extra_params)
            if after:
                params["after"] = after

            response = http.get(path, params=params)
            data = response.get("data", [])
            results.extend(mapper(item) for item in data)

            # Check if we've hit the limit
            if limit is not None and len(results) >= limit:
                return results[:limit]

            # Check for more pages
            paging = response.get("paging", {})
            after = paging.get("after")
            if not after:
                break

        return results

    async def _apaginate_list(
        self,
        http: AsyncHttpClient,
        path: str,
        mapper: Callable[[dict], Any],
        limit: int | None = None,
        page_size: int = 100,
        extra_params: dict[str, Any] | None = None,
    ) -> list:
        """
        Paginate through all results from a list endpoint asynchronously.

        Args:
            http: Async HTTP client to use
            path: API path
            mapper: Function to map response items to model objects
            limit: Maximum number of items to return (None for all)
            page_size: Number of items per page
            extra_params: Additional query parameters to include in each request

        Returns:
            List of all items
        """
        results: list = []
        after: str | None = None

        while True:
            params: dict[str, Any] = {"limit": page_size}
            if extra_params:
                params.update(extra_params)
            if after:
                params["after"] = after

            response = await http.get(path, params=params)
            data = response.get("data", [])
            results.extend(mapper(item) for item in data)

            # Check if we've hit the limit
            if limit is not None and len(results) >= limit:
                return results[:limit]

            # Check for more pages
            paging = response.get("paging", {})
            after = paging.get("after")
            if not after:
                break

        return results

    def agent(self, name: str) -> AgentHandle:
        """
        Get a handle to a specific agent.

        Args:
            name: The agent name (e.g., "DataQualityPlannerAgent")

        Returns:
            AgentHandle for invoking the agent

        Example:
            agent = client.agent("DataQualityPlannerAgent")
            response = agent.call("What tests should I add?")

            # Or async (if enable_async=True)
            response = await agent.acall("What tests should I add?")
        """
        return AgentHandle(
            name=name,
            http=self._http,
            async_http=self._async_http,
        )

    @property
    def mcp(self) -> MCPClient:
        """
        Get the MCP client for tool operations.

        Returns:
            MCPClient instance for interacting with OpenMetadata's MCP server

        Example:
            tools = client.mcp.list_tools()
            result = client.mcp.call_tool(MCPTool.SEARCH_METADATA, {"query": "customer"})
        """
        if self._mcp_client is None:
            self._mcp_client = MCPClient(
                host=self._host,
                auth=self._auth,
                http=self._http,
            )
        return self._mcp_client

    def list_agents(
        self,
        limit: int | None = None,
    ) -> list[AgentInfo]:
        """
        List all API-enabled agents.

        Automatically paginates through all results.

        Args:
            limit: Maximum number of agents to return. If None, returns all agents.

        Returns:
            List of AgentInfo objects for API-enabled agents
        """
        return self._paginate_list(
            self._http,
            "/",
            lambda a: AgentInfo.from_dict(a),
            limit=limit,
            extra_params={"apiEnabled": "true"},
        )

    async def alist_agents(
        self,
        limit: int | None = None,
    ) -> list[AgentInfo]:
        """
        List all API-enabled agents asynchronously.

        Automatically paginates through all results.

        Args:
            limit: Maximum number of agents to return. If None, returns all agents.

        Returns:
            List of AgentInfo objects for API-enabled agents

        Raises:
            RuntimeError: If async client is not available
        """
        if self._async_http is None:
            raise RuntimeError(
                "Async HTTP client not available. "
                "Use AiSdk with enable_async=True for async operations."
            )

        return await self._apaginate_list(
            self._async_http,
            "/",
            lambda a: AgentInfo.from_dict(a),
            limit=limit,
            extra_params={"apiEnabled": "true"},
        )

    def create_agent(self, request: CreateAgentRequest) -> AgentInfo:
        """
        Create a new dynamic agent.

        Args:
            request: CreateAgentRequest with agent configuration

        Returns:
            AgentInfo for the created agent

        Example:
            from ai_sdk import CreateAgentRequest

            request = CreateAgentRequest(
                name="MyAgent",
                description="An agent that helps with data quality",
                persona="DataAnalyst",  # Name of an existing persona
                mode="chat",
                api_enabled=True,
            )
            agent_info = client.create_agent(request)
        """
        # Resolve persona name to ID
        persona_info = self.get_persona(request.persona)
        api_dict = request.to_api_dict()
        api_dict["persona"] = {"id": persona_info.id, "type": "persona"}

        # Resolve ability names to IDs if provided
        if request.abilities:
            ability_refs = []
            for ability_name in request.abilities:
                ability_info = self.get_ability(ability_name)
                ability_refs.append({"id": ability_info.id, "type": "ability"})
            api_dict["abilities"] = ability_refs

        response = self._http.post("/", json=api_dict)
        return AgentInfo.from_dict(response)

    async def acreate_agent(self, request: CreateAgentRequest) -> AgentInfo:
        """
        Create a new dynamic agent asynchronously.

        Args:
            request: CreateAgentRequest with agent configuration

        Returns:
            AgentInfo for the created agent

        Raises:
            RuntimeError: If async client is not available

        Example:
            from ai_sdk import CreateAgentRequest

            request = CreateAgentRequest(
                name="MyAgent",
                description="An agent that helps with data quality",
                persona="DataAnalyst",  # Name of an existing persona
                mode="chat",
                api_enabled=True,
            )
            agent_info = await client.acreate_agent(request)
        """
        if self._async_http is None:
            raise RuntimeError(
                "Async HTTP client not available. "
                "Use AiSdk with enable_async=True for async operations."
            )

        # Resolve persona name to ID
        persona_info = await self.aget_persona(request.persona)
        api_dict = request.to_api_dict()
        api_dict["persona"] = {"id": persona_info.id, "type": "persona"}

        # Resolve ability names to IDs if provided
        if request.abilities:
            ability_refs = []
            for ability_name in request.abilities:
                ability_info = await self.aget_ability(ability_name)
                ability_refs.append({"id": ability_info.id, "type": "ability"})
            api_dict["abilities"] = ability_refs

        response = await self._async_http.post("/", json=api_dict)
        return AgentInfo.from_dict(response)

    # -------------------------------------------------------------------------
    # Bot Operations
    # -------------------------------------------------------------------------

    def list_bots(self, limit: int | None = None) -> list[BotInfo]:
        """
        List all bots.

        Automatically paginates through all results.

        Args:
            limit: Maximum number of bots to return. If None, returns all bots.

        Returns:
            List of BotInfo objects
        """
        return self._paginate_list(
            self._bots_http,
            "/",
            lambda b: BotInfo.from_dict(b),
            limit=limit,
        )

    async def alist_bots(self, limit: int | None = None) -> list[BotInfo]:
        """
        List all bots asynchronously.

        Automatically paginates through all results.

        Args:
            limit: Maximum number of bots to return. If None, returns all bots.

        Returns:
            List of BotInfo objects

        Raises:
            RuntimeError: If async client is not available
        """
        if self._async_bots_http is None:
            raise RuntimeError(
                "Async HTTP client not available. "
                "Use AiSdk with enable_async=True for async operations."
            )

        return await self._apaginate_list(
            self._async_bots_http,
            "/",
            lambda b: BotInfo.from_dict(b),
            limit=limit,
        )

    def get_bot(self, name: str) -> BotInfo:
        """
        Get a bot by name.

        Args:
            name: The bot name

        Returns:
            BotInfo object

        Raises:
            BotNotFoundError: If the bot is not found
        """
        encoded_name = quote(name, safe="")
        response = self._bots_http.get(f"/name/{encoded_name}", bot_name=name)
        return BotInfo.from_dict(response)

    async def aget_bot(self, name: str) -> BotInfo:
        """
        Get a bot by name asynchronously.

        Args:
            name: The bot name

        Returns:
            BotInfo object

        Raises:
            BotNotFoundError: If the bot is not found
            RuntimeError: If async client is not available
        """
        if self._async_bots_http is None:
            raise RuntimeError(
                "Async HTTP client not available. "
                "Use AiSdk with enable_async=True for async operations."
            )

        encoded_name = quote(name, safe="")
        response = await self._async_bots_http.get(f"/name/{encoded_name}", bot_name=name)
        return BotInfo.from_dict(response)

    # -------------------------------------------------------------------------
    # Persona Operations
    # -------------------------------------------------------------------------

    def list_personas(self, limit: int | None = None) -> list[PersonaInfo]:
        """
        List all personas.

        Automatically paginates through all results.

        Args:
            limit: Maximum number of personas to return. If None, returns all personas.

        Returns:
            List of PersonaInfo objects
        """
        return self._paginate_list(
            self._personas_http,
            "/",
            lambda p: PersonaInfo.from_dict(p),
            limit=limit,
        )

    async def alist_personas(self, limit: int | None = None) -> list[PersonaInfo]:
        """
        List all personas asynchronously.

        Automatically paginates through all results.

        Args:
            limit: Maximum number of personas to return. If None, returns all personas.

        Returns:
            List of PersonaInfo objects

        Raises:
            RuntimeError: If async client is not available
        """
        if self._async_personas_http is None:
            raise RuntimeError(
                "Async HTTP client not available. "
                "Use AiSdk with enable_async=True for async operations."
            )

        return await self._apaginate_list(
            self._async_personas_http,
            "/",
            lambda p: PersonaInfo.from_dict(p),
            limit=limit,
        )

    def get_persona(self, name: str) -> PersonaInfo:
        """
        Get a persona by name.

        Args:
            name: The persona name

        Returns:
            PersonaInfo for the requested persona

        Raises:
            PersonaNotFoundError: If the persona does not exist
        """
        try:
            encoded_name = quote(name, safe="")
            response = self._personas_http.get(f"/name/{encoded_name}")
            return PersonaInfo.from_dict(response)
        except AiSdkError as e:
            if e.status_code == 404:
                raise PersonaNotFoundError(name) from e
            raise

    async def aget_persona(self, name: str) -> PersonaInfo:
        """
        Get a persona by name asynchronously.

        Args:
            name: The persona name

        Returns:
            PersonaInfo for the requested persona

        Raises:
            PersonaNotFoundError: If the persona does not exist
            RuntimeError: If async client is not available
        """
        if self._async_personas_http is None:
            raise RuntimeError(
                "Async HTTP client not available. "
                "Use AiSdk with enable_async=True for async operations."
            )

        try:
            encoded_name = quote(name, safe="")
            response = await self._async_personas_http.get(f"/name/{encoded_name}")
            return PersonaInfo.from_dict(response)
        except AiSdkError as e:
            if e.status_code == 404:
                raise PersonaNotFoundError(name) from e
            raise

    def create_persona(self, request: CreatePersonaRequest) -> PersonaInfo:
        """
        Create a new persona.

        Args:
            request: CreatePersonaRequest with persona details

        Returns:
            PersonaInfo for the created persona
        """
        response = self._personas_http.post("/", json=request.to_api_dict())
        return PersonaInfo.from_dict(response)

    async def acreate_persona(self, request: CreatePersonaRequest) -> PersonaInfo:
        """
        Create a new persona asynchronously.

        Args:
            request: CreatePersonaRequest with persona details

        Returns:
            PersonaInfo for the created persona

        Raises:
            RuntimeError: If async client is not available
        """
        if self._async_personas_http is None:
            raise RuntimeError(
                "Async HTTP client not available. "
                "Use AiSdk with enable_async=True for async operations."
            )

        response = await self._async_personas_http.post("/", json=request.to_api_dict())
        return PersonaInfo.from_dict(response)

    # -------------------------------------------------------------------------
    # Ability Operations
    # -------------------------------------------------------------------------

    def list_abilities(self, limit: int | None = None) -> list[AbilityInfo]:
        """
        List all abilities.

        Automatically paginates through all results.

        Args:
            limit: Maximum number of abilities to return. If None, returns all abilities.

        Returns:
            List of AbilityInfo objects
        """
        return self._paginate_list(
            self._abilities_http,
            "/",
            lambda a: AbilityInfo.from_dict(a),
            limit=limit,
        )

    async def alist_abilities(self, limit: int | None = None) -> list[AbilityInfo]:
        """
        List all abilities asynchronously.

        Automatically paginates through all results.

        Args:
            limit: Maximum number of abilities to return. If None, returns all abilities.

        Returns:
            List of AbilityInfo objects

        Raises:
            RuntimeError: If async client is not available
        """
        if self._async_abilities_http is None:
            raise RuntimeError(
                "Async HTTP client not available. "
                "Use AiSdk with enable_async=True for async operations."
            )

        return await self._apaginate_list(
            self._async_abilities_http,
            "/",
            lambda a: AbilityInfo.from_dict(a),
            limit=limit,
        )

    def get_ability(self, name: str) -> AbilityInfo:
        """
        Get an ability by name.

        Args:
            name: The ability name

        Returns:
            AbilityInfo for the requested ability

        Raises:
            AbilityNotFoundError: If the ability does not exist
        """
        try:
            encoded_name = quote(name, safe="")
            response = self._abilities_http.get(f"/name/{encoded_name}")
            return AbilityInfo.from_dict(response)
        except AiSdkError as e:
            if e.status_code == 404:
                raise AbilityNotFoundError(name) from e
            raise

    async def aget_ability(self, name: str) -> AbilityInfo:
        """
        Get an ability by name asynchronously.

        Args:
            name: The ability name

        Returns:
            AbilityInfo for the requested ability

        Raises:
            AbilityNotFoundError: If the ability does not exist
            RuntimeError: If async client is not available
        """
        if self._async_abilities_http is None:
            raise RuntimeError(
                "Async HTTP client not available. "
                "Use AiSdk with enable_async=True for async operations."
            )

        try:
            encoded_name = quote(name, safe="")
            response = await self._async_abilities_http.get(f"/name/{encoded_name}")
            return AbilityInfo.from_dict(response)
        except AiSdkError as e:
            if e.status_code == 404:
                raise AbilityNotFoundError(name) from e
            raise

    @property
    def host(self) -> str:
        """Get the configured host URL."""
        return self._host

    @property
    def async_enabled(self) -> bool:
        """Check if async operations are enabled."""
        return self._enable_async

    def close(self) -> None:
        """Close the client and release resources."""
        self._http.close()
        self._personas_http.close()
        self._bots_http.close()
        self._abilities_http.close()

    async def aclose(self) -> None:
        """Close the async client and release resources."""
        if self._async_http is not None:
            await self._async_http.close()
        if self._async_personas_http is not None:
            await self._async_personas_http.close()
        if self._async_bots_http is not None:
            await self._async_bots_http.close()
        if self._async_abilities_http is not None:
            await self._async_abilities_http.close()

    def __enter__(self) -> AiSdk:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    async def __aenter__(self) -> AiSdk:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()
        self.close()

    def __repr__(self) -> str:
        return f"AiSdk(host={self._host!r})"

    @classmethod
    def from_config(cls, config: AiSdkConfig) -> AiSdk:
        """
        Create a client from an AiSdkConfig object.

        This is the recommended way to create a client when using
        environment-based configuration.

        Args:
            config: AiSdkConfig instance

        Returns:
            AiSdk client

        Example:
            from ai_sdk.client import AiSdk
            from ai_sdk.config import AiSdkConfig

            # From environment variables
            config = AiSdkConfig.from_env()
            client = AiSdk.from_config(config)

            # With overrides
            config = AiSdkConfig.from_env(timeout=30.0)
            client = AiSdk.from_config(config)
        """
        if config.debug:
            from ai_sdk._logging import set_debug

            set_debug(True)

        return cls(
            host=config.host,
            token=config.token,
            timeout=config.timeout,
            verify_ssl=config.verify_ssl,
            enable_async=config.enable_async,
            max_retries=config.max_retries,
            retry_delay=config.retry_delay,
            user_agent=config.user_agent,
        )
