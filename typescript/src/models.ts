/**
 * Data models for the Metadata AI SDK.
 *
 * These interfaces define the request/response structures for
 * communicating with the Metadata AI Agent API.
 */

/**
 * Configuration options for the MetadataAI client.
 */
export interface MetadataAIOptions {
  /** The OpenMetadata server URL (e.g., "https://openmetadata.example.com") */
  host: string;
  /** JWT bot token for authentication */
  token: string;
  /** Request timeout in milliseconds (default: 120000) */
  timeout?: number;
  /** Whether to verify SSL certificates (default: true, limited in Node fetch) */
  verifySsl?: boolean;
  /** Maximum number of retry attempts for transient errors (default: 3) */
  maxRetries?: number;
  /** Base delay between retries in milliseconds (default: 1000) */
  retryDelay?: number;
}

/**
 * Options for invoking an agent.
 */
export interface InvokeOptions {
  /** Optional conversation ID for multi-turn conversations */
  conversationId?: string;
  /** Optional parameters to pass to the agent */
  parameters?: Record<string, unknown>;
}

/**
 * Token usage statistics from an agent invocation.
 */
export interface Usage {
  /** Number of tokens in the prompt */
  promptTokens: number;
  /** Number of tokens in the completion */
  completionTokens: number;
  /** Total number of tokens used */
  totalTokens: number;
}

/**
 * Response from a synchronous agent invocation.
 */
export interface InvokeResponse {
  /** Conversation ID for multi-turn conversations */
  conversationId: string;
  /** The agent's response text */
  response: string;
  /** List of tools used by the agent during execution */
  toolsUsed: string[];
  /** Optional token usage statistics */
  usage?: Usage;
}

/**
 * Event types for streaming responses.
 */
export type StreamEventType = 'start' | 'content' | 'tool_use' | 'end' | 'error';

/**
 * Event from a streaming agent response.
 */
export interface StreamEvent {
  /** Event type */
  type: StreamEventType;
  /** Content for 'content' events */
  content?: string;
  /** Tool name for 'tool_use' events */
  toolName?: string;
  /** Conversation ID (available on 'start' and 'end' events) */
  conversationId?: string;
  /** Error message for 'error' events */
  error?: string;
}

/**
 * Information about an available agent.
 */
export interface AgentInfo {
  /** Agent name (identifier used for API calls) */
  name: string;
  /** Human-readable display name */
  displayName: string;
  /** Agent description */
  description: string;
  /** List of agent abilities/capabilities */
  abilities: string[];
  /** Whether the agent is enabled for API access */
  apiEnabled: boolean;
}

/**
 * Internal request body structure for agent invocation.
 * @internal
 */
export interface InvokeRequestBody {
  message?: string;
  conversationId?: string;
  parameters?: Record<string, unknown>;
}

/**
 * Paginated list response from the API.
 * @internal
 */
export interface PaginatedResponse<T> {
  data: T[];
  paging?: {
    total?: number;
    offset?: number;
    limit?: number;
    after?: string;
    before?: string;
  };
}

/**
 * API response for agent info (maps to internal format).
 * @internal
 */
export interface ApiAgentInfo {
  name: string;
  displayName?: string;
  description?: string;
  abilities?: string[];
  apiEnabled?: boolean;
}

/**
 * API response for invoke (maps to internal format).
 * @internal
 */
export interface ApiInvokeResponse {
  conversationId: string;
  response: string;
  toolsUsed?: string[];
  usage?: {
    promptTokens?: number;
    completionTokens?: number;
    totalTokens?: number;
  };
}
