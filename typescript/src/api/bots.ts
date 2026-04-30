/**
 * Bots namespace.
 *
 * Backed by an HttpClient rooted at /api/v1/bots.
 */

import type { HttpClient } from '../http.js';
import type { PaginatedResponse } from '../models.js';
import type { BotInfo, EntityReference } from '../types.js';

/**
 * Options for list operations on the bots namespace.
 */
export interface BotsListOptions {
  /** Maximum number of bots to return. If omitted, returns all bots. */
  limit?: number;
}

/**
 * API response for a bot.
 * @internal
 */
interface ApiBotInfo {
  id: string;
  name: string;
  displayName?: string;
  description?: string;
  botUser?: EntityReference;
}

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
 * Namespace for bot operations.
 */
export class BotsApi {
  private readonly http: HttpClient;

  constructor(http: HttpClient) {
    this.http = http;
  }

  /**
   * List all bots.
   *
   * Automatically paginates through all results.
   */
  async list(options?: BotsListOptions): Promise<BotInfo[]> {
    return paginate<ApiBotInfo, BotInfo>(
      (params) => this.http.get<PaginatedResponse<ApiBotInfo>>('/', params),
      mapBotInfo,
      options?.limit
    );
  }

  /**
   * Get a bot by name.
   *
   * @throws {BotNotFoundError} If the bot is not found.
   */
  async get(name: string): Promise<BotInfo> {
    const response = await this.http.get<ApiBotInfo>(
      `/name/${encodeURIComponent(name)}`,
      undefined,
      undefined,
      'bot',
      name
    );
    return mapBotInfo(response);
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
