/**
 * Skills namespace.
 *
 * Backed by an HttpClient rooted at /api/v1/agents/skills.
 */

import type { HttpClient } from '../http.js';
import type { PaginatedResponse } from '../models.js';
import type { SkillInfo } from '../types.js';

/**
 * Options for list operations on the skills namespace.
 */
export interface SkillsListOptions {
  /** Maximum number of skills to return. If omitted, returns all skills. */
  limit?: number;
}

/**
 * API response for a skill.
 * @internal
 */
interface ApiSkillInfo {
  id: string;
  name: string;
  displayName?: string;
  description?: string;
  provider?: string;
  fullyQualifiedName?: string;
  tools?: string[];
}

function mapSkillInfo(data: ApiSkillInfo): SkillInfo {
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
 * Namespace for skill operations.
 */
export class SkillsApi {
  private readonly http: HttpClient;

  constructor(http: HttpClient) {
    this.http = http;
  }

  /**
   * List all skills.
   *
   * Automatically paginates through all results.
   */
  async list(options?: SkillsListOptions): Promise<SkillInfo[]> {
    return paginate<ApiSkillInfo, SkillInfo>(
      (params) => this.http.get<PaginatedResponse<ApiSkillInfo>>('/', params),
      mapSkillInfo,
      options?.limit
    );
  }

  /**
   * Get a skill by name.
   *
   * @throws {SkillNotFoundError} If the skill is not found.
   */
  async get(name: string): Promise<SkillInfo> {
    const response = await this.http.get<ApiSkillInfo>(
      `/name/${encodeURIComponent(name)}`,
      undefined,
      undefined,
      'skill',
      name
    );
    return mapSkillInfo(response);
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
