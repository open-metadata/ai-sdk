/**
 * Agent handle for the Metadata AI SDK.
 *
 * This module provides the AgentHandle class for invoking specific agents.
 */

import type { HttpClient } from './http.js';
import {
  mapAgentInfo,
  type AgentInfo,
  type ApiAgentInfo,
  type ApiInvokeResponse,
  type InvokeOptions,
  type InvokeRequestBody,
  type InvokeResponse,
  type StreamEvent,
} from './models.js';
import { createStreamIterable } from './streaming.js';

/**
 * Convert API invoke response to InvokeResponse.
 */
function mapInvokeResponse(data: ApiInvokeResponse): InvokeResponse {
  return {
    conversationId: data.conversationId,
    response: data.response,
    toolsUsed: data.toolsUsed || [],
    usage: data.usage
      ? {
          promptTokens: data.usage.promptTokens || 0,
          completionTokens: data.usage.completionTokens || 0,
          totalTokens: data.usage.totalTokens || 0,
        }
      : undefined,
  };
}

/**
 * Handle for invoking a specific agent.
 *
 * This class provides methods for synchronous and streaming invocation
 * of Metadata AI agents.
 *
 * @example
 * ```typescript
 * // Get agent handle from client
 * const agent = client.agent('DataQualityPlannerAgent');
 *
 * // Synchronous invocation
 * const response = await agent.invoke('What tables have issues?');
 * console.log(response.response);
 *
 * // Streaming invocation
 * for await (const event of agent.stream('Analyze the orders table')) {
 *   if (event.type === 'content') {
 *     process.stdout.write(event.content || '');
 *   }
 * }
 * ```
 */
export class AgentHandle {
  private readonly agentName: string;
  private readonly http: HttpClient;

  /**
   * Create a new agent handle.
   *
   * @param name - The agent name
   * @param http - HTTP client for API communication
   * @internal This constructor is called by AiSdk.agent()
   */
  constructor(name: string, http: HttpClient) {
    this.agentName = name;
    this.http = http;
  }

  /**
   * Get the agent name.
   */
  get name(): string {
    return this.agentName;
  }

  /**
   * Invoke the agent synchronously.
   *
   * @param message - Optional query or instruction for the agent. If not provided, the agent's configured prompt will be used.
   * @param options - Optional invoke options (conversationId, parameters)
   * @returns Promise resolving to the complete response
   *
   * @throws {AgentNotFoundError} If the agent does not exist
   * @throws {AgentNotEnabledError} If the agent is not API-enabled
   * @throws {AuthenticationError} If the token is invalid
   * @throws {AgentExecutionError} If the agent execution fails
   *
   * @example
   * ```typescript
   * // Simple invocation
   * const response = await agent.invoke('What tables have quality issues?');
   * console.log(response.response);
   * console.log('Tools used:', response.toolsUsed);
   *
   * // Invoke without message (uses agent's configured prompt)
   * const response = await agent.invoke();
   *
   * // Multi-turn conversation
   * const r1 = await agent.invoke('Analyze the orders table');
   * const r2 = await agent.invoke('Now create tests for the issues', {
   *   conversationId: r1.conversationId,
   * });
   * ```
   */
  async invoke(message?: string, options?: InvokeOptions): Promise<InvokeResponse> {
    const requestBody: InvokeRequestBody = {};

    if (message !== undefined) {
      requestBody.message = message;
    }

    if (options?.conversationId) {
      requestBody.conversationId = options.conversationId;
    }

    if (options?.parameters && Object.keys(options.parameters).length > 0) {
      requestBody.parameters = options.parameters;
    }

    const data = await this.http.post<ApiInvokeResponse>(
      `/name/${this.agentName}/invoke`,
      requestBody,
      this.agentName
    );

    return mapInvokeResponse(data);
  }

  /**
   * Invoke the agent with streaming response.
   *
   * @param message - Optional query or instruction for the agent. If not provided, the agent's configured prompt will be used.
   * @param options - Optional invoke options (conversationId, parameters)
   * @returns Async iterable of stream events
   *
   * @throws {AgentNotFoundError} If the agent does not exist
   * @throws {AgentNotEnabledError} If the agent is not API-enabled
   * @throws {AuthenticationError} If the token is invalid
   * @throws {AgentExecutionError} If the agent execution fails
   *
   * @example
   * ```typescript
   * for await (const event of agent.stream('Analyze data quality')) {
   *   switch (event.type) {
   *     case 'start':
   *       console.log('Started conversation:', event.conversationId);
   *       break;
   *     case 'content':
   *       process.stdout.write(event.content || '');
   *       break;
   *     case 'tool_use':
   *       console.log('Using tool:', event.toolName);
   *       break;
   *     case 'end':
   *       console.log('\nCompleted');
   *       break;
   *     case 'error':
   *       console.error('Error:', event.error);
   *       break;
   *   }
   * }
   *
   * // Stream without message (uses agent's configured prompt)
   * for await (const event of agent.stream()) {
   *   // handle events
   * }
   * ```
   */
  async *stream(
    message?: string,
    options?: InvokeOptions
  ): AsyncGenerator<StreamEvent, void, unknown> {
    const requestBody: InvokeRequestBody = {};

    if (message !== undefined) {
      requestBody.message = message;
    }

    if (options?.conversationId) {
      requestBody.conversationId = options.conversationId;
    }

    if (options?.parameters && Object.keys(options.parameters).length > 0) {
      requestBody.parameters = options.parameters;
    }

    const byteStream = await this.http.postStream(
      `/name/${this.agentName}/stream`,
      requestBody,
      this.agentName
    );

    yield* createStreamIterable(byteStream);
  }

  /**
   * Get agent metadata including abilities and description.
   *
   * @returns Promise resolving to agent information
   *
   * @throws {AgentNotFoundError} If the agent does not exist
   * @throws {AgentNotEnabledError} If the agent is not API-enabled
   *
   * @example
   * ```typescript
   * const info = await agent.getInfo();
   * console.log('Agent:', info.displayName);
   * console.log('Description:', info.description);
   * console.log('Abilities:', info.abilities.join(', '));
   * ```
   */
  async getInfo(): Promise<AgentInfo> {
    const data = await this.http.get<ApiAgentInfo>(
      `/name/${this.agentName}`,
      undefined,
      this.agentName
    );

    return mapAgentInfo(data);
  }

  /**
   * String representation of the agent handle.
   */
  toString(): string {
    return `AgentHandle(name="${this.agentName}")`;
  }
}
