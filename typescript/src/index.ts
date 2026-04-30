/**
 * Metadata AI SDK for Node.js
 *
 * A TypeScript SDK for interacting with OpenMetadata Dynamic Agents.
 *
 * @packageDocumentation
 *
 * @example
 * ```typescript
 * import { AISdk } from '@openmetadata/ai-sdk';
 *
 * // Initialize the client
 * const client = new AISdk({
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
 * // List available agents (namespaced)
 * const agents = await client.agents.list();
 *
 * // Search Context Center memories
 * const results = await client.memories.search('customer churn');
 * ```
 */

// Main client
export { AISdk } from './client.js';

// Agent handles
export { AgentHandle, DefaultAgentHandle } from './agent.js';

// Namespace classes
export {
  AbilitiesApi,
  AgentsApi,
  BotsApi,
  MemoriesApi,
  PersonasApi,
  type AbilitiesListOptions,
  type AgentsListOptions,
  type BotsListOptions,
  type MemoriesListOptions,
  type MemoriesSearchOptions,
  type PersonasListOptions,
} from './api/index.js';

// Models and types
export type {
  AISdkOptions,
  InvokeOptions,
  InvokeResponse,
  StreamEvent,
  StreamEventType,
  Usage,
  AgentInfo,
} from './models.js';

// Extended types for bots, personas, agents, abilities, and memories
export type {
  EntityReference,
  BotInfo,
  PersonaInfo,
  AbilityInfo,
  KnowledgeScope,
  CreatePersonaRequest,
  CreateAgentRequest,
  ContextMemory,
  CreateContextMemoryRequest,
  MemoryScope,
  MemorySearchHit,
  MemorySearchResults,
  MemoryType,
  MemoryVisibility,
} from './types.js';

// Error classes
export {
  AISdkError,
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
