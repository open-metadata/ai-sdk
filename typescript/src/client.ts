/**
 * Main client for the Metadata AI SDK.
 *
 * This module provides the MetadataAI class, the primary entry point
 * for interacting with OpenMetadata Dynamic Agents.
 */

import { AgentHandle } from './agent.js';
import { HttpClient } from './http.js';
import type {
  AgentInfo,
  ApiAgentInfo,
  MetadataAIOptions,
  PaginatedResponse,
} from './models.js';
import type {
  AbilityInfo,
  BotInfo,
  PersonaInfo,
  CreatePersonaRequest,
  CreateAgentRequest,
} from './types.js';

/** Default timeout in milliseconds (2 minutes) */
const DEFAULT_TIMEOUT = 120000;

/** Default number of retry attempts */
const DEFAULT_MAX_RETRIES = 3;

/** Default base delay between retries in milliseconds */
const DEFAULT_RETRY_DELAY = 1000;

/**
 * API response for bot info.
 * @internal
 */
interface ApiBotInfo {
  id: string;
  name: string;
  displayName?: string;
  description?: string;
  botUser?: {
    id: string;
    type: string;
    name?: string;
    displayName?: string;
  };
}

/**
 * API response for persona info.
 * @internal
 */
interface ApiPersonaInfo {
  id: string;
  name: string;
  displayName?: string;
  description?: string;
  prompt?: string;
  provider: string;
}

/**
 * API response for ability info.
 * @internal
 */
interface ApiAbilityInfo {
  id: string;
  name: string;
  displayName?: string;
  description?: string;
  provider?: string;
  fullyQualifiedName?: string;
  tools?: string[];
}

/**
 * Convert API agent info response to AgentInfo.
 */
function mapAgentInfo(data: ApiAgentInfo): AgentInfo {
  return {
    name: data.name,
    displayName: data.displayName || data.name,
    description: data.description || '',
    abilities: data.abilities || [],
    apiEnabled: data.apiEnabled ?? false,
  };
}

/**
 * Convert API bot info response to BotInfo.
 */
function mapBotInfo(data: ApiBotInfo): BotInfo {
  return {
    id: data.id,
    name: data.name,
    displayName: data.displayName,
    description: data.description,
    botUser: data.botUser,
  };
}

/**
 * Convert API persona info response to PersonaInfo.
 */
function mapPersonaInfo(data: ApiPersonaInfo): PersonaInfo {
  return {
    id: data.id,
    name: data.name,
    displayName: data.displayName,
    description: data.description,
    prompt: data.prompt,
    provider: data.provider,
  };
}

/**
 * Convert API ability info response to AbilityInfo.
 */
function mapAbilityInfo(data: ApiAbilityInfo): AbilityInfo {
  return {
    id: data.id,
    name: data.name,
    displayName: data.displayName,
    description: data.description,
    provider: data.provider,
    fullyQualifiedName: data.fullyQualifiedName,
    tools: data.tools || [],
  };
}

/**
 * Main client for interacting with Metadata AI agents.
 *
 * This client provides access to OpenMetadata Dynamic Agents, enabling you to
 * leverage semantic intelligence capabilities in your applications.
 *
 * @example
 * ```typescript
 * import { MetadataAI } from '@openmetadata/ai-sdk';
 *
 * // Initialize the client
 * const client = new MetadataAI({
 *   host: 'https://openmetadata.example.com',
 *   token: 'your-bot-jwt-token',
 * });
 *
 * // Get an agent handle
 * const agent = client.agent('DataQualityPlannerAgent');
 *
 * // Invoke synchronously
 * const response = await agent.invoke('Analyze the customers table');
 * console.log(response.response);
 *
 * // Or stream the response
 * for await (const event of agent.stream('Analyze the customers table')) {
 *   if (event.type === 'content') {
 *     process.stdout.write(event.content || '');
 *   }
 * }
 *
 * // Multi-turn conversations
 * const r1 = await agent.invoke('Analyze the orders table');
 * const r2 = await agent.invoke('Now create tests for the issues you found', {
 *   conversationId: r1.conversationId,
 * });
 *
 * // List available agents
 * const agents = await client.listAgents();
 * for (const agentInfo of agents) {
 *   console.log(`${agentInfo.displayName}: ${agentInfo.description}`);
 * }
 * ```
 */
export class MetadataAI {
  private readonly hostUrl: string;
  private readonly http: HttpClient;

  /**
   * Create a new MetadataAI client.
   *
   * @param options - Client configuration options
   *
   * @throws {Error} If host or token is empty
   *
   * @example
   * ```typescript
   * // Basic initialization
   * const client = new MetadataAI({
   *   host: 'https://openmetadata.example.com',
   *   token: 'your-jwt-token',
   * });
   *
   * // With custom options
   * const client = new MetadataAI({
   *   host: 'https://openmetadata.example.com',
   *   token: 'your-jwt-token',
   *   timeout: 60000,      // 60 seconds
   *   maxRetries: 5,       // More retries
   *   retryDelay: 2000,    // Start with 2 second delay
   * });
   * ```
   */
  constructor(options: MetadataAIOptions) {
    if (!options.host) {
      throw new Error('Host is required');
    }
    if (!options.token) {
      throw new Error('Token is required');
    }

    // Normalize host URL (remove trailing slash)
    this.hostUrl = options.host.replace(/\/$/, '');

    // Create HTTP client with base URL for agents API
    this.http = new HttpClient({
      baseUrl: `${this.hostUrl}/api/v1/api/agents`,
      token: options.token,
      timeout: options.timeout ?? DEFAULT_TIMEOUT,
      maxRetries: options.maxRetries ?? DEFAULT_MAX_RETRIES,
      retryDelay: options.retryDelay ?? DEFAULT_RETRY_DELAY,
    });
  }

  /**
   * Get the configured host URL.
   */
  get host(): string {
    return this.hostUrl;
  }

  /**
   * Paginate through all results from a list endpoint.
   * @internal
   */
  private async paginateList<T, U>(
    fetcher: (params: Record<string, string | number>) => Promise<PaginatedResponse<T>>,
    mapper: (item: T) => U,
    limit?: number,
    pageSize: number = 100
  ): Promise<U[]> {
    const results: U[] = [];
    let after: string | undefined = undefined;

    while (true) {
      const params: Record<string, string | number> = { limit: pageSize };
      if (after) {
        params.after = after;
      }

      const response = await fetcher(params);
      const data = response.data || [];
      results.push(...data.map(mapper));

      // Check if we've hit the requested limit
      if (limit !== undefined && results.length >= limit) {
        return results.slice(0, limit);
      }

      // Check for more pages
      after = response.paging?.after;
      if (!after) {
        break;
      }
    }

    return results;
  }

  /**
   * Get a handle to a specific agent.
   *
   * @param name - The agent name (e.g., "DataQualityPlannerAgent")
   * @returns AgentHandle for invoking the agent
   *
   * @example
   * ```typescript
   * const agent = client.agent('DataQualityPlannerAgent');
   *
   * // Invoke the agent
   * const response = await agent.invoke('What tests should I add?');
   * ```
   */
  agent(name: string): AgentHandle {
    return new AgentHandle(name, this.http);
  }

  /**
   * List all API-enabled agents.
   *
   * Automatically paginates through all results.
   *
   * @param options - Options
   * @param options.limit - Maximum number of agents to return. If not specified, returns all agents.
   * @returns Promise resolving to list of AgentInfo objects
   *
   * @example
   * ```typescript
   * // List all agents
   * const agents = await client.listAgents();
   *
   * // List with limit
   * const agents = await client.listAgents({ limit: 20 });
   *
   * // Display agent information
   * for (const agent of agents) {
   *   console.log(`${agent.name}: ${agent.description}`);
   *   console.log(`  Abilities: ${agent.abilities.join(', ')}`);
   * }
   * ```
   */
  async listAgents(options?: { limit?: number }): Promise<AgentInfo[]> {
    return this.paginateList<ApiAgentInfo, AgentInfo>(
      (params) => this.http.get<PaginatedResponse<ApiAgentInfo>>('/', params),
      mapAgentInfo,
      options?.limit
    );
  }

  /**
   * List all bots in the system.
   *
   * Automatically paginates through all results.
   *
   * @param options - Options
   * @param options.limit - Maximum number of bots to return. If not specified, returns all bots.
   * @returns Promise resolving to list of BotInfo objects
   *
   * @example
   * ```typescript
   * // List all bots
   * const bots = await client.listBots();
   * for (const bot of bots) {
   *   console.log(`${bot.name}: ${bot.description}`);
   * }
   *
   * // List with limit
   * const bots = await client.listBots({ limit: 5 });
   * ```
   */
  async listBots(options?: { limit?: number }): Promise<BotInfo[]> {
    return this.paginateList<ApiBotInfo, BotInfo>(
      (params) => this.http.getAbsolute<PaginatedResponse<ApiBotInfo>>('/api/v1/bots', params),
      mapBotInfo,
      options?.limit
    );
  }

  /**
   * Get a bot by name.
   *
   * @param name - The bot name
   * @returns Promise resolving to BotInfo
   * @throws {BotNotFoundError} If the bot is not found
   *
   * @example
   * ```typescript
   * const bot = await client.getBot('ingestion-bot');
   * console.log(`Bot: ${bot.displayName}`);
   * console.log(`User: ${bot.botUser?.name}`);
   * ```
   */
  async getBot(name: string): Promise<BotInfo> {
    const response = await this.http.getAbsolute<ApiBotInfo>(
      `/api/v1/bots/name/${encodeURIComponent(name)}`,
      undefined,
      'bot',
      name
    );

    return mapBotInfo(response);
  }

  /**
   * List all personas in the system.
   *
   * Automatically paginates through all results.
   *
   * @param options - Options
   * @param options.limit - Maximum number of personas to return. If not specified, returns all personas.
   * @returns Promise resolving to list of PersonaInfo objects
   *
   * @example
   * ```typescript
   * // List all personas
   * const personas = await client.listPersonas();
   * for (const persona of personas) {
   *   console.log(`${persona.name}: ${persona.description}`);
   * }
   *
   * // List with limit
   * const personas = await client.listPersonas({ limit: 5 });
   * ```
   */
  async listPersonas(options?: { limit?: number }): Promise<PersonaInfo[]> {
    return this.paginateList<ApiPersonaInfo, PersonaInfo>(
      (params) =>
        this.http.getAbsolute<PaginatedResponse<ApiPersonaInfo>>('/api/v1/agents/personas', params),
      mapPersonaInfo,
      options?.limit
    );
  }

  /**
   * Get a persona by name.
   *
   * @param name - The persona name
   * @returns Promise resolving to PersonaInfo
   * @throws {PersonaNotFoundError} If the persona is not found
   *
   * @example
   * ```typescript
   * const persona = await client.getPersona('data-analyst');
   * console.log(`Persona: ${persona.displayName}`);
   * console.log(`Prompt: ${persona.prompt}`);
   * ```
   */
  async getPersona(name: string): Promise<PersonaInfo> {
    const response = await this.http.getAbsolute<ApiPersonaInfo>(
      `/api/v1/agents/personas/name/${encodeURIComponent(name)}`,
      undefined,
      'persona',
      name
    );

    return mapPersonaInfo(response);
  }

  /**
   * Create a new persona.
   *
   * @param request - The persona creation request
   * @returns Promise resolving to the created PersonaInfo
   *
   * @example
   * ```typescript
   * const persona = await client.createPersona({
   *   name: 'custom-analyst',
   *   description: 'A custom data analyst persona',
   *   prompt: 'You are a helpful data analyst...',
   *   displayName: 'Custom Analyst',
   * });
   * console.log(`Created persona: ${persona.id}`);
   * ```
   */
  async createPersona(request: CreatePersonaRequest): Promise<PersonaInfo> {
    const body = {
      name: request.name,
      description: request.description,
      prompt: request.prompt,
      displayName: request.displayName,
      provider: request.provider ?? 'user',
      owners: request.owners,
    };

    const response = await this.http.postAbsolute<ApiPersonaInfo>(
      '/api/v1/agents/personas',
      body
    );

    return mapPersonaInfo(response);
  }

  /**
   * Create a new dynamic agent.
   *
   * @param request - The agent creation request
   * @returns Promise resolving to the created AgentInfo
   *
   * @example
   * ```typescript
   * const agent = await client.createAgent({
   *   name: 'my-custom-agent',
   *   description: 'A custom agent for data analysis',
   *   persona: 'data-analyst',
   *   mode: 'chat',
   *   displayName: 'My Custom Agent',
   *   abilities: ['analyze', 'report'],
   *   apiEnabled: true,
   * });
   * console.log(`Created agent: ${agent.name}`);
   *
   * // Invoke the new agent
   * const response = await client.agent(agent.name).invoke('Hello!');
   * ```
   */
  async createAgent(request: CreateAgentRequest): Promise<AgentInfo> {
    // Resolve persona name to ID
    const personaInfo = await this.getPersona(request.persona);

    // Resolve ability names to IDs if provided
    let abilityRefs: Array<{ id: string; type: string }> | undefined;
    if (request.abilities && request.abilities.length > 0) {
      abilityRefs = [];
      for (const abilityName of request.abilities) {
        const abilityInfo = await this.getAbility(abilityName);
        abilityRefs.push({ id: abilityInfo.id, type: 'ability' });
      }
    }

    const body = {
      name: request.name,
      description: request.description,
      persona: { id: personaInfo.id, type: 'persona' },
      mode: request.mode,
      displayName: request.displayName,
      icon: request.icon,
      botName: request.botName,
      abilities: abilityRefs,
      knowledge: request.knowledge,
      prompt: request.prompt,
      schedule: request.schedule,
      apiEnabled: request.apiEnabled ?? false,
      provider: request.provider ?? 'user',
    };

    const response = await this.http.postAbsolute<ApiAgentInfo>(
      '/api/v1/agents/dynamic',
      body
    );

    return mapAgentInfo(response);
  }

  /**
   * List all abilities in the system.
   *
   * Automatically paginates through all results.
   *
   * @param options - Options
   * @param options.limit - Maximum number of abilities to return. If not specified, returns all abilities.
   * @returns Promise resolving to list of AbilityInfo objects
   *
   * @example
   * ```typescript
   * // List all abilities
   * const abilities = await client.listAbilities();
   * for (const ability of abilities) {
   *   console.log(`${ability.name}: ${ability.description}`);
   *   console.log(`  Tools: ${ability.tools.join(', ')}`);
   * }
   *
   * // List with limit
   * const abilities = await client.listAbilities({ limit: 5 });
   * ```
   */
  async listAbilities(options?: { limit?: number }): Promise<AbilityInfo[]> {
    return this.paginateList<ApiAbilityInfo, AbilityInfo>(
      (params) =>
        this.http.getAbsolute<PaginatedResponse<ApiAbilityInfo>>(
          '/api/v1/agents/abilities',
          params
        ),
      mapAbilityInfo,
      options?.limit
    );
  }

  /**
   * Get an ability by name.
   *
   * @param name - The ability name
   * @returns Promise resolving to AbilityInfo
   * @throws {AbilityNotFoundError} If the ability is not found
   *
   * @example
   * ```typescript
   * const ability = await client.getAbility('analyze-data');
   * console.log(`Ability: ${ability.displayName}`);
   * console.log(`Tools: ${ability.tools.join(', ')}`);
   * ```
   */
  async getAbility(name: string): Promise<AbilityInfo> {
    const response = await this.http.getAbsolute<ApiAbilityInfo>(
      `/api/v1/agents/abilities/name/${encodeURIComponent(name)}`,
      undefined,
      'ability',
      name
    );

    return mapAbilityInfo(response);
  }

  /**
   * String representation of the client.
   */
  toString(): string {
    return `MetadataAI(host="${this.hostUrl}")`;
  }
}
