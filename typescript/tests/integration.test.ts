/**
 * Integration tests for Metadata AI TypeScript SDK.
 *
 * These tests run against a real Metadata instance and require:
 * - AI_SDK_HOST: Base URL of the Metadata instance
 * - AI_SDK_TOKEN: JWT authentication token
 *
 * Optional:
 * - AI_SDK_RUN_CHAT_TESTS: Set to "true" to run chat tests - invoke and streaming (uses AI tokens)
 *
 * Run with: npm run test:integration
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { randomUUID } from 'crypto';
import {
  AISdk,
  AuthenticationError,
  PersonaNotFoundError,
  BotNotFoundError,
} from '../src';

// Skip tests if credentials not configured
const AI_SDK_HOST = process.env.AI_SDK_HOST;
const AI_SDK_TOKEN = process.env.AI_SDK_TOKEN;

const shouldRun = AI_SDK_HOST && AI_SDK_TOKEN;

// Check if chat tests should run (invoke + streaming - they use AI tokens)
const CHAT_TESTS_ENABLED = process.env.AI_SDK_RUN_CHAT_TESTS?.toLowerCase() === 'true';

/** Generate a unique name for test entities */
function uniqueName(prefix: string): string {
  return `${prefix}-test-${randomUUID().slice(0, 8)}`;
}

describe.skipIf(!shouldRun)('Integration Tests', () => {
  let client: AISdk;
  let testAgentName: string | null = null;

  beforeAll(async () => {
    client = new AISdk({
      host: AI_SDK_HOST!,
      token: AI_SDK_TOKEN!,
    });

    // Create a test agent with discoveryAndSearch skill for proper streaming tests
    const personas = await client.personas.list();
    if (personas.length > 0) {
      const agentName = uniqueName('invoke-test-agent');
      try {
        await client.agents.create({
          name: agentName,
          description: 'Auto-created agent for integration testing',
          persona: personas[0].name,
          mode: 'chat',
          skills: ['discoveryAndSearch'],
          apiEnabled: true,
        });
        testAgentName = agentName;
      } catch (e) {
        console.log(`Could not create test agent: ${e}`);
        // Fall back to first available agent
        const agents = await client.agents.list();
        if (agents.length > 0) {
          testAgentName = agents[0].name;
        }
      }
    }
  });

  describe('Connection', () => {
    it('should create client with valid credentials', () => {
      expect(client).toBeDefined();
      expect(client.host).toBe(AI_SDK_HOST!.replace(/\/$/, ''));
    });

    it('should list agents successfully', async () => {
      const agents = await client.agents.list();
      expect(Array.isArray(agents)).toBe(true);
      console.log(`Found ${agents.length} API-enabled agents`);
    });

    it('should reject invalid token', async () => {
      const badClient = new AISdk({
        host: AI_SDK_HOST!,
        token: 'invalid-token-12345',
      });

      await expect(badClient.agents.list()).rejects.toThrow(AuthenticationError);
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

      // Use a prompt that triggers tool use with discoveryAndSearch skill
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
      const personas = await client.personas.list();
      expect(Array.isArray(personas)).toBe(true);
      console.log(`Found ${personas.length} personas`);
    });

    it('should list personas with limit', async () => {
      const personas = await client.personas.list({ limit: 5 });
      expect(Array.isArray(personas)).toBe(true);
      expect(personas.length).toBeLessThanOrEqual(5);
    });

    it('should get persona by name', async () => {
      const personas = await client.personas.list();
      if (personas.length === 0) {
        console.log('Skipping: No personas available');
        return;
      }

      const personaName = personas[0].name;
      const persona = await client.personas.get(personaName);

      expect(persona).toBeDefined();
      expect(persona.name).toBe(personaName);
      console.log(`Got persona: ${persona.name} (${persona.displayName || 'No display name'})`);
    });

    it('should throw PersonaNotFoundError for non-existent persona', async () => {
      await expect(client.personas.get('non-existent-persona-12345')).rejects.toThrow(
        PersonaNotFoundError
      );
    });

    it('should create a persona', async () => {
      const personaName = uniqueName('persona');
      const created = await client.personas.create({
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
      const bots = await client.bots.list();
      expect(Array.isArray(bots)).toBe(true);
      console.log(`Found ${bots.length} bots`);
    });

    it('should list bots with limit', async () => {
      const bots = await client.bots.list({ limit: 5 });
      expect(Array.isArray(bots)).toBe(true);
      expect(bots.length).toBeLessThanOrEqual(5);
    });

    it('should get bot by name', async () => {
      const bots = await client.bots.list();
      if (bots.length === 0) {
        console.log('Skipping: No bots available');
        return;
      }

      const botName = bots[0].name;
      const bot = await client.bots.get(botName);

      expect(bot).toBeDefined();
      expect(bot.name).toBe(botName);
      console.log(`Got bot: ${bot.name} (${bot.displayName || 'No display name'})`);
    });

    it('should throw BotNotFoundError for non-existent bot', async () => {
      await expect(client.bots.get('non-existent-bot-12345')).rejects.toThrow(BotNotFoundError);
    });
  });

  describe('Skill Operations', () => {
    it('should list skills', async () => {
      const skills = await client.skills.list();
      expect(Array.isArray(skills)).toBe(true);
      console.log(`Found ${skills.length} skills`);
    });

    it('should list skills with limit', async () => {
      const skills = await client.skills.list({ limit: 5 });
      expect(Array.isArray(skills)).toBe(true);
      expect(skills.length).toBeLessThanOrEqual(5);
    });

    it('should have expected fields on skills', async () => {
      const skills = await client.skills.list();
      if (skills.length === 0) {
        console.log('Skipping: No skills available');
        return;
      }

      const skill = skills[0];
      expect(skill.name).toBeDefined();
      console.log(`Skill: ${skill.name}`);
    });
  });

  describe('Agent CRUD Operations', () => {
    it('should create an agent', async () => {
      const personas = await client.personas.list();
      if (personas.length === 0) {
        console.log('Skipping: No personas available to create agent');
        return;
      }

      const agentName = uniqueName('agent');
      const created = await client.agents.create({
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

    it('should create an agent with skills', async () => {
      const personas = await client.personas.list();
      const skills = await client.skills.list();

      if (personas.length === 0) {
        console.log('Skipping: No personas available');
        return;
      }
      if (skills.length === 0) {
        console.log('Skipping: No skills available');
        return;
      }

      const agentName = uniqueName('agent-skills');
      const skillNames = skills.slice(0, 2).map((a) => a.name);

      const created = await client.agents.create({
        name: agentName,
        description: 'Integration test agent with skills',
        persona: personas[0].name,
        mode: 'agent',
        skills: skillNames,
        apiEnabled: true,
      });

      expect(created).toBeDefined();
      expect(created.name).toBe(agentName);
      console.log(`Created agent with skills: ${created.name}`);
    });
  });
});
