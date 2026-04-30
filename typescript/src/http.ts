/**
 * HTTP client for the Metadata AI SDK.
 *
 * This module provides a thin wrapper around the native fetch API
 * with support for:
 * - Automatic retry with exponential backoff
 * - Request correlation IDs for debugging
 * - Proper error handling and mapping
 * - Custom base URL support for different API endpoints
 */

import {
  AbilityNotFoundError,
  AgentExecutionError,
  AgentNotEnabledError,
  AgentNotFoundError,
  AuthenticationError,
  BotNotFoundError,
  AISdkError,
  NetworkError,
  PersonaNotFoundError,
  RateLimitError,
  TimeoutError,
} from './errors.js';

/** Status codes that should trigger a retry */
const RETRYABLE_STATUS_CODES = new Set([429, 500, 502, 503, 504]);

/**
 * Generate a unique request ID for correlation.
 */
function generateRequestId(): string {
  return Math.random().toString(36).substring(2, 10);
}

/**
 * Options for HTTP client configuration.
 */
export interface HttpClientOptions {
  /** Base URL for API requests */
  baseUrl: string;
  /** JWT token for authentication */
  token: string;
  /** Request timeout in milliseconds */
  timeout: number;
  /** Maximum number of retry attempts */
  maxRetries: number;
  /** Base delay between retries in milliseconds */
  retryDelay: number;
}

/**
 * Entity type for error context.
 */
export type EntityType = 'agent' | 'bot' | 'persona' | 'ability';

/**
 * Options for individual HTTP requests.
 */
export interface RequestOptions {
  /** HTTP method */
  method: 'GET' | 'POST' | 'DELETE';
  /** Request path (appended to baseUrl) */
  path: string;
  /** Request body (for POST requests) */
  body?: unknown;
  /** Query parameters (for GET/DELETE requests) */
  params?: Record<string, string | number | boolean>;
  /** Agent name for error context */
  agentName?: string;
  /** Entity type for error context (default: 'agent') */
  entityType?: EntityType;
  /** Entity name for error context */
  entityName?: string;
  /** Whether this is a streaming request */
  stream?: boolean;
}

/**
 * HTTP client for API communication with retry support.
 */
export class HttpClient {
  private readonly baseUrl: string;
  private readonly token: string;
  private readonly timeout: number;
  private readonly maxRetries: number;
  private readonly retryDelay: number;
  private readonly userAgent = 'ai-sdk-ts/0.0.2';

  constructor(options: HttpClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/$/, '');
    this.token = options.token;
    this.timeout = options.timeout;
    this.maxRetries = options.maxRetries;
    this.retryDelay = options.retryDelay;
  }

  /**
   * Build request headers.
   */
  private getHeaders(requestId: string, stream = false): Record<string, string> {
    return {
      Authorization: `Bearer ${this.token}`,
      'Content-Type': 'application/json',
      Accept: stream ? 'text/event-stream' : 'application/json',
      'User-Agent': this.userAgent,
      'X-Request-ID': requestId,
    };
  }

  /**
   * Build full URL with query parameters.
   */
  private buildUrl(
    path: string,
    params?: Record<string, string | number | boolean>
  ): string {
    // Construct full URL by appending path to base URL
    const fullPath = path.startsWith('/') ? path : `/${path}`;
    const urlString = `${this.baseUrl}${fullPath}`;
    const url = new URL(urlString);
    if (params) {
      for (const [key, value] of Object.entries(params)) {
        url.searchParams.set(key, String(value));
      }
    }
    return url.toString();
  }

  /**
   * Check if a response status should trigger a retry.
   */
  private shouldRetry(status: number, attempt: number): boolean {
    if (attempt >= this.maxRetries) {
      return false;
    }
    return RETRYABLE_STATUS_CODES.has(status);
  }

  /**
   * Calculate retry delay with exponential backoff.
   */
  private getRetryDelay(attempt: number, retryAfterHeader?: string | null): number {
    if (retryAfterHeader) {
      const parsed = parseInt(retryAfterHeader, 10);
      if (!isNaN(parsed)) {
        return parsed * 1000; // Convert seconds to milliseconds
      }
    }
    return this.retryDelay * Math.pow(2, attempt);
  }

  /**
   * Wait for the specified delay.
   */
  private async wait(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * Handle error responses and throw appropriate exceptions.
   */
  private async handleError(
    response: Response,
    agentName?: string,
    _requestId?: string,
    entityType?: EntityType,
    entityName?: string
  ): Promise<never> {
    const status = response.status;

    if (status === 401) {
      throw new AuthenticationError();
    }

    if (status === 403) {
      if (agentName) {
        throw new AgentNotEnabledError(agentName);
      }
      throw new AISdkError('Access forbidden', 403);
    }

    if (status === 404) {
      // Check entity type for specific error classes
      if (entityType === 'bot' && entityName) {
        throw new BotNotFoundError(entityName);
      }
      if (entityType === 'persona' && entityName) {
        throw new PersonaNotFoundError(entityName);
      }
      if (entityType === 'ability' && entityName) {
        throw new AbilityNotFoundError(entityName);
      }
      if (agentName) {
        throw new AgentNotFoundError(agentName);
      }
      throw new AISdkError('Resource not found', 404);
    }

    if (status === 429) {
      const retryAfter = response.headers.get('Retry-After');
      const retrySeconds = retryAfter ? parseInt(retryAfter, 10) : undefined;
      throw new RateLimitError('Rate limit exceeded', retrySeconds);
    }

    // Try to extract error message from response body
    let message: string;
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      try {
        const errorData = (await response.json()) as { message?: string };
        message = errorData.message || response.statusText;
      } catch {
        message = response.statusText;
      }
    } else {
      message = await response.text().catch(() => response.statusText);
    }

    throw new AgentExecutionError(
      `API error (${status}): ${message}`,
      agentName
    );
  }

  /**
   * Make a GET request with retry support.
   */
  async get<T>(
    path: string,
    params?: Record<string, string | number | boolean>,
    agentName?: string,
    entityType?: EntityType,
    entityName?: string
  ): Promise<T> {
    return this.request<T>({
      method: 'GET',
      path,
      params,
      agentName,
      entityType,
      entityName,
    });
  }

  /**
   * Make a POST request with retry support.
   */
  async post<T>(
    path: string,
    body: unknown,
    agentName?: string,
    entityType?: EntityType,
    entityName?: string
  ): Promise<T> {
    return this.request<T>({
      method: 'POST',
      path,
      body,
      agentName,
      entityType,
      entityName,
    });
  }

  /**
   * Make a DELETE request with retry support.
   *
   * Returns void for empty responses; otherwise the parsed JSON body.
   */
  async delete<T = void>(
    path: string,
    params?: Record<string, string | number | boolean>,
    agentName?: string,
    entityType?: EntityType,
    entityName?: string
  ): Promise<T> {
    return this.request<T>({
      method: 'DELETE',
      path,
      params,
      agentName,
      entityType,
      entityName,
    });
  }

  /**
   * Make a streaming POST request.
   *
   * Note: Streaming requests don't support automatic retry.
   *
   * Unlike non-streaming methods, `postStream` intentionally does NOT apply
   * `this.timeout` as a request deadline. SSE streams can run for many
   * minutes (long agent runs with multiple tool calls), and the stream's
   * own events signal liveness. A fixed deadline would cut the stream
   * mid-run regardless of progress. Callers that need cancellation can
   * abort externally (e.g. close the underlying ReadableStream / Ctrl+C).
   */
  async postStream(
    path: string,
    body: unknown,
    agentName?: string
  ): Promise<ReadableStream<Uint8Array>> {
    const requestId = generateRequestId();
    const url = this.buildUrl(path);
    const headers = this.getHeaders(requestId, true);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        await this.handleError(response, agentName, requestId);
      }

      if (!response.body) {
        throw new AISdkError('No response body for streaming request');
      }

      return response.body;
    } catch (error) {
      if (error instanceof AISdkError) {
        throw error;
      }

      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          // Caller-initiated abort (no internal deadline is applied here).
          throw new TimeoutError(this.timeout);
        }
        throw new NetworkError(`Network error: ${error.message}`, error);
      }

      throw new NetworkError('Unknown network error');
    }
  }

  /**
   * Parse the response body. Returns undefined for empty / 204 responses
   * (e.g. DELETE) so callers can declare a `void` return type.
   */
  private async parseBody<T>(response: Response): Promise<T> {
    if (response.status === 204) {
      return undefined as T;
    }
    const contentLength = response.headers?.get?.('content-length');
    if (contentLength === '0') {
      return undefined as T;
    }
    try {
      return (await response.json()) as T;
    } catch {
      return undefined as T;
    }
  }

  /**
   * Internal request method with retry logic.
   */
  private async request<T>(options: RequestOptions): Promise<T> {
    const { method, path, body, params, agentName, entityType, entityName } = options;
    const requestId = generateRequestId();
    const url = this.buildUrl(path, params);
    const headers = this.getHeaders(requestId);

    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);

      try {
        const response = await fetch(url, {
          method,
          headers,
          body: body ? JSON.stringify(body) : undefined,
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        if (response.ok) {
          return await this.parseBody<T>(response);
        }

        // Check if we should retry
        if (this.shouldRetry(response.status, attempt)) {
          const delay = this.getRetryDelay(
            attempt,
            response.headers.get('Retry-After')
          );
          await this.wait(delay);
          continue;
        }

        // Non-retryable error
        await this.handleError(response, agentName, requestId, entityType, entityName);
      } catch (error) {
        clearTimeout(timeoutId);

        if (error instanceof AISdkError) {
          throw error;
        }

        if (error instanceof Error) {
          if (error.name === 'AbortError') {
            lastError = new TimeoutError(this.timeout);
            // Timeouts are retryable
            if (attempt < this.maxRetries) {
              const delay = this.retryDelay * Math.pow(2, attempt);
              await this.wait(delay);
              continue;
            }
            throw lastError;
          }
          lastError = new NetworkError(`Network error: ${error.message}`, error);
          // Network errors are retryable
          if (attempt < this.maxRetries) {
            const delay = this.retryDelay * Math.pow(2, attempt);
            await this.wait(delay);
            continue;
          }
          throw lastError;
        }

        throw new NetworkError('Unknown network error');
      }
    }

    // Should never reach here, but TypeScript needs this
    throw lastError || new NetworkError('Request failed after retries');
  }
}
