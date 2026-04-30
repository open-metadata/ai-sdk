/**
 * Tests for the MemoriesApi namespace.
 *
 * Mocks the underlying HttpClient and asserts the request shape and
 * response parsing for each verb (list, get, create, delete, search).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoriesApi } from '../src/api/memories.js';
import type { HttpClient } from '../src/http.js';

/**
 * Build a minimal HttpClient mock with `get`, `post`, `delete` jest mocks.
 */
function createHttpMock(): {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
  delete: ReturnType<typeof vi.fn>;
} {
  return {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  };
}

function asHttpClient(mock: ReturnType<typeof createHttpMock>): HttpClient {
  return mock as unknown as HttpClient;
}

describe('MemoriesApi', () => {
  let memoriesHttp: ReturnType<typeof createHttpMock>;
  let searchHttp: ReturnType<typeof createHttpMock>;
  let api: MemoriesApi;

  beforeEach(() => {
    memoriesHttp = createHttpMock();
    searchHttp = createHttpMock();
    api = new MemoriesApi(asHttpClient(memoriesHttp), asHttpClient(searchHttp));
  });

  describe('list()', () => {
    it('issues GET / with default page size and parses results', async () => {
      memoriesHttp.get.mockResolvedValueOnce({
        data: [
          {
            id: 'mem-1',
            name: 'memory-one',
            fullyQualifiedName: 'cm.memory-one',
            title: 'First',
            question: 'q1',
            answer: 'a1',
            memoryType: 'Note',
            memoryScope: 'EntityScoped',
            shareConfig: { visibility: 'Private' },
            usageCount: 3,
          },
          {
            id: 'mem-2',
            name: 'memory-two',
            question: 'q2',
            answer: 'a2',
            memoryType: 'Faq',
            memoryScope: 'UserGlobal',
            shareConfig: { visibility: 'Shared' },
          },
        ],
        paging: {},
      });

      const memories = await api.list();

      expect(memoriesHttp.get).toHaveBeenCalledTimes(1);
      const [path, params] = memoriesHttp.get.mock.calls[0];
      expect(path).toBe('/');
      expect(params).toEqual({ limit: 100 });
      expect(memories).toHaveLength(2);
      expect(memories[0]).toMatchObject({
        id: 'mem-1',
        name: 'memory-one',
        title: 'First',
        question: 'q1',
        answer: 'a1',
        memoryType: 'Note',
        memoryScope: 'EntityScoped',
        visibility: 'Private',
        usageCount: 3,
        deleted: false,
      });
      expect(memories[1].visibility).toBe('Shared');
      expect(memories[1].memoryType).toBe('Faq');
    });

    it('passes primaryEntityFqn filter through', async () => {
      memoriesHttp.get.mockResolvedValueOnce({ data: [], paging: {} });

      await api.list({ primaryEntityFqn: 'service.db.schema.tbl' });

      expect(memoriesHttp.get).toHaveBeenCalledTimes(1);
      const [, params] = memoriesHttp.get.mock.calls[0];
      expect(params).toEqual({
        limit: 100,
        primaryEntityFqn: 'service.db.schema.tbl',
      });
    });

    it('honors limit option and slices the accumulated results', async () => {
      memoriesHttp.get.mockResolvedValueOnce({
        data: [
          { id: 'mem-1', name: 'one', question: 'q', answer: 'a' },
          { id: 'mem-2', name: 'two', question: 'q', answer: 'a' },
          { id: 'mem-3', name: 'three', question: 'q', answer: 'a' },
        ],
        paging: {},
      });

      const memories = await api.list({ limit: 2 });

      expect(memories).toHaveLength(2);
      expect(memories.map((m) => m.id)).toEqual(['mem-1', 'mem-2']);
    });

    it('paginates with the after cursor until exhausted', async () => {
      memoriesHttp.get
        .mockResolvedValueOnce({
          data: [{ id: 'mem-1', name: 'one', question: 'q', answer: 'a' }],
          paging: { after: 'cursor-1' },
        })
        .mockResolvedValueOnce({
          data: [{ id: 'mem-2', name: 'two', question: 'q', answer: 'a' }],
          paging: {},
        });

      const memories = await api.list();

      expect(memoriesHttp.get).toHaveBeenCalledTimes(2);
      expect(memoriesHttp.get.mock.calls[1][1]).toEqual({ limit: 100, after: 'cursor-1' });
      expect(memories.map((m) => m.id)).toEqual(['mem-1', 'mem-2']);
    });
  });

  describe('get()', () => {
    it('issues GET /<id> and parses the document', async () => {
      memoriesHttp.get.mockResolvedValueOnce({
        id: 'mem-42',
        name: 'memory-42',
        question: 'why?',
        answer: 'because',
        memoryType: 'Runbook',
        memoryScope: 'EntityScoped',
        shareConfig: { visibility: 'Entity' },
        primaryEntity: { id: 'tbl-1', type: 'table', name: 'orders' },
        usageCount: 7,
        lastUsedAt: 1700000000000,
      });

      const memory = await api.get('mem-42');

      expect(memoriesHttp.get).toHaveBeenCalledWith('/mem-42');
      expect(memory).toMatchObject({
        id: 'mem-42',
        name: 'memory-42',
        memoryType: 'Runbook',
        visibility: 'Entity',
        primaryEntity: { id: 'tbl-1', type: 'table', name: 'orders' },
        usageCount: 7,
        lastUsedAt: 1700000000000,
      });
    });

    it('defaults visibility to Private when shareConfig is missing', async () => {
      memoriesHttp.get.mockResolvedValueOnce({
        id: 'mem-1',
        name: 'lonely',
        question: 'q',
        answer: 'a',
      });

      const memory = await api.get('mem-1');

      expect(memory.visibility).toBe('Private');
      expect(memory.memoryType).toBe('Note');
      expect(memory.memoryScope).toBe('EntityScoped');
    });
  });

  describe('create()', () => {
    it('issues POST / with the create body and parses the response', async () => {
      memoriesHttp.post.mockResolvedValueOnce({
        id: 'mem-new',
        name: 'preferred-tooling',
        question: 'Which tool?',
        answer: 'Use dbt.',
        memoryType: 'Preference',
        memoryScope: 'UserGlobal',
        shareConfig: { visibility: 'Shared' },
      });

      const memory = await api.create({
        name: 'preferred-tooling',
        question: 'Which tool?',
        answer: 'Use dbt.',
        memoryType: 'Preference',
        memoryScope: 'UserGlobal',
        visibility: 'Shared',
      });

      expect(memoriesHttp.post).toHaveBeenCalledTimes(1);
      const [path, body] = memoriesHttp.post.mock.calls[0];
      expect(path).toBe('/');
      expect(body).toEqual({
        name: 'preferred-tooling',
        question: 'Which tool?',
        answer: 'Use dbt.',
        memoryType: 'Preference',
        memoryScope: 'UserGlobal',
        shareConfig: { visibility: 'Shared' },
      });
      expect(memory.id).toBe('mem-new');
      expect(memory.visibility).toBe('Shared');
    });

    it('applies sensible defaults when optional fields are omitted', async () => {
      memoriesHttp.post.mockResolvedValueOnce({
        id: 'mem-default',
        name: 'minimal',
        question: 'q',
        answer: 'a',
      });

      await api.create({
        name: 'minimal',
        question: 'q',
        answer: 'a',
      });

      const [, body] = memoriesHttp.post.mock.calls[0];
      expect(body).toEqual({
        name: 'minimal',
        question: 'q',
        answer: 'a',
        memoryType: 'Note',
        memoryScope: 'EntityScoped',
        shareConfig: { visibility: 'Private' },
      });
    });

    it('wraps tag FQNs into TagLabel objects on the wire', async () => {
      memoriesHttp.post.mockResolvedValueOnce({
        id: 'mem-tagged',
        name: 'tagged-memory',
        question: 'q',
        answer: 'a',
      });

      await api.create({
        name: 'tagged-memory',
        question: 'q',
        answer: 'a',
        tags: ['PII.Sensitive', 'Tier.Tier1'],
      });

      const [, body] = memoriesHttp.post.mock.calls[0];
      expect((body as { tags: unknown[] }).tags).toEqual([
        {
          tagFQN: 'PII.Sensitive',
          labelType: 'Manual',
          state: 'Confirmed',
          source: 'Classification',
        },
        {
          tagFQN: 'Tier.Tier1',
          labelType: 'Manual',
          state: 'Confirmed',
          source: 'Classification',
        },
      ]);
    });

    it('forwards primaryEntity and relatedEntities verbatim', async () => {
      memoriesHttp.post.mockResolvedValueOnce({
        id: 'mem-with-entity',
        name: 'attached',
        question: 'q',
        answer: 'a',
      });

      await api.create({
        name: 'attached',
        question: 'q',
        answer: 'a',
        title: 'Attached Memory',
        description: 'desc',
        primaryEntity: { id: 'tbl-1', type: 'table', name: 'orders' },
        relatedEntities: [{ id: 'tbl-2', type: 'table' }],
      });

      const [, body] = memoriesHttp.post.mock.calls[0];
      expect(body).toMatchObject({
        title: 'Attached Memory',
        description: 'desc',
        primaryEntity: { id: 'tbl-1', type: 'table', name: 'orders' },
        relatedEntities: [{ id: 'tbl-2', type: 'table' }],
      });
    });
  });

  describe('delete()', () => {
    it('issues DELETE /<id> with hardDelete=false by default', async () => {
      memoriesHttp.delete.mockResolvedValueOnce(undefined);

      await api.delete('mem-1');

      expect(memoriesHttp.delete).toHaveBeenCalledTimes(1);
      const [path, params] = memoriesHttp.delete.mock.calls[0];
      expect(path).toBe('/mem-1');
      expect(params).toEqual({ hardDelete: false });
    });

    it('forwards hardDelete=true when requested', async () => {
      memoriesHttp.delete.mockResolvedValueOnce(undefined);

      await api.delete('mem-1', { hardDelete: true });

      const [, params] = memoriesHttp.delete.mock.calls[0];
      expect(params).toEqual({ hardDelete: true });
    });
  });

  describe('search()', () => {
    it('issues GET /hybrid/nlq/search with default size/from and parses hits', async () => {
      searchHttp.get.mockResolvedValueOnce({
        hits: {
          total: { value: 2 },
          hits: [
            {
              _score: 1.42,
              _source: {
                id: 'mem-1',
                name: 'first',
                question: 'q1',
                answer: 'a1',
                memoryType: 'Note',
                memoryScope: 'EntityScoped',
                shareConfig: { visibility: 'Private' },
              },
            },
            {
              _score: 0.81,
              _source: {
                id: 'mem-2',
                name: 'second',
                question: 'q2',
                answer: 'a2',
              },
            },
          ],
        },
      });

      const results = await api.search('customer churn');

      expect(searchHttp.get).toHaveBeenCalledTimes(1);
      const [path, params] = searchHttp.get.mock.calls[0];
      expect(path).toBe('/hybrid/nlq/search');
      expect(params).toEqual({
        q: 'customer churn',
        index: 'contextMemory',
        size: 15,
        from: 0,
      });
      expect(results.total).toBe(2);
      expect(results.hits).toHaveLength(2);
      expect(results.hits[0].score).toBe(1.42);
      expect(results.hits[0].memory.id).toBe('mem-1');
      expect(results.hits[0].memory.visibility).toBe('Private');
      expect(results.hits[1].score).toBe(0.81);
    });

    it('serializes filters as JSON in the query string', async () => {
      searchHttp.get.mockResolvedValueOnce({
        hits: { total: 0, hits: [] },
      });

      await api.search('runbooks', {
        filters: {
          primaryEntityId: ['abc', 'def'],
          visibility: ['Shared'],
        },
        size: 25,
        from: 50,
      });

      const [, params] = searchHttp.get.mock.calls[0];
      expect(params).toEqual({
        q: 'runbooks',
        index: 'contextMemory',
        size: 25,
        from: 50,
        filters: JSON.stringify({
          primaryEntityId: ['abc', 'def'],
          visibility: ['Shared'],
        }),
      });
    });

    it('handles a numeric total and missing hits gracefully', async () => {
      searchHttp.get.mockResolvedValueOnce({
        hits: { total: 5, hits: undefined },
      });

      const results = await api.search('q');

      expect(results.total).toBe(5);
      expect(results.hits).toEqual([]);
    });

    it('returns an empty result when the search response is empty', async () => {
      searchHttp.get.mockResolvedValueOnce({});

      const results = await api.search('nothing');

      expect(results.total).toBe(0);
      expect(results.hits).toEqual([]);
    });
  });
});
