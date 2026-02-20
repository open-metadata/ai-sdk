/**
 * Metadata AI SDK for Node.js
 *
 * A TypeScript SDK for interacting with OpenMetadata Dynamic Agents.
 *
 * @packageDocumentation
 *
 * @example
 * ```typescript
 * import { AiSdk } from '@openmetadata/ai-sdk';
 *
 * // Initialize the client
 * const client = new AiSdk({
 *   host: 'https://openmetadata.example.com',
 *   token: 'your-bot-jwt-token',
 * });
 *
 * // Synchronous invocation
 * const response = await client.agent('DataQualityPlannerAgent')
 *   .invoke('What tables have quality issues?');
 * console.log(response.response);
 *
 * // Streaming (simple - content only)
 * for await (const chunk of client.agent('DataQualityPlannerAgent')
 *   .streamContent('Analyze the orders table')) {
 *   process.stdout.write(chunk);
 * }
 *
 * // Streaming (advanced - all events)
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
export { AiSdk } from './client.js';

// Agent handle
export { AgentHandle } from './agent.js';

// Models and types
export type {
  AiSdkOptions,
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
  AiSdkError,
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
