/**
 * Metadata AI SDK for Node.js
 *
 * A TypeScript SDK for interacting with OpenMetadata Dynamic Agents.
 *
 * @packageDocumentation
 *
 * @example
 * ```typescript
 * import { MetadataAI } from '@openmetadata/metadata-ai';
 *
 * // Initialize the client
 * const client = new MetadataAI({
 *   host: 'https://openmetadata.example.com',
 *   token: 'your-bot-jwt-token',
 * });
 *
 * // Synchronous invocation
 * const response = await client.agent('DataQualityPlannerAgent')
 *   .invoke('What tables have quality issues?');
 * console.log(response.response);
 *
 * // Streaming invocation
 * for await (const event of client.agent('DataQualityPlannerAgent')
 *   .stream('Analyze the orders table')) {
 *   if (event.type === 'content') {
 *     process.stdout.write(event.content || '');
 *   }
 * }
 *
 * // Multi-turn conversation
 * const r1 = await client.agent('planner').invoke('Analyze orders');
 * const r2 = await client.agent('planner').invoke('Create tests', {
 *   conversationId: r1.conversationId,
 * });
 *
 * // List available agents
 * const agents = await client.listAgents();
 * ```
 */

// Main client
export { MetadataAI } from './client.js';

// Agent handle
export { AgentHandle } from './agent.js';

// Models and types
export type {
  MetadataAIOptions,
  InvokeOptions,
  InvokeResponse,
  StreamEvent,
  StreamEventType,
  Usage,
  AgentInfo,
} from './models.js';

// Extended types for bots, personas, agents, and abilities
export type {
  EntityReference,
  BotInfo,
  PersonaInfo,
  AbilityInfo,
  KnowledgeScope,
  CreatePersonaRequest,
  CreateAgentRequest,
} from './types.js';

// Error classes
export {
  MetadataError,
  AuthenticationError,
  AgentNotFoundError,
  AgentNotEnabledError,
  RateLimitError,
  AgentExecutionError,
  NetworkError,
  TimeoutError,
  BotNotFoundError,
  PersonaNotFoundError,
  AbilityNotFoundError,
} from './errors.js';

// Streaming utilities (for advanced use cases)
export { parseSSEStream, createStreamIterable } from './streaming.js';
