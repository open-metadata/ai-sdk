import { afterEach, describe, expect, it, vi } from 'vitest';
import { AISdk } from '../src/client.js';

afterEach(() => vi.unstubAllGlobals());

describe('Collate 2.1 contracts', () => {
  it('retains current memory values and filters by entity UUID', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      data: [{
        id: 'm1', name: 'learning', memoryType: 'Learning',
        shareConfig: { visibility: 'Public' }, entityStatus: 'Unprocessed',
        statusReason: 'Awaiting review',
      }],
    })));
    vi.stubGlobal('fetch', fetchMock);
    const client = new AISdk({ host: 'https://example.com', token: 'test' });
    const [memory] = await client.memories.list({ primaryEntityId: 'asset-id' });
    expect(memory.memoryType).toBe('Learning');
    expect(memory.visibility).toBe('Public');
    expect(memory.entityStatus).toBe('Unprocessed');
    expect(memory.statusReason).toBe('Awaiting review');
    expect(String(fetchMock.mock.calls[0][0])).toContain('primaryEntityId=asset-id');
  });

  it('serializes a requested lifecycle stage', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      id: 'm1', name: 'note', entityStatus: 'Approved',
    })));
    vi.stubGlobal('fetch', fetchMock);
    const client = new AISdk({ host: 'https://example.com', token: 'test' });
    const memory = await client.memories.create({
      name: 'note', question: 'q', answer: 'a', entityStatus: 'Approved',
    });
    expect(JSON.parse(fetchMock.mock.calls[0][1].body).entityStatus).toBe('Approved');
    expect(memory.entityStatus).toBe('Approved');
  });

  it('sends the required message and retains structured output', async () => {
    const components = [{ type: 'chart', content: { title: 'Revenue' } }];
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      conversationId: 'c1', response: '', components,
    })));
    vi.stubGlobal('fetch', fetchMock);
    const client = new AISdk({ host: 'https://example.com', token: 'test' });
    const response = await client.agent('agent').invoke();
    expect(JSON.parse(fetchMock.mock.calls[0][1].body).message).toBe('');
    expect(response.components).toEqual(components);
  });

  it('surfaces terminal streaming errors', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(
      'event: stream-error\ndata: {"message":"run failed","severity":"fatal"}\n\n',
    ));
    vi.stubGlobal('fetch', fetchMock);
    const client = new AISdk({ host: 'https://example.com', token: 'test' });
    const events = [];
    for await (const event of client.agent('agent').stream()) events.push(event);
    expect(events).toEqual([expect.objectContaining({ type: 'error', error: 'run failed' })]);
    expect(JSON.parse(fetchMock.mock.calls[0][1].body).message).toBe('');
  });
});
