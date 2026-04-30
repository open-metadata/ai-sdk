/**
 * Memories namespace — CRUD + hybrid search for Context Center memories.
 *
 * Backed by two HttpClients:
 *   1. memoriesHttp rooted at /api/v1/contextCenter/memories (CRUD).
 *   2. searchHttp rooted at /api/v1, used for /hybrid/nlq/search.
 */

import type { HttpClient } from '../http.js';
import type { PaginatedResponse } from '../models.js';
import type {
  ContextMemory,
  CreateContextMemoryRequest,
  EntityReference,
  MemoryScope,
  MemorySearchHit,
  MemorySearchResults,
  MemoryType,
  MemoryVisibility,
} from '../types.js';

/**
 * Options for {@link MemoriesApi.list}.
 */
export interface MemoriesListOptions {
  /** Filter to memories attached to this primary entity FQN. */
  primaryEntityFqn?: string;
  /** Maximum number of memories to return. If omitted, returns all. */
  limit?: number;
}

/**
 * Options for {@link MemoriesApi.search}.
 */
export interface MemoriesSearchOptions {
  /**
   * Field filters. Map of field name -> list of values
   * (e.g. `{ primaryEntityId: ["abc"], visibility: ["Shared"] }`).
   */
  filters?: Record<string, string[]>;
  /** Number of results to return (1-100, default: 15). */
  size?: number;
  /** Pagination offset (default: 0). */
  from?: number;
}

/**
 * Raw API shape for a memory document. Captures only the fields the SDK
 * surfaces; everything else is ignored.
 * @internal
 */
interface ApiContextMemory {
  id: string;
  name: string;
  fullyQualifiedName?: string;
  title?: string;
  question?: string;
  answer?: string;
  summary?: string;
  memoryType?: MemoryType;
  memoryScope?: MemoryScope;
  shareConfig?: {
    visibility?: MemoryVisibility;
  };
  primaryEntity?: EntityReference;
  usageCount?: number;
  lastUsedAt?: number;
  deleted?: boolean;
}

/**
 * Raw OpenSearch-style response for the hybrid NLQ search endpoint.
 * @internal
 */
interface ApiSearchResponse {
  hits?: {
    total?: number | { value?: number };
    hits?: Array<{
      _source?: ApiContextMemory;
      _score?: number;
    }>;
  };
}

function mapContextMemory(data: ApiContextMemory): ContextMemory {
  const visibility: MemoryVisibility = data.shareConfig?.visibility ?? 'Private';
  return {
    id: data.id,
    name: data.name,
    fullyQualifiedName: data.fullyQualifiedName,
    title: data.title,
    question: data.question ?? '',
    answer: data.answer ?? '',
    summary: data.summary,
    memoryType: data.memoryType ?? 'Note',
    memoryScope: data.memoryScope ?? 'EntityScoped',
    visibility,
    primaryEntity: data.primaryEntity,
    usageCount: data.usageCount ?? 0,
    lastUsedAt: data.lastUsedAt,
    deleted: data.deleted ?? false,
  };
}

function buildCreateBody(request: CreateContextMemoryRequest): Record<string, unknown> {
  const body: Record<string, unknown> = {
    name: request.name,
    question: request.question,
    answer: request.answer,
    memoryType: request.memoryType ?? 'Note',
    memoryScope: request.memoryScope ?? 'EntityScoped',
    shareConfig: { visibility: request.visibility ?? 'Private' },
  };
  if (request.title !== undefined) {
    body.title = request.title;
  }
  if (request.description !== undefined) {
    body.description = request.description;
  }
  if (request.primaryEntity !== undefined) {
    body.primaryEntity = request.primaryEntity;
  }
  if (request.relatedEntities !== undefined) {
    body.relatedEntities = request.relatedEntities;
  }
  if (request.tags !== undefined) {
    body.tags = request.tags.map((tagFqn) => ({
      tagFQN: tagFqn,
      labelType: 'Manual',
      state: 'Confirmed',
      source: 'Classification',
    }));
  }
  return body;
}

function mapSearchResults(data: ApiSearchResponse): MemorySearchResults {
  const hitsBlock = data.hits ?? {};
  const totalRaw = hitsBlock.total ?? 0;
  const total =
    typeof totalRaw === 'number' ? totalRaw : Number(totalRaw.value ?? 0);
  const rawHits = hitsBlock.hits ?? [];
  const hits: MemorySearchHit[] = rawHits.map((hit) => ({
    memory: mapContextMemory(hit._source ?? ({} as ApiContextMemory)),
    score: Number(hit._score ?? 0),
  }));
  return { total, hits };
}

/**
 * Namespace for Context Center memory operations.
 */
export class MemoriesApi {
  private readonly memoriesHttp: HttpClient;
  private readonly searchHttp: HttpClient;

  constructor(memoriesHttp: HttpClient, searchHttp: HttpClient) {
    this.memoriesHttp = memoriesHttp;
    this.searchHttp = searchHttp;
  }

  /**
   * List Context Center memories.
   *
   * Automatically paginates through all results.
   */
  async list(options?: MemoriesListOptions): Promise<ContextMemory[]> {
    return paginateMemories(
      this.memoriesHttp,
      options?.primaryEntityFqn,
      options?.limit
    );
  }

  /**
   * Get a memory by ID.
   */
  async get(memoryId: string): Promise<ContextMemory> {
    const response = await this.memoriesHttp.get<ApiContextMemory>(`/${memoryId}`);
    return mapContextMemory(response);
  }

  /**
   * Create a new Context Center memory.
   */
  async create(request: CreateContextMemoryRequest): Promise<ContextMemory> {
    const body = buildCreateBody(request);
    const response = await this.memoriesHttp.post<ApiContextMemory>('/', body);
    return mapContextMemory(response);
  }

  /**
   * Delete a memory by ID. Soft delete by default; pass `hardDelete: true`
   * to permanently remove.
   */
  async delete(memoryId: string, options?: { hardDelete?: boolean }): Promise<void> {
    await this.memoriesHttp.delete<void>(`/${memoryId}`, {
      hardDelete: options?.hardDelete ?? false,
    });
  }

  /**
   * Hybrid NLQ search over Context Center memories.
   */
  async search(query: string, options?: MemoriesSearchOptions): Promise<MemorySearchResults> {
    const params: Record<string, string | number | boolean> = {
      q: query,
      index: 'contextMemory',
      size: options?.size ?? 15,
      from: options?.from ?? 0,
    };
    if (options?.filters) {
      params.filters = JSON.stringify(options.filters);
    }
    const response = await this.searchHttp.get<ApiSearchResponse>(
      '/hybrid/nlq/search',
      params
    );
    return mapSearchResults(response);
  }
}

/**
 * Paginate through memory list results.
 * @internal
 */
async function paginateMemories(
  http: HttpClient,
  primaryEntityFqn: string | undefined,
  limit: number | undefined,
  pageSize: number = 100
): Promise<ContextMemory[]> {
  const results: ContextMemory[] = [];
  let after: string | undefined = undefined;

  // eslint-disable-next-line no-constant-condition
  while (true) {
    const params: Record<string, string | number | boolean> = { limit: pageSize };
    if (primaryEntityFqn !== undefined) {
      params.primaryEntityFqn = primaryEntityFqn;
    }
    if (after) {
      params.after = after;
    }

    const response = await http.get<PaginatedResponse<ApiContextMemory>>('/', params);
    const data = response.data || [];
    results.push(...data.map(mapContextMemory));

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
