/**
 * Agents namespace — CRUD for dynamic agents.
 *
 * Backed by an HttpClient rooted at /api/v1/agents/dynamic.
 */

import type { HttpClient } from '../http.js';
import {
  mapAgentInfo,
  type AgentInfo,
  type ApiAgentInfo,
  type PaginatedResponse,
} from '../models.js';
import type { CreateAgentRequest } from '../types.js';
import type { AISdk } from '../client.js';

/**
 * Options for list operations on the agents namespace.
 */
export interface AgentsListOptions {
  /** Maximum number of agents to return. If omitted, returns all agents. */
  limit?: number;
}

/**
 * Namespace for dynamic agent CRUD operations.
 *
 * Holds a back-reference to AISdk so that {@link create} can resolve
 * persona/skill names to entity references through the personas/skills
 * namespaces.
 */
export class AgentsApi {
  private readonly http: HttpClient;
  private readonly client: AISdk;

  constructor(http: HttpClient, client: AISdk) {
    this.http = http;
    this.client = client;
  }

  /**
   * List all API-enabled dynamic agents.
   *
   * Automatically paginates through all results.
   */
  async list(options?: AgentsListOptions): Promise<AgentInfo[]> {
    return paginate<ApiAgentInfo, AgentInfo>(
      (params) =>
        this.http.get<PaginatedResponse<ApiAgentInfo>>('/', { ...params, apiEnabled: 'true' }),
      mapAgentInfo,
      options?.limit
    );
  }

  /**
   * Create a new dynamic agent.
   *
   * Resolves the persona name and any skill names to entity references
   * via {@link AISdk.personas} and {@link AISdk.skills} before issuing
   * the create request.
   */
  async create(request: CreateAgentRequest): Promise<AgentInfo> {
    const personaInfo = await this.client.personas.get(request.persona);

    let skillRefs: Array<{ id: string; type: string }> | undefined;
    if (request.skills && request.skills.length > 0) {
      skillRefs = [];
      for (const skillName of request.skills) {
        const skillInfo = await this.client.skills.get(skillName);
        skillRefs.push({ id: skillInfo.id, type: 'skill' });
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
      skills: skillRefs,
      knowledge: request.knowledge,
      prompt: request.prompt,
      schedule: request.schedule,
      apiEnabled: request.apiEnabled ?? false,
      provider: request.provider ?? 'user',
    };

    const response = await this.http.post<ApiAgentInfo>('/', body);
    return mapAgentInfo(response);
  }
}

/**
 * Paginate through all results from a list endpoint.
 * @internal
 */
async function paginate<T, U>(
  fetcher: (
    params: Record<string, string | number | boolean>
  ) => Promise<PaginatedResponse<T>>,
  mapper: (item: T) => U,
  limit?: number,
  pageSize: number = 100
): Promise<U[]> {
  const results: U[] = [];
  let after: string | undefined = undefined;

  // eslint-disable-next-line no-constant-condition
  while (true) {
    const params: Record<string, string | number | boolean> = { limit: pageSize };
    if (after) {
      params.after = after;
    }

    const response = await fetcher(params);
    const data = response.data || [];
    results.push(...data.map(mapper));

    if (limit !== undefined && results.length >= limit) {
      return results.slice(0, limit);
    }

    after = response.paging?.after;
    if (!after) {
      break;
    }
  }

  return results;
}
