/**
 * Tests for the Metadata AI SDK client.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  AiSdk,
  AgentHandle,
  AiSdkError,
  AuthenticationError,
  AgentNotFoundError,
  AgentNotEnabledError,
  RateLimitError,
  BotNotFoundError,
  PersonaNotFoundError,
} from '../src/index.js';

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

describe('AiSdk', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('initialization', () => {
    it('should create a client with required options', () => {
      const client = new AiSdk({
        host: 'https://openmetadata.example.com',
        token: 'test-token',
      });

      expect(client).toBeInstanceOf(AiSdk);
      expect(client.host).toBe('https://openmetadata.example.com');
    });

    it('should strip trailing slash from host', () => {
      const client = new AiSdk({
        host: 'https://openmetadata.example.com/',
        token: 'test-token',
      });

      expect(client.host).toBe('https://openmetadata.example.com');
    });

    it('should throw error if host is empty', () => {
      expect(() => {
        new AiSdk({
          host: '',
          token: 'test-token',
        });
      }).toThrow('Host is required');
    });

    it('should throw error if token is empty', () => {
      expect(() => {
        new AiSdk({
          host: 'https://openmetadata.example.com',
          token: '',
        });
      }).toThrow('Token is required');
    });
  });

  describe('agent()', () => {
    it('should return an AgentHandle with correct name', () => {
      const client = new AiSdk({
        host: 'https://openmetadata.example.com',
        token: 'test-token',
      });

      const agent = client.agent('DataQualityAgent');

      expect(agent).toBeInstanceOf(AgentHandle);
      expect(agent.name).toBe('DataQualityAgent');
    });
  });

  describe('listAgents()', () => {
    it('should return list of agents', async () => {
      const mockResponse = {
        data: [
          {
            name: 'DataQualityPlannerAgent',
            displayName: 'Data Quality Planner',
            description: 'Plans data quality tests',
            abilities: ['analyze', 'suggest'],
            apiEnabled: true,
          },
          {
            name: 'SqlQueryAgent',
            displayName: 'SQL Query Agent',
            description: 'Executes SQL queries',
            abilities: ['query'],
            apiEnabled: true,
          },
        ],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const client = new AiSdk({
        host: 'https://openmetadata.example.com',
        token: 'test-token',
      });

      const agents = await client.listAgents();

      expect(agents).toHaveLength(2);
      expect(agents[0].name).toBe('DataQualityPlannerAgent');
      expect(agents[0].displayName).toBe('Data Quality Planner');
      expect(agents[1].name).toBe('SqlQueryAgent');
    });

    it('should respect limit parameter when paginating', async () => {
      // Mock first page with 3 items (less than limit)
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          data: [
            { name: 'agent1', displayName: 'Agent 1', apiEnabled: true },
            { name: 'agent2', displayName: 'Agent 2', apiEnabled: true },
            { name: 'agent3', displayName: 'Agent 3', apiEnabled: true },
          ],
          paging: {},  // No 'after' cursor means last page
        }),
      });

      const client = new AiSdk({
        host: 'https://openmetadata.example.com',
        token: 'test-token',
      });

      const agents = await client.listAgents({ limit: 5 });

      expect(agents).toHaveLength(3);
      expect(mockFetch).toHaveBeenCalledTimes(1);
      // The SDK uses page size of 100 internally for pagination
      const url = mockFetch.mock.calls[0][0] as string;
      expect(url).toContain('limit=100');
    });
  });
});

describe('AgentHandle', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('invoke()', () => {
    it('should invoke agent and return response', async () => {
      const mockResponse = {
        conversationId: 'conv-123',
        response: 'Here is the analysis...',
        toolsUsed: ['searchMetadata', 'executeQuery'],
        usage: {
          promptTokens: 100,
          completionTokens: 200,
          totalTokens: 300,
        },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const client = new AiSdk({
        host: 'https://openmetadata.example.com',
        token: 'test-token',
      });

      const response = await client.agent('TestAgent').invoke('Analyze this');

      expect(response.conversationId).toBe('conv-123');
      expect(response.response).toBe('Here is the analysis...');
      expect(response.toolsUsed).toEqual(['searchMetadata', 'executeQuery']);
      expect(response.usage?.totalTokens).toBe(300);
    });

    it('should send conversation ID for multi-turn', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            conversationId: 'conv-123',
            response: 'Response',
            toolsUsed: [],
          }),
      });

      const client = new AiSdk({
        host: 'https://openmetadata.example.com',
        token: 'test-token',
      });

      await client.agent('TestAgent').invoke('Follow up', {
        conversationId: 'conv-123',
      });

      const requestBody = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(requestBody.conversationId).toBe('conv-123');
    });

    it('should send parameters when provided', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            conversationId: 'conv-123',
            response: 'Response',
            toolsUsed: [],
          }),
      });

      const client = new AiSdk({
        host: 'https://openmetadata.example.com',
        token: 'test-token',
      });

      await client.agent('TestAgent').invoke('Query', {
        parameters: { table: 'orders', limit: 100 },
      });

      const requestBody = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(requestBody.parameters).toEqual({ table: 'orders', limit: 100 });
    });

    it('should invoke agent without message (uses agent configured prompt)', async () => {
      const mockResponse = {
        conversationId: 'conv-456',
        response: 'Response from configured prompt...',
        toolsUsed: ['defaultTool'],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const client = new AiSdk({
        host: 'https://openmetadata.example.com',
        token: 'test-token',
      });

      const response = await client.agent('TestAgent').invoke();

      expect(response.conversationId).toBe('conv-456');
      expect(response.response).toBe('Response from configured prompt...');

      const requestBody = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(requestBody.message).toBeUndefined();
    });

    it('should invoke agent without message but with options', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            conversationId: 'conv-789',
            response: 'Response',
            toolsUsed: [],
          }),
      });

      const client = new AiSdk({
        host: 'https://openmetadata.example.com',
        token: 'test-token',
      });

      await client.agent('TestAgent').invoke(undefined, {
        conversationId: 'existing-conv',
        parameters: { key: 'value' },
      });

      const requestBody = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(requestBody.message).toBeUndefined();
      expect(requestBody.conversationId).toBe('existing-conv');
      expect(requestBody.parameters).toEqual({ key: 'value' });
    });
  });

  describe('getInfo()', () => {
    it('should return agent info', async () => {
      const mockResponse = {
        name: 'DataQualityAgent',
        displayName: 'Data Quality Agent',
        description: 'Analyzes data quality',
        abilities: ['analyze', 'report'],
        apiEnabled: true,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const client = new AiSdk({
        host: 'https://openmetadata.example.com',
        token: 'test-token',
      });

      const info = await client.agent('DataQualityAgent').getInfo();

      expect(info.name).toBe('DataQualityAgent');
      expect(info.displayName).toBe('Data Quality Agent');
      expect(info.abilities).toContain('analyze');
    });
  });
});

describe('Error handling', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should throw AuthenticationError on 401', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () => Promise.resolve({ message: 'Invalid token' }),
    });

    const client = new AiSdk({
      host: 'https://openmetadata.example.com',
      token: 'invalid-token',
    });

    await expect(client.agent('TestAgent').invoke('test')).rejects.toThrow(
      AuthenticationError
    );
  });

  it('should throw AgentNotFoundError on 404', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () => Promise.resolve({ message: 'Agent not found' }),
    });

    const client = new AiSdk({
      host: 'https://openmetadata.example.com',
      token: 'test-token',
    });

    await expect(client.agent('NonExistentAgent').invoke('test')).rejects.toThrow(
      AgentNotFoundError
    );
  });

  it('should throw AgentNotEnabledError on 403', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 403,
      statusText: 'Forbidden',
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () => Promise.resolve({ message: 'Agent not API enabled' }),
    });

    const client = new AiSdk({
      host: 'https://openmetadata.example.com',
      token: 'test-token',
    });

    await expect(client.agent('DisabledAgent').invoke('test')).rejects.toThrow(
      AgentNotEnabledError
    );
  });

  it('should throw RateLimitError on 429', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 429,
      statusText: 'Too Many Requests',
      headers: new Headers({
        'content-type': 'application/json',
        'Retry-After': '60',
      }),
      json: () => Promise.resolve({ message: 'Rate limit exceeded' }),
    });

    const client = new AiSdk({
      host: 'https://openmetadata.example.com',
      token: 'test-token',
      maxRetries: 0, // Disable retries for this test
    });

    try {
      await client.agent('TestAgent').invoke('test');
      expect.fail('Should have thrown RateLimitError');
    } catch (error) {
      expect(error).toBeInstanceOf(RateLimitError);
      expect((error as RateLimitError).retryAfter).toBe(60);
    }
  });
});

describe('Request configuration', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should send Authorization header with Bearer token', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          conversationId: 'conv-123',
          response: 'test',
          toolsUsed: [],
        }),
    });

    const client = new AiSdk({
      host: 'https://openmetadata.example.com',
      token: 'my-jwt-token',
    });

    await client.agent('TestAgent').invoke('test');

    const headers = mockFetch.mock.calls[0][1].headers;
    expect(headers.Authorization).toBe('Bearer my-jwt-token');
  });

  it('should use correct API base URL', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          conversationId: 'conv-123',
          response: 'test',
          toolsUsed: [],
        }),
    });

    const client = new AiSdk({
      host: 'https://openmetadata.example.com',
      token: 'test-token',
    });

    await client.agent('TestAgent').invoke('test');

    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain('https://openmetadata.example.com/api/v1/agents/dynamic/name/TestAgent/invoke');
  });
});

describe('Bot operations', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('listBots()', () => {
    it('should return list of bots', async () => {
      const mockResponse = {
        data: [
          {
            id: 'bot-1',
            name: 'ingestion-bot',
            displayName: 'Ingestion Bot',
            description: 'Bot for data ingestion',
            botUser: {
              id: 'user-1',
              type: 'user',
              name: 'ingestion-bot-user',
            },
          },
          {
            id: 'bot-2',
            name: 'test-bot',
            displayName: 'Test Bot',
            description: 'Bot for testing',
          },
        ],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const client = new AiSdk({
        host: 'https://openmetadata.example.com',
        token: 'test-token',
      });

      const bots = await client.listBots();

      expect(bots).toHaveLength(2);
      expect(bots[0].name).toBe('ingestion-bot');
      expect(bots[0].displayName).toBe('Ingestion Bot');
      expect(bots[0].botUser?.name).toBe('ingestion-bot-user');
      expect(bots[1].name).toBe('test-bot');
    });

    it('should use correct API endpoint for bots', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ data: [], paging: {} }),
      });

      const client = new AiSdk({
        host: 'https://openmetadata.example.com',
        token: 'test-token',
      });

      await client.listBots({ limit: 5 });

      const url = mockFetch.mock.calls[0][0] as string;
      expect(url).toContain('https://openmetadata.example.com/api/v1/bots');
      // SDK uses page size of 100 for pagination, limit is applied after fetching
      expect(url).toContain('limit=100');
    });
  });

  describe('getBot()', () => {
    it('should return bot by name', async () => {
      const mockResponse = {
        id: 'bot-1',
        name: 'ingestion-bot',
        displayName: 'Ingestion Bot',
        description: 'Bot for data ingestion',
        botUser: {
          id: 'user-1',
          type: 'user',
          name: 'ingestion-bot-user',
        },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const client = new AiSdk({
        host: 'https://openmetadata.example.com',
        token: 'test-token',
      });

      const bot = await client.getBot('ingestion-bot');

      expect(bot.id).toBe('bot-1');
      expect(bot.name).toBe('ingestion-bot');
      expect(bot.displayName).toBe('Ingestion Bot');
    });

    it('should use correct API endpoint for get bot by name', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            id: 'bot-1',
            name: 'my-bot',
          }),
      });

      const client = new AiSdk({
        host: 'https://openmetadata.example.com',
        token: 'test-token',
      });

      await client.getBot('my-bot');

      const url = mockFetch.mock.calls[0][0] as string;
      expect(url).toBe('https://openmetadata.example.com/api/v1/bots/name/my-bot');
    });

    it('should throw BotNotFoundError on 404', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () => Promise.resolve({ message: 'Bot not found' }),
      });

      const client = new AiSdk({
        host: 'https://openmetadata.example.com',
        token: 'test-token',
      });

      await expect(client.getBot('non-existent-bot')).rejects.toThrow(
        BotNotFoundError
      );
    });
  });
});

describe('Persona operations', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('listPersonas()', () => {
    it('should return list of personas', async () => {
      const mockResponse = {
        data: [
          {
            id: 'persona-1',
            name: 'data-analyst',
            displayName: 'Data Analyst',
            description: 'A data analyst persona',
            prompt: 'You are a helpful data analyst...',
            provider: 'system',
          },
          {
            id: 'persona-2',
            name: 'sql-expert',
            displayName: 'SQL Expert',
            description: 'An SQL expert persona',
            provider: 'user',
          },
        ],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const client = new AiSdk({
        host: 'https://openmetadata.example.com',
        token: 'test-token',
      });

      const personas = await client.listPersonas();

      expect(personas).toHaveLength(2);
      expect(personas[0].name).toBe('data-analyst');
      expect(personas[0].displayName).toBe('Data Analyst');
      expect(personas[0].provider).toBe('system');
      expect(personas[1].name).toBe('sql-expert');
    });

    it('should use correct API endpoint for personas', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ data: [], paging: {} }),
      });

      const client = new AiSdk({
        host: 'https://openmetadata.example.com',
        token: 'test-token',
      });

      await client.listPersonas({ limit: 5 });

      const url = mockFetch.mock.calls[0][0] as string;
      expect(url).toContain('https://openmetadata.example.com/api/v1/agents/personas');
      // SDK uses page size of 100 for pagination, limit is applied after fetching
      expect(url).toContain('limit=100');
    });
  });

  describe('getPersona()', () => {
    it('should return persona by name', async () => {
      const mockResponse = {
        id: 'persona-1',
        name: 'data-analyst',
        displayName: 'Data Analyst',
        description: 'A data analyst persona',
        prompt: 'You are a helpful data analyst...',
        provider: 'system',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const client = new AiSdk({
        host: 'https://openmetadata.example.com',
        token: 'test-token',
      });

      const persona = await client.getPersona('data-analyst');

      expect(persona.id).toBe('persona-1');
      expect(persona.name).toBe('data-analyst');
      expect(persona.prompt).toBe('You are a helpful data analyst...');
    });

    it('should use correct API endpoint for get persona by name', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            id: 'persona-1',
            name: 'my-persona',
            provider: 'user',
          }),
      });

      const client = new AiSdk({
        host: 'https://openmetadata.example.com',
        token: 'test-token',
      });

      await client.getPersona('my-persona');

      const url = mockFetch.mock.calls[0][0] as string;
      expect(url).toBe('https://openmetadata.example.com/api/v1/agents/personas/name/my-persona');
    });

    it('should throw PersonaNotFoundError on 404', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () => Promise.resolve({ message: 'Persona not found' }),
      });

      const client = new AiSdk({
        host: 'https://openmetadata.example.com',
        token: 'test-token',
      });

      await expect(client.getPersona('non-existent-persona')).rejects.toThrow(
        PersonaNotFoundError
      );
    });
  });

  describe('createPersona()', () => {
    it('should create a persona', async () => {
      const mockResponse = {
        id: 'persona-new',
        name: 'custom-analyst',
        displayName: 'Custom Analyst',
        description: 'A custom data analyst persona',
        prompt: 'You are a custom analyst...',
        provider: 'user',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const client = new AiSdk({
        host: 'https://openmetadata.example.com',
        token: 'test-token',
      });

      const persona = await client.createPersona({
        name: 'custom-analyst',
        description: 'A custom data analyst persona',
        prompt: 'You are a custom analyst...',
        displayName: 'Custom Analyst',
      });

      expect(persona.id).toBe('persona-new');
      expect(persona.name).toBe('custom-analyst');
      expect(persona.provider).toBe('user');
    });

    it('should send correct request body', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            id: 'persona-new',
            name: 'test-persona',
            provider: 'user',
          }),
      });

      const client = new AiSdk({
        host: 'https://openmetadata.example.com',
        token: 'test-token',
      });

      await client.createPersona({
        name: 'test-persona',
        description: 'Test description',
        prompt: 'Test prompt',
        displayName: 'Test Persona',
        provider: 'custom',
      });

      const requestBody = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(requestBody.name).toBe('test-persona');
      expect(requestBody.description).toBe('Test description');
      expect(requestBody.prompt).toBe('Test prompt');
      expect(requestBody.displayName).toBe('Test Persona');
      expect(requestBody.provider).toBe('custom');
    });

    it('should use default provider when not specified', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            id: 'persona-new',
            name: 'test-persona',
            provider: 'user',
          }),
      });

      const client = new AiSdk({
        host: 'https://openmetadata.example.com',
        token: 'test-token',
      });

      await client.createPersona({
        name: 'test-persona',
        description: 'Test',
        prompt: 'Test',
      });

      const requestBody = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(requestBody.provider).toBe('user');
    });
  });
});

describe('Agent creation', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('createAgent()', () => {
    it('should create an agent', async () => {
      // Mock persona resolution
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            id: 'persona-123',
            name: 'data-analyst',
            displayName: 'Data Analyst',
            provider: 'system',
          }),
      });
      // Mock ability resolution
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            id: 'ability-1',
            name: 'analyze',
            tools: [],
          }),
      });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            id: 'ability-2',
            name: 'report',
            tools: [],
          }),
      });
      // Mock agent creation
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            name: 'my-custom-agent',
            displayName: 'My Custom Agent',
            description: 'A custom agent for data analysis',
            abilities: ['analyze', 'report'],
            apiEnabled: true,
          }),
      });

      const client = new AiSdk({
        host: 'https://openmetadata.example.com',
        token: 'test-token',
      });

      const agent = await client.createAgent({
        name: 'my-custom-agent',
        description: 'A custom agent for data analysis',
        persona: 'data-analyst',
        mode: 'chat',
        displayName: 'My Custom Agent',
        abilities: ['analyze', 'report'],
        apiEnabled: true,
      });

      expect(agent.name).toBe('my-custom-agent');
      expect(agent.displayName).toBe('My Custom Agent');
      expect(agent.abilities).toEqual(['analyze', 'report']);
      expect(agent.apiEnabled).toBe(true);
    });

    it('should send correct request body with resolved persona ID', async () => {
      // Mock persona resolution
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            id: 'persona-456',
            name: 'my-persona',
            displayName: 'My Persona',
            provider: 'user',
          }),
      });
      // Mock agent creation
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            name: 'test-agent',
            displayName: 'Test Agent',
            description: 'Test',
            abilities: [],
            apiEnabled: false,
          }),
      });

      const client = new AiSdk({
        host: 'https://openmetadata.example.com',
        token: 'test-token',
      });

      await client.createAgent({
        name: 'test-agent',
        description: 'Test description',
        persona: 'my-persona',
        mode: 'agent',
        botName: 'my-bot',
        schedule: '0 0 * * *',
      });

      // The POST request is the second call (after persona GET)
      const requestBody = JSON.parse(mockFetch.mock.calls[1][1].body);
      expect(requestBody.name).toBe('test-agent');
      // Persona should be resolved to EntityReference with ID
      expect(requestBody.persona).toEqual({ id: 'persona-456', type: 'persona' });
      expect(requestBody.mode).toBe('agent');
      expect(requestBody.botName).toBe('my-bot');
      expect(requestBody.schedule).toBe('0 0 * * *');
      expect(requestBody.apiEnabled).toBe(false);
      expect(requestBody.provider).toBe('user');
    });

    it('should use correct API endpoint', async () => {
      // Mock persona resolution
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            id: 'persona-789',
            name: 'test-persona',
            displayName: 'Test Persona',
            provider: 'user',
          }),
      });
      // Mock agent creation
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            name: 'test-agent',
            displayName: 'Test Agent',
            description: 'Test',
            abilities: [],
            apiEnabled: false,
          }),
      });

      const client = new AiSdk({
        host: 'https://openmetadata.example.com',
        token: 'test-token',
      });

      await client.createAgent({
        name: 'test-agent',
        description: 'Test',
        persona: 'test-persona',
        mode: 'both',
      });

      // The POST request is the second call (after persona GET)
      const url = mockFetch.mock.calls[1][0] as string;
      expect(url).toBe('https://openmetadata.example.com/api/v1/agents/dynamic');
    });

    it('should include knowledge scope when provided', async () => {
      // Mock persona resolution
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            id: 'persona-abc',
            name: 'test-persona',
            displayName: 'Test Persona',
            provider: 'user',
          }),
      });
      // Mock agent creation
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            name: 'test-agent',
            displayName: 'Test',
            description: 'Test',
            abilities: [],
            apiEnabled: false,
          }),
      });

      const client = new AiSdk({
        host: 'https://openmetadata.example.com',
        token: 'test-token',
      });

      await client.createAgent({
        name: 'test-agent',
        description: 'Test',
        persona: 'test-persona',
        mode: 'chat',
        knowledge: {
          entityTypes: ['table', 'dashboard'],
          services: [{ id: 'svc-1', type: 'databaseService', name: 'my-db' }],
        },
      });

      // The POST request is the second call (after persona GET)
      const requestBody = JSON.parse(mockFetch.mock.calls[1][1].body);
      expect(requestBody.knowledge).toEqual({
        entityTypes: ['table', 'dashboard'],
        services: [{ id: 'svc-1', type: 'databaseService', name: 'my-db' }],
      });
    });
  });
});
