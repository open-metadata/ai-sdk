/**
 * Integration tests for n8n OpenMetadata node.
 *
 * These tests verify the SDK integration works correctly.
 * Full n8n runtime tests would require a more complex setup.
 *
 * Environment variables:
 * - AI_SDK_HOST: Base URL of the OpenMetadata instance
 * - AI_SDK_TOKEN: JWT authentication token
 *
 * Run with: npm run test:integration
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { AiSdk } from '@openmetadata/ai-sdk';

// Skip tests if credentials not configured
const AI_SDK_HOST = process.env.AI_SDK_HOST;
const AI_SDK_TOKEN = process.env.AI_SDK_TOKEN;

const shouldRun = AI_SDK_HOST && AI_SDK_TOKEN;

describe.skipIf(!shouldRun)('n8n Node Integration Tests', () => {
  let client: AiSdk;

  beforeAll(() => {
    client = new AiSdk({
      host: AI_SDK_HOST!,
      token: AI_SDK_TOKEN!,
    });
  });

  describe('SDK Dependency', () => {
    it('should create AiSdk client from SDK', () => {
      expect(client).toBeDefined();
      expect(client.host).toBe(AI_SDK_HOST!.replace(/\/$/, ''));
    });

    it('should list agents via SDK', async () => {
      const agents = await client.listAgents();
      expect(Array.isArray(agents)).toBe(true);
      console.log(`SDK connection verified: Found ${agents.length} agents`);
    });
  });

  describe('Node Module Loading', () => {
    it('should load AiSdkAgent node class', async () => {
      // Dynamic import to test the built module
      const nodeModule = await import('../nodes/AiSdkAgent/AiSdkAgent.node');
      expect(nodeModule.AiSdkAgent).toBeDefined();
    });

    it('should load AiSdkApi credentials class', async () => {
      const credModule = await import('../credentials/AiSdkApi.credentials');
      expect(credModule.AiSdkApi).toBeDefined();
    });
  });
});
