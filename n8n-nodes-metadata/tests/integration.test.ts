/**
 * Integration tests for n8n OpenMetadata node.
 *
 * These tests verify the SDK integration works correctly.
 * Full n8n runtime tests would require a more complex setup.
 *
 * Environment variables:
 * - METADATA_HOST: Base URL of the OpenMetadata instance
 * - METADATA_TOKEN: JWT authentication token
 *
 * Run with: npm run test:integration
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { MetadataAI } from '@openmetadata/ai-sdk';

// Skip tests if credentials not configured
const METADATA_HOST = process.env.METADATA_HOST;
const METADATA_TOKEN = process.env.METADATA_TOKEN;

const shouldRun = METADATA_HOST && METADATA_TOKEN;

describe.skipIf(!shouldRun)('n8n Node Integration Tests', () => {
  let client: MetadataAI;

  beforeAll(() => {
    client = new MetadataAI({
      host: METADATA_HOST!,
      token: METADATA_TOKEN!,
    });
  });

  describe('SDK Dependency', () => {
    it('should create MetadataAI client from SDK', () => {
      expect(client).toBeDefined();
      expect(client.host).toBe(METADATA_HOST!.replace(/\/$/, ''));
    });

    it('should list agents via SDK', async () => {
      const agents = await client.listAgents();
      expect(Array.isArray(agents)).toBe(true);
      console.log(`SDK connection verified: Found ${agents.length} agents`);
    });
  });

  describe('Node Module Loading', () => {
    it('should load MetadataAgent node class', async () => {
      // Dynamic import to test the built module
      const nodeModule = await import('../nodes/MetadataAgent/MetadataAgent.node');
      expect(nodeModule.MetadataAgent).toBeDefined();
    });

    it('should load MetadataApi credentials class', async () => {
      const credModule = await import('../credentials/MetadataApi.credentials');
      expect(credModule.MetadataApi).toBeDefined();
    });
  });
});
