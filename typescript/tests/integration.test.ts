/**
 * Integration tests for Metadata AI TypeScript SDK.
 *
 * These tests run against a real Metadata instance and require:
 * - METADATA_HOST: Base URL of the Metadata instance
 * - METADATA_TOKEN: JWT authentication token
 *
 * Optional:
 * - METADATA_RUN_CHAT_TESTS: Set to "true" to run chat tests - invoke and streaming (uses AI tokens)
 *
 * Run with: npm run test:integration
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { randomUUID } from 'crypto';
import {
  MetadataAI,
  AuthenticationError,
  PersonaNotFoundError,
  BotNotFoundError,
} from '../src';

// Skip tests if credentials not configured
const METADATA_HOST = process.env.METADATA_HOST;
const METADATA_TOKEN = process.env.METADATA_TOKEN;

const shouldRun = METADATA_HOST && METADATA_TOKEN;

// Check if chat tests should run (invoke + streaming - they use AI tokens)
const CHAT_TESTS_ENABLED = process.env.METADATA_RUN_CHAT_TESTS?.toLowerCase() === 'true';

/** Generate a unique name for test entities */
function uniqueName(prefix: string): string {
  return `${prefix}-test-${randomUUID().slice(0, 8)}`;
}

describe.skipIf(!shouldRun)('Integration Tests', () => {
  let client: MetadataAI;
  let testAgentName: string | null = null;

  beforeAll(async () => {
    client = new MetadataAI({
      host: METADATA_HOST!,
      token: METADATA_TOKEN!,
    });

    // Create a test agent with discoveryAndSearch ability for proper streaming tests
    const personas = await client.listPersonas();
    if (personas.length > 0) {
      const agentName = uniqueName('invoke-test-agent');
      try {
        await client.createAgent({
          name: agentName,
          description: 'Auto-created agent for integration testing',
          persona: personas[0].name,
          mode: 'chat',
          abilities: ['discoveryAndSearch'],
          apiEnabled: true,
        });
        testAgentName = agentName;
      } catch (e) {
        console.log(`Could not create test agent: ${e}`);
        // Fall back to first available agent
        const agents = await client.listAgents();
        if (agents.length > 0) {
          testAgentName = agents[0].name;
        }
      }
    }
  });

  describe('Connection', () => {
    it('should create client with valid credentials', () => {
      expect(client).toBeDefined();
      expect(client.host).toBe(METADATA_HOST!.replace(/\/$/, ''));
    });

    it('should list agents successfully', async () => {
      const agents = await client.listAgents();
      expect(Array.isArray(agents)).toBe(true);
      console.log(`Found ${agents.length} API-enabled agents`);
    });

    it('should reject invalid token', async () => {
      const badClient = new MetadataAI({
        host: METADATA_HOST!,
        token: 'invalid-token-12345',
      });

      await expect(badClient.listAgents()).rejects.toThrow(AuthenticationError);
    });
  });

  describe('Agent Operations', () => {
    it('should get agent info', async () => {
      if (!testAgentName) {
        console.log('Skipping: No test agent available');
        return;
      }

      const agent = client.agent(testAgentName);
      const info = await agent.getInfo();

      expect(info).toBeDefined();
      expect(info.name).toBe(testAgentName);
      console.log(`Agent '${testAgentName}' info: ${info.description || 'No description'}`);
    });

    it.skipIf(!CHAT_TESTS_ENABLED)('should invoke agent with simple message', async () => {
      if (!testAgentName) {
        console.log('Skipping: No test agent available');
        return;
      }

      const agent = client.agent(testAgentName);
      const response = await agent.invoke('Hello, this is an integration test. Please respond briefly.');

      expect(response).toBeDefined();
      expect(response.response).toBeDefined();
      expect(response.response.length).toBeGreaterThan(0);
      console.log(`Agent response: ${response.response.substring(0, 200)}...`);
    });

    it.skipIf(!CHAT_TESTS_ENABLED)('should stream agent response', async () => {
      if (!testAgentName) {
        console.log('Skipping: No test agent available');
        return;
      }

      const agent = client.agent(testAgentName);
      const chunks: string[] = [];

      // Use a prompt that triggers tool use with discoveryAndSearch ability
      for await (const event of agent.stream('do we have any customer data')) {
        if (event.content) {
          chunks.push(event.content);
        }
      }

      expect(chunks.length).toBeGreaterThan(0);
      const fullResponse = chunks.join('');
      console.log(`Streamed response: ${fullResponse.substring(0, 200)}...`);
    }, 120000);  // 2 minute timeout for streaming
  });

  describe('Persona Operations', () => {
    it('should list personas', async () => {
      const personas = await client.listPersonas();
      expect(Array.isArray(personas)).toBe(true);
      console.log(`Found ${personas.length} personas`);
    });

    it('should list personas with limit', async () => {
      const personas = await client.listPersonas({ limit: 5 });
      expect(Array.isArray(personas)).toBe(true);
      expect(personas.length).toBeLessThanOrEqual(5);
    });

    it('should get persona by name', async () => {
      const personas = await client.listPersonas();
      if (personas.length === 0) {
        console.log('Skipping: No personas available');
        return;
      }

      const personaName = personas[0].name;
      const persona = await client.getPersona(personaName);

      expect(persona).toBeDefined();
      expect(persona.name).toBe(personaName);
      console.log(`Got persona: ${persona.name} (${persona.displayName || 'No display name'})`);
    });

    it('should throw PersonaNotFoundError for non-existent persona', async () => {
      await expect(client.getPersona('non-existent-persona-12345')).rejects.toThrow(
        PersonaNotFoundError
      );
    });

    it('should create a persona', async () => {
      const personaName = uniqueName('persona');
      const created = await client.createPersona({
        name: personaName,
        description: 'Integration test persona',
        prompt: 'You are a helpful test assistant.',
        displayName: 'Test Persona',
      });

      expect(created).toBeDefined();
      expect(created.name).toBe(personaName);
      expect(created.description).toBe('Integration test persona');
      console.log(`Created persona: ${created.name}`);
    });
  });

  describe('Bot Operations', () => {
    it('should list bots', async () => {
      const bots = await client.listBots();
      expect(Array.isArray(bots)).toBe(true);
      console.log(`Found ${bots.length} bots`);
    });

    it('should list bots with limit', async () => {
      const bots = await client.listBots({ limit: 5 });
      expect(Array.isArray(bots)).toBe(true);
      expect(bots.length).toBeLessThanOrEqual(5);
    });

    it('should get bot by name', async () => {
      const bots = await client.listBots();
      if (bots.length === 0) {
        console.log('Skipping: No bots available');
        return;
      }

      const botName = bots[0].name;
      const bot = await client.getBot(botName);

      expect(bot).toBeDefined();
      expect(bot.name).toBe(botName);
      console.log(`Got bot: ${bot.name} (${bot.displayName || 'No display name'})`);
    });

    it('should throw BotNotFoundError for non-existent bot', async () => {
      await expect(client.getBot('non-existent-bot-12345')).rejects.toThrow(BotNotFoundError);
    });
  });

  describe('Ability Operations', () => {
    it('should list abilities', async () => {
      const abilities = await client.listAbilities();
      expect(Array.isArray(abilities)).toBe(true);
      console.log(`Found ${abilities.length} abilities`);
    });

    it('should list abilities with limit', async () => {
      const abilities = await client.listAbilities({ limit: 5 });
      expect(Array.isArray(abilities)).toBe(true);
      expect(abilities.length).toBeLessThanOrEqual(5);
    });

    it('should have expected fields on abilities', async () => {
      const abilities = await client.listAbilities();
      if (abilities.length === 0) {
        console.log('Skipping: No abilities available');
        return;
      }

      const ability = abilities[0];
      expect(ability.name).toBeDefined();
      console.log(`Ability: ${ability.name}`);
    });
  });

  describe('Agent CRUD Operations', () => {
    it('should create an agent', async () => {
      const personas = await client.listPersonas();
      if (personas.length === 0) {
        console.log('Skipping: No personas available to create agent');
        return;
      }

      const agentName = uniqueName('agent');
      const created = await client.createAgent({
        name: agentName,
        description: 'Integration test agent',
        persona: personas[0].name,
        mode: 'chat',
        apiEnabled: true,
      });

      expect(created).toBeDefined();
      expect(created.name).toBe(agentName);
      console.log(`Created agent: ${created.name}`);
    });

    it('should create an agent with abilities', async () => {
      const personas = await client.listPersonas();
      const abilities = await client.listAbilities();

      if (personas.length === 0) {
        console.log('Skipping: No personas available');
        return;
      }
      if (abilities.length === 0) {
        console.log('Skipping: No abilities available');
        return;
      }

      const agentName = uniqueName('agent-abilities');
      const abilityNames = abilities.slice(0, 2).map((a) => a.name);

      const created = await client.createAgent({
        name: agentName,
        description: 'Integration test agent with abilities',
        persona: personas[0].name,
        mode: 'agent',
        abilities: abilityNames,
        apiEnabled: true,
      });

      expect(created).toBeDefined();
      expect(created.name).toBe(agentName);
      console.log(`Created agent with abilities: ${created.name}`);
    });
  });
});
