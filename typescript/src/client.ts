/**
 * Main client for the Metadata AI SDK.
 *
 * This module provides the AISdk class, the primary entry point
 * for interacting with OpenMetadata Dynamic Agents.
 */

import { AgentHandle, DefaultAgentHandle } from './agent.js';
import { AbilitiesApi } from './api/abilities.js';
import { AgentsApi } from './api/agents.js';
import { BotsApi } from './api/bots.js';
import { MemoriesApi } from './api/memories.js';
import { PersonasApi } from './api/personas.js';
import { HttpClient } from './http.js';
import type { AISdkOptions } from './models.js';

/** Default timeout in milliseconds (15 minutes) for non-streaming requests */
const DEFAULT_TIMEOUT = 900000;

/** Default number of retry attempts */
const DEFAULT_MAX_RETRIES = 3;

/** Default base delay between retries in milliseconds */
const DEFAULT_RETRY_DELAY = 1000;

/**
 * Main client for interacting with Metadata AI agents.
 *
 * This client provides access to OpenMetadata Dynamic Agents, enabling you to
 * leverage semantic intelligence capabilities in your applications.
 *
 * Entity CRUD operations live on per-entity namespaces:
 *
 * ```typescript
 * client.agents.list();
 * client.bots.get('ingestion-bot');
 * client.personas.create(req);
 * client.abilities.list();
 * client.memories.search('customer churn');
 * ```
 *
 * The agent handle factory is unchanged:
 *
 * ```typescript
 * client.agent('DataQualityPlannerAgent').invoke('Hello');
 * client.agent().invoke('Hello'); // platform default agent
 * ```
 *
 * @example
 * ```typescript
 * import { AISdk } from '@openmetadata/ai-sdk';
 *
 * const client = new AISdk({
 *   host: 'https://openmetadata.example.com',
 *   token: 'your-bot-jwt-token',
 * });
 *
 * const response = await client.agent('DataQualityPlannerAgent')
 *   .invoke('Analyze the customers table');
 * console.log(response.response);
 *
 * const agents = await client.agents.list();
 * for (const info of agents) {
 *   console.log(`${info.displayName}: ${info.description}`);
 * }
 * ```
 */
export class AISdk {
  private readonly hostUrl: string;
  private readonly agentsHttp: HttpClient;
  private readonly botsHttp: HttpClient;
  private readonly personasHttp: HttpClient;
  private readonly abilitiesHttp: HttpClient;
  private readonly memoriesHttp: HttpClient;
  private readonly searchHttp: HttpClient;
  private readonly defaultAgentHttp: HttpClient;
  private readonly chatConvHttp: HttpClient;

  /** Namespace for dynamic agent CRUD operations. */
  public readonly agents: AgentsApi;
  /** Namespace for bot operations. */
  public readonly bots: BotsApi;
  /** Namespace for persona operations. */
  public readonly personas: PersonasApi;
  /** Namespace for ability operations. */
  public readonly abilities: AbilitiesApi;
  /** Namespace for Context Center memory operations (CRUD + hybrid search). */
  public readonly memories: MemoriesApi;

  /**
   * Create a new AISdk client.
   *
   * @param options - Client configuration options
   *
   * @throws {Error} If host or token is empty
   *
   * @example
   * ```typescript
   * const client = new AISdk({
   *   host: 'https://openmetadata.example.com',
   *   token: 'your-jwt-token',
   * });
   * ```
   */
  constructor(options: AISdkOptions) {
    if (!options.host) {
      throw new Error('Host is required');
    }
    if (!options.token) {
      throw new Error('Token is required');
    }

    // Normalize host URL (remove trailing slash)
    this.hostUrl = options.host.replace(/\/$/, '');

    const httpDefaults = {
      token: options.token,
      timeout: options.timeout ?? DEFAULT_TIMEOUT,
      maxRetries: options.maxRetries ?? DEFAULT_MAX_RETRIES,
      retryDelay: options.retryDelay ?? DEFAULT_RETRY_DELAY,
    };

    // Per-entity HTTP clients, each rooted at the entity's API path so that
    // namespace classes can issue plain `/`, `/name/<n>`, `/<id>` calls.
    this.agentsHttp = new HttpClient({
      baseUrl: `${this.hostUrl}/api/v1/agents/dynamic`,
      ...httpDefaults,
    });
    this.botsHttp = new HttpClient({
      baseUrl: `${this.hostUrl}/api/v1/bots`,
      ...httpDefaults,
    });
    this.personasHttp = new HttpClient({
      baseUrl: `${this.hostUrl}/api/v1/agents/personas`,
      ...httpDefaults,
    });
    this.abilitiesHttp = new HttpClient({
      baseUrl: `${this.hostUrl}/api/v1/agents/abilities`,
      ...httpDefaults,
    });
    this.memoriesHttp = new HttpClient({
      baseUrl: `${this.hostUrl}/api/v1/contextCenter/memories`,
      ...httpDefaults,
    });
    this.searchHttp = new HttpClient({
      baseUrl: `${this.hostUrl}/api/v1`,
      ...httpDefaults,
    });

    // HTTP client for the default agent (/api/v1/agents/invoke and /api/v1/agents/run)
    this.defaultAgentHttp = new HttpClient({
      baseUrl: `${this.hostUrl}/api/v1/agents`,
      ...httpDefaults,
    });
    // Note: base URL ends at /assistants so that POST '/chatConversations' lands on
    // /api/v1/assistants/chatConversations (matches the Python SDK's pattern and
    // avoids fetch's trailing-slash normalization quirks).
    this.chatConvHttp = new HttpClient({
      baseUrl: `${this.hostUrl}/api/v1/assistants`,
      ...httpDefaults,
    });

    // Wire namespaces.
    this.agents = new AgentsApi(this.agentsHttp, this);
    this.bots = new BotsApi(this.botsHttp);
    this.personas = new PersonasApi(this.personasHttp);
    this.abilities = new AbilitiesApi(this.abilitiesHttp);
    this.memories = new MemoriesApi(this.memoriesHttp, this.searchHttp);
  }

  /**
   * Get the configured host URL.
   */
  get host(): string {
    return this.hostUrl;
  }

  /**
   * Get a handle to an agent.
   *
   * - With a name: handle for a named dynamic agent.
   * - Without a name: handle for the platform's default agent (PLANNER/CHAT_MODE).
   *   Auto-creates a chat conversation when conversationId is not supplied.
   *
   * @param name - The agent name (e.g., "DataQualityPlannerAgent"). Omit to use the default agent.
   * @returns AgentHandle or DefaultAgentHandle for invoking the agent
   *
   * @example
   * ```typescript
   * // Named agent
   * const agent = client.agent('DataQualityPlannerAgent');
   * const response = await agent.invoke('What tests should I add?');
   *
   * // Default agent (auto-creates a conversation)
   * const defaultAgent = client.agent();
   * const response = await defaultAgent.invoke('Hello!');
   * ```
   */
  agent(): DefaultAgentHandle;
  agent(name: string): AgentHandle;
  agent(name?: string): AgentHandle | DefaultAgentHandle {
    if (name === undefined) {
      return new DefaultAgentHandle(this.defaultAgentHttp, this.chatConvHttp);
    }
    return new AgentHandle(name, this.agentsHttp);
  }

  /**
   * String representation of the client.
   */
  toString(): string {
    return `AISdk(host="${this.hostUrl}")`;
  }
}
