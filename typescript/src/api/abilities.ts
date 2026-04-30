/**
 * Abilities namespace.
 *
 * Backed by an HttpClient rooted at /api/v1/agents/abilities.
 */

import type { HttpClient } from '../http.js';
import type { PaginatedResponse } from '../models.js';
import type { AbilityInfo } from '../types.js';

/**
 * Options for list operations on the abilities namespace.
 */
export interface AbilitiesListOptions {
  /** Maximum number of abilities to return. If omitted, returns all abilities. */
  limit?: number;
}

/**
 * API response for an ability.
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
 * Namespace for ability operations.
 */
export class AbilitiesApi {
  private readonly http: HttpClient;

  constructor(http: HttpClient) {
    this.http = http;
  }

  /**
   * List all abilities.
   *
   * Automatically paginates through all results.
   */
  async list(options?: AbilitiesListOptions): Promise<AbilityInfo[]> {
    return paginate<ApiAbilityInfo, AbilityInfo>(
      (params) => this.http.get<PaginatedResponse<ApiAbilityInfo>>('/', params),
      mapAbilityInfo,
      options?.limit
    );
  }

  /**
   * Get an ability by name.
   *
   * @throws {AbilityNotFoundError} If the ability is not found.
   */
  async get(name: string): Promise<AbilityInfo> {
    const response = await this.http.get<ApiAbilityInfo>(
      `/name/${encodeURIComponent(name)}`,
      undefined,
      undefined,
      'ability',
      name
    );
    return mapAbilityInfo(response);
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
