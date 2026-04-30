/**
 * Personas namespace.
 *
 * Backed by an HttpClient rooted at /api/v1/agents/personas.
 */

import type { HttpClient } from '../http.js';
import type { PaginatedResponse } from '../models.js';
import type { CreatePersonaRequest, PersonaInfo } from '../types.js';

/**
 * Options for list operations on the personas namespace.
 */
export interface PersonasListOptions {
  /** Maximum number of personas to return. If omitted, returns all personas. */
  limit?: number;
}

/**
 * API response for a persona.
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
 * Namespace for persona operations.
 */
export class PersonasApi {
  private readonly http: HttpClient;

  constructor(http: HttpClient) {
    this.http = http;
  }

  /**
   * List all personas.
   *
   * Automatically paginates through all results.
   */
  async list(options?: PersonasListOptions): Promise<PersonaInfo[]> {
    return paginate<ApiPersonaInfo, PersonaInfo>(
      (params) => this.http.get<PaginatedResponse<ApiPersonaInfo>>('/', params),
      mapPersonaInfo,
      options?.limit
    );
  }

  /**
   * Get a persona by name.
   *
   * @throws {PersonaNotFoundError} If the persona is not found.
   */
  async get(name: string): Promise<PersonaInfo> {
    const response = await this.http.get<ApiPersonaInfo>(
      `/name/${encodeURIComponent(name)}`,
      undefined,
      undefined,
      'persona',
      name
    );
    return mapPersonaInfo(response);
  }

  /**
   * Create a new persona.
   */
  async create(request: CreatePersonaRequest): Promise<PersonaInfo> {
    const body = {
      name: request.name,
      description: request.description,
      prompt: request.prompt,
      displayName: request.displayName,
      provider: request.provider ?? 'user',
      owners: request.owners,
    };

    const response = await this.http.post<ApiPersonaInfo>('/', body);
    return mapPersonaInfo(response);
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
