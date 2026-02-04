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
  MetadataError,
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
  method: 'GET' | 'POST';
  /** Request path (appended to baseUrl) */
  path: string;
  /** Request body (for POST requests) */
  body?: unknown;
  /** Query parameters (for GET requests) */
  params?: Record<string, string | number>;
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
  /** The root host URL (without API path) */
  public readonly hostUrl: string;
  private readonly token: string;
  private readonly timeout: number;
  private readonly maxRetries: number;
  private readonly retryDelay: number;
  private readonly userAgent = 'metadata-ai-sdk-ts/0.1.0';

  constructor(options: HttpClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/$/, '');
    // Extract host URL from base URL (remove /api/v1/api/agents suffix)
    this.hostUrl = this.baseUrl.replace(/\/api\/v1\/api\/agents$/, '');
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
  private buildUrl(path: string, params?: Record<string, string | number>): string {
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
      throw new MetadataError('Access forbidden', 403);
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
      throw new MetadataError('Resource not found', 404);
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
    params?: Record<string, string | number>,
    agentName?: string
  ): Promise<T> {
    return this.request<T>({
      method: 'GET',
      path,
      params,
      agentName,
    });
  }

  /**
   * Make a POST request with retry support.
   */
  async post<T>(path: string, body: unknown, agentName?: string): Promise<T> {
    return this.request<T>({
      method: 'POST',
      path,
      body,
      agentName,
    });
  }

  /**
   * Make a GET request to a custom API path (relative to host URL).
   * This allows accessing endpoints outside the default /api/v1/api/agents base.
   */
  async getAbsolute<T>(
    apiPath: string,
    params?: Record<string, string | number>,
    entityType?: EntityType,
    entityName?: string
  ): Promise<T> {
    return this.requestAbsolute<T>({
      method: 'GET',
      path: apiPath,
      params,
      entityType,
      entityName,
    });
  }

  /**
   * Make a POST request to a custom API path (relative to host URL).
   * This allows accessing endpoints outside the default /api/v1/api/agents base.
   */
  async postAbsolute<T>(
    apiPath: string,
    body: unknown,
    entityType?: EntityType,
    entityName?: string
  ): Promise<T> {
    return this.requestAbsolute<T>({
      method: 'POST',
      path: apiPath,
      body,
      entityType,
      entityName,
    });
  }

  /**
   * Make a streaming POST request.
   *
   * Note: Streaming requests don't support automatic retry.
   */
  async postStream(
    path: string,
    body: unknown,
    agentName?: string
  ): Promise<ReadableStream<Uint8Array>> {
    const requestId = generateRequestId();
    const url = this.buildUrl(path);
    const headers = this.getHeaders(requestId, true);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        await this.handleError(response, agentName, requestId);
      }

      if (!response.body) {
        throw new MetadataError('No response body for streaming request');
      }

      return response.body;
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof MetadataError) {
        throw error;
      }

      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw new TimeoutError(this.timeout);
        }
        throw new NetworkError(`Network error: ${error.message}`, error);
      }

      throw new NetworkError('Unknown network error');
    }
  }

  /**
   * Internal request method with retry logic.
   */
  private async request<T>(options: RequestOptions): Promise<T> {
    const { method, path, body, params, agentName } = options;
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
          return (await response.json()) as T;
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
        await this.handleError(response, agentName, requestId);
      } catch (error) {
        clearTimeout(timeoutId);

        if (error instanceof MetadataError) {
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

  /**
   * Build URL with custom API path (relative to host URL).
   */
  private buildAbsoluteUrl(apiPath: string, params?: Record<string, string | number>): string {
    const fullPath = apiPath.startsWith('/') ? apiPath : `/${apiPath}`;
    const urlString = `${this.hostUrl}${fullPath}`;
    const url = new URL(urlString);
    if (params) {
      for (const [key, value] of Object.entries(params)) {
        url.searchParams.set(key, String(value));
      }
    }
    return url.toString();
  }

  /**
   * Internal request method for absolute paths with retry logic.
   */
  private async requestAbsolute<T>(options: RequestOptions): Promise<T> {
    const { method, path, body, params, entityType, entityName } = options;
    const requestId = generateRequestId();
    const url = this.buildAbsoluteUrl(path, params);
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
          return (await response.json()) as T;
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
        await this.handleError(response, undefined, requestId, entityType, entityName);
      } catch (error) {
        clearTimeout(timeoutId);

        if (error instanceof MetadataError) {
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
