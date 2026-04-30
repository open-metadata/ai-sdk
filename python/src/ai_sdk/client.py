"""Main client for the AI SDK."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ai_sdk.config import AISdkConfig

from ai_sdk._http import AsyncHTTPClient, HTTPClient
from ai_sdk.agent import AgentHandle
from ai_sdk.api.abilities import AbilitiesAPI
from ai_sdk.api.agents import AgentsAPI
from ai_sdk.api.bots import BotsAPI
from ai_sdk.api.memories import MemoriesAPI
from ai_sdk.api.personas import PersonasAPI
from ai_sdk.auth import TokenAuth
from ai_sdk.mcp._client import MCPClient


class AISdk:
    """Main client for interacting with AI agents.

    Composition pattern — entity CRUD lives on namespaces:
        client.agents.list()
        client.bots.get("ingestion-bot")
        client.personas.list()
        client.abilities.get("DataQuality")
        client.memories.search("customer churn")

    The agent handle factory is unchanged:
        client.agent("DataQualityPlannerAgent").call("...")

    Usage:
        from ai_sdk.client import AISdk

        client = AISdk(host="https://...", token="...")
        response = client.agent("DataQualityPlannerAgent").call("Hello")

    Async:
        client = AISdk(host="...", token="...", enable_async=True)
        response = await client.agent("DataQualityPlannerAgent").acall("Hello")

    From environment:
        from ai_sdk.config import AISdkConfig
        client = AISdk.from_config(AISdkConfig.from_env())
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
    ) -> None:
        if not token:
            raise ValueError("token must be a non-empty string")

        self._host = host.rstrip("/")
        self._auth = TokenAuth(token)
        self._enable_async = enable_async

        common_kwargs: dict[str, Any] = {
            "auth": self._auth,
            "timeout": timeout,
            "verify_ssl": verify_ssl,
            "max_retries": max_retries,
            "retry_delay": retry_delay,
            "user_agent": user_agent,
        }

        agents_url = f"{self._host}/api/v1/agents/dynamic"
        personas_url = f"{self._host}/api/v1/agents/personas"
        bots_url = f"{self._host}/api/v1/bots"
        abilities_url = f"{self._host}/api/v1/agents/abilities"
        default_agent_url = f"{self._host}/api/v1/agents"
        chat_conv_url = f"{self._host}/api/v1/assistants"
        memories_url = f"{self._host}/api/v1/contextCenter/memories"
        search_url = f"{self._host}/api/v1"

        self._http = HTTPClient(base_url=agents_url, **common_kwargs)
        self._personas_http = HTTPClient(base_url=personas_url, **common_kwargs)
        self._bots_http = HTTPClient(base_url=bots_url, **common_kwargs)
        self._abilities_http = HTTPClient(base_url=abilities_url, **common_kwargs)
        self._default_http = HTTPClient(base_url=default_agent_url, **common_kwargs)
        self._chat_conv_http = HTTPClient(base_url=chat_conv_url, **common_kwargs)
        self._memories_http = HTTPClient(base_url=memories_url, **common_kwargs)
        self._search_http = HTTPClient(base_url=search_url, **common_kwargs)

        self._async_http: AsyncHTTPClient | None = None
        self._async_personas_http: AsyncHTTPClient | None = None
        self._async_bots_http: AsyncHTTPClient | None = None
        self._async_abilities_http: AsyncHTTPClient | None = None
        self._async_default_http: AsyncHTTPClient | None = None
        self._async_chat_conv_http: AsyncHTTPClient | None = None
        self._async_memories_http: AsyncHTTPClient | None = None
        self._async_search_http: AsyncHTTPClient | None = None

        if enable_async:
            self._async_http = AsyncHTTPClient(base_url=agents_url, **common_kwargs)
            self._async_personas_http = AsyncHTTPClient(base_url=personas_url, **common_kwargs)
            self._async_bots_http = AsyncHTTPClient(base_url=bots_url, **common_kwargs)
            self._async_abilities_http = AsyncHTTPClient(base_url=abilities_url, **common_kwargs)
            self._async_default_http = AsyncHTTPClient(
                base_url=default_agent_url, **common_kwargs
            )
            self._async_chat_conv_http = AsyncHTTPClient(
                base_url=chat_conv_url, **common_kwargs
            )
            self._async_memories_http = AsyncHTTPClient(base_url=memories_url, **common_kwargs)
            self._async_search_http = AsyncHTTPClient(base_url=search_url, **common_kwargs)

        # Lazily-initialized namespaces
        self._agents_ns: AgentsAPI | None = None
        self._bots_ns: BotsAPI | None = None
        self._personas_ns: PersonasAPI | None = None
        self._abilities_ns: AbilitiesAPI | None = None
        self._memories_ns: MemoriesAPI | None = None
        self._mcp_client: MCPClient | None = None

    # -------------------------------------------------------------------------
    # Namespaces
    # -------------------------------------------------------------------------

    @property
    def agents(self) -> AgentsAPI:
        if self._agents_ns is None:
            self._agents_ns = AgentsAPI(self._http, self._async_http, client=self)
        return self._agents_ns

    @property
    def bots(self) -> BotsAPI:
        if self._bots_ns is None:
            self._bots_ns = BotsAPI(self._bots_http, self._async_bots_http)
        return self._bots_ns

    @property
    def personas(self) -> PersonasAPI:
        if self._personas_ns is None:
            self._personas_ns = PersonasAPI(self._personas_http, self._async_personas_http)
        return self._personas_ns

    @property
    def abilities(self) -> AbilitiesAPI:
        if self._abilities_ns is None:
            self._abilities_ns = AbilitiesAPI(
                self._abilities_http, self._async_abilities_http
            )
        return self._abilities_ns

    @property
    def memories(self) -> MemoriesAPI:
        if self._memories_ns is None:
            self._memories_ns = MemoriesAPI(
                http=self._memories_http,
                async_http=self._async_memories_http,
                search_http=self._search_http,
                search_async_http=self._async_search_http,
            )
        return self._memories_ns

    @property
    def mcp(self) -> MCPClient:
        if self._mcp_client is None:
            self._mcp_client = MCPClient(host=self._host, auth=self._auth, http=self._http)
        return self._mcp_client

    # -------------------------------------------------------------------------
    # Agent handle factory (unchanged surface)
    # -------------------------------------------------------------------------

    def agent(self, name: str | None = None) -> AgentHandle:
        """Get a handle to an agent.

        - With a name: returns a handle for the named dynamic agent.
        - Without a name: returns a handle for the platform's default agent
          (PLANNER / CHAT_MODE).
        """
        if name is None:
            from ai_sdk._default_agent import DefaultAgentHandle

            return DefaultAgentHandle(
                chat_http=self._chat_conv_http,
                chat_async_http=self._async_chat_conv_http,
                default_http=self._default_http,
                default_async_http=self._async_default_http,
            )
        return AgentHandle(name=name, http=self._http, async_http=self._async_http)

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def host(self) -> str:
        return self._host

    @property
    def async_enabled(self) -> bool:
        return self._enable_async

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def close(self) -> None:
        for client in (
            self._http,
            self._personas_http,
            self._bots_http,
            self._abilities_http,
            self._default_http,
            self._chat_conv_http,
            self._memories_http,
            self._search_http,
        ):
            client.close()

    async def aclose(self) -> None:
        for client in (
            self._async_http,
            self._async_personas_http,
            self._async_bots_http,
            self._async_abilities_http,
            self._async_default_http,
            self._async_chat_conv_http,
            self._async_memories_http,
            self._async_search_http,
        ):
            if client is not None:
                await client.close()

    def __enter__(self) -> AISdk:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    async def __aenter__(self) -> AISdk:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()
        self.close()

    def __repr__(self) -> str:
        return f"AISdk(host={self._host!r})"

    @classmethod
    def from_config(cls, config: AISdkConfig) -> AISdk:
        """Create a client from an AISdkConfig object."""
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
