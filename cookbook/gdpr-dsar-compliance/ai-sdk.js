// typescript/src/streaming.ts
function mapEventType(eventType) {
  if (!eventType) {
    return "content";
  }
  const typeMapping = {
    "stream-start": "start",
    message: "content",
    "tool-use": "tool_use",
    "stream-completed": "end",
    error: "error",
    "fatal-error": "error"
  };
  return typeMapping[eventType] || eventType;
}
function parseEvent(eventStr) {
  let eventType = null;
  let data = null;
  for (const line of eventStr.split("\n")) {
    const trimmed = line.trim();
    if (trimmed.startsWith("event:")) {
      eventType = trimmed.slice(6).trim();
    } else if (trimmed.startsWith("data:")) {
      data = trimmed.slice(5).trim();
    }
  }
  if (!data) {
    return null;
  }
  let payload;
  try {
    payload = JSON.parse(data);
  } catch {
    payload = { content: data };
  }
  const mappedType = mapEventType(eventType);
  let content;
  let toolName;
  let conversationId = payload.conversationId;
  const dataField = payload.data;
  if (dataField?.message) {
    const message = dataField.message;
    if (!conversationId) {
      conversationId = message.conversationId;
    }
    const contentBlocks = message.content;
    if (contentBlocks && Array.isArray(contentBlocks)) {
      const textParts = [];
      for (const block of contentBlocks) {
        const textMessage = block.textMessage;
        if (textMessage) {
          if (typeof textMessage === "object" && textMessage.message) {
            textParts.push(textMessage.message);
          } else if (typeof textMessage === "string") {
            textParts.push(textMessage);
          }
        }
        const tools = block.tools;
        if (tools && Array.isArray(tools)) {
          for (const tool of tools) {
            if (tool.name) {
              toolName = tool.name;
            }
          }
        }
      }
      if (textParts.length > 0) {
        content = textParts.join("");
      }
    }
  } else if (payload.content) {
    content = payload.content;
  }
  return {
    type: mappedType,
    content,
    toolName,
    conversationId,
    error: mappedType === "error" ? payload.error || payload.message : void 0
  };
}
async function* parseSSEStream(stream) {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        if (buffer.trim()) {
          const event = parseEvent(buffer);
          if (event) {
            yield event;
          }
        }
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buffer.indexOf("\n\n")) !== -1) {
        const eventStr = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        const event = parseEvent(eventStr);
        if (event) {
          yield event;
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
function createStreamIterable(stream) {
  return {
    [Symbol.asyncIterator]() {
      return parseSSEStream(stream);
    }
  };
}

// typescript/src/agent.ts
function mapAgentInfo(data) {
  return {
    name: data.name,
    displayName: data.displayName || data.name,
    description: data.description || "",
    abilities: data.abilities || [],
    apiEnabled: data.apiEnabled ?? false
  };
}
function mapInvokeResponse(data) {
  return {
    conversationId: data.conversationId,
    response: data.response,
    toolsUsed: data.toolsUsed || [],
    usage: data.usage ? {
      promptTokens: data.usage.promptTokens || 0,
      completionTokens: data.usage.completionTokens || 0,
      totalTokens: data.usage.totalTokens || 0
    } : void 0
  };
}
var AgentHandle = class {
  agentName;
  http;
  /**
   * Create a new agent handle.
   *
   * @param name - The agent name
   * @param http - HTTP client for API communication
   * @internal This constructor is called by AiSdk.agent()
   */
  constructor(name, http) {
    this.agentName = name;
    this.http = http;
  }
  /**
   * Get the agent name.
   */
  get name() {
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
  async invoke(message, options) {
    const requestBody = {};
    if (message !== void 0) {
      requestBody.message = message;
    }
    if (options?.conversationId) {
      requestBody.conversationId = options.conversationId;
    }
    if (options?.parameters && Object.keys(options.parameters).length > 0) {
      requestBody.parameters = options.parameters;
    }
    const data = await this.http.post(
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
  async *stream(message, options) {
    const requestBody = {};
    if (message !== void 0) {
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
  async getInfo() {
    const data = await this.http.get(
      `/name/${this.agentName}`,
      void 0,
      this.agentName
    );
    return mapAgentInfo(data);
  }
  /**
   * String representation of the agent handle.
   */
  toString() {
    return `AgentHandle(name="${this.agentName}")`;
  }
};

// typescript/src/errors.ts
var AiSdkError = class extends Error {
  /** HTTP status code associated with the error */
  statusCode;
  constructor(message, statusCode) {
    super(message);
    this.name = "AiSdkError";
    this.statusCode = statusCode;
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, this.constructor);
    }
  }
};
var AuthenticationError = class extends AiSdkError {
  constructor(message = "Invalid or expired token") {
    super(message, 401);
    this.name = "AuthenticationError";
  }
};
var AgentNotFoundError = class extends AiSdkError {
  /** The name of the agent that was not found */
  agentName;
  constructor(agentName) {
    super(`Agent not found: ${agentName}`, 404);
    this.name = "AgentNotFoundError";
    this.agentName = agentName;
  }
};
var AgentNotEnabledError = class extends AiSdkError {
  /** The name of the agent that is not enabled */
  agentName;
  constructor(agentName) {
    super(
      `Agent '${agentName}' is not enabled for API access. Set apiEnabled=true on the agent to enable SDK access.`,
      403
    );
    this.name = "AgentNotEnabledError";
    this.agentName = agentName;
  }
};
var RateLimitError = class extends AiSdkError {
  /** Number of seconds to wait before retrying (from Retry-After header) */
  retryAfter;
  constructor(message = "Rate limit exceeded", retryAfter) {
    super(message, 429);
    this.name = "RateLimitError";
    this.retryAfter = retryAfter;
  }
};
var AgentExecutionError = class extends AiSdkError {
  /** The name of the agent that failed (if known) */
  agentName;
  constructor(message, agentName) {
    super(message, 500);
    this.name = "AgentExecutionError";
    this.agentName = agentName;
  }
};
var NetworkError = class extends AiSdkError {
  /** The original error that caused the network failure */
  cause;
  constructor(message, cause) {
    super(message);
    this.name = "NetworkError";
    this.cause = cause;
  }
};
var TimeoutError = class extends AiSdkError {
  /** The timeout duration in milliseconds */
  timeoutMs;
  constructor(timeoutMs) {
    super(`Request timed out after ${timeoutMs}ms`);
    this.name = "TimeoutError";
    this.timeoutMs = timeoutMs;
  }
};
var BotNotFoundError = class extends AiSdkError {
  /** The name of the bot that was not found */
  botName;
  constructor(botName) {
    super(`Bot not found: ${botName}`, 404);
    this.name = "BotNotFoundError";
    this.botName = botName;
  }
};
var PersonaNotFoundError = class extends AiSdkError {
  /** The name of the persona that was not found */
  personaName;
  constructor(personaName) {
    super(`Persona not found: ${personaName}`, 404);
    this.name = "PersonaNotFoundError";
    this.personaName = personaName;
  }
};
var AbilityNotFoundError = class extends AiSdkError {
  /** The name of the ability that was not found */
  abilityName;
  constructor(abilityName) {
    super(`Ability not found: ${abilityName}`, 404);
    this.name = "AbilityNotFoundError";
    this.abilityName = abilityName;
  }
};

// typescript/src/http.ts
var RETRYABLE_STATUS_CODES = /* @__PURE__ */ new Set([429, 500, 502, 503, 504]);
function generateRequestId() {
  return Math.random().toString(36).substring(2, 10);
}
var HttpClient = class {
  baseUrl;
  /** The root host URL (without API path) */
  hostUrl;
  token;
  timeout;
  maxRetries;
  retryDelay;
  userAgent = "ai-sdk-ts/0.1.0";
  constructor(options) {
    this.baseUrl = options.baseUrl.replace(/\/$/, "");
    this.hostUrl = this.baseUrl.replace(/\/api\/v1\/agents\/dynamic$/, "");
    this.token = options.token;
    this.timeout = options.timeout;
    this.maxRetries = options.maxRetries;
    this.retryDelay = options.retryDelay;
  }
  /**
   * Build request headers.
   */
  getHeaders(requestId, stream = false) {
    return {
      Authorization: `Bearer ${this.token}`,
      "Content-Type": "application/json",
      Accept: stream ? "text/event-stream" : "application/json",
      "User-Agent": this.userAgent,
      "X-Request-ID": requestId
    };
  }
  /**
   * Build full URL with query parameters.
   */
  buildUrl(path, params) {
    const fullPath = path.startsWith("/") ? path : `/${path}`;
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
  shouldRetry(status, attempt) {
    if (attempt >= this.maxRetries) {
      return false;
    }
    return RETRYABLE_STATUS_CODES.has(status);
  }
  /**
   * Calculate retry delay with exponential backoff.
   */
  getRetryDelay(attempt, retryAfterHeader) {
    if (retryAfterHeader) {
      const parsed = parseInt(retryAfterHeader, 10);
      if (!isNaN(parsed)) {
        return parsed * 1e3;
      }
    }
    return this.retryDelay * Math.pow(2, attempt);
  }
  /**
   * Wait for the specified delay.
   */
  async wait(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
  /**
   * Handle error responses and throw appropriate exceptions.
   */
  async handleError(response, agentName, _requestId, entityType, entityName) {
    const status = response.status;
    if (status === 401) {
      throw new AuthenticationError();
    }
    if (status === 403) {
      if (agentName) {
        throw new AgentNotEnabledError(agentName);
      }
      throw new AiSdkError("Access forbidden", 403);
    }
    if (status === 404) {
      if (entityType === "bot" && entityName) {
        throw new BotNotFoundError(entityName);
      }
      if (entityType === "persona" && entityName) {
        throw new PersonaNotFoundError(entityName);
      }
      if (entityType === "ability" && entityName) {
        throw new AbilityNotFoundError(entityName);
      }
      if (agentName) {
        throw new AgentNotFoundError(agentName);
      }
      throw new AiSdkError("Resource not found", 404);
    }
    if (status === 429) {
      const retryAfter = response.headers.get("Retry-After");
      const retrySeconds = retryAfter ? parseInt(retryAfter, 10) : void 0;
      throw new RateLimitError("Rate limit exceeded", retrySeconds);
    }
    let message;
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      try {
        const errorData = await response.json();
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
  async get(path, params, agentName) {
    return this.request({
      method: "GET",
      path,
      params,
      agentName
    });
  }
  /**
   * Make a POST request with retry support.
   */
  async post(path, body, agentName) {
    return this.request({
      method: "POST",
      path,
      body,
      agentName
    });
  }
  /**
   * Make a GET request to a custom API path (relative to host URL).
   * This allows accessing endpoints outside the default /api/v1/agents/dynamic base.
   */
  async getAbsolute(apiPath, params, entityType, entityName) {
    return this.requestAbsolute({
      method: "GET",
      path: apiPath,
      params,
      entityType,
      entityName
    });
  }
  /**
   * Make a POST request to a custom API path (relative to host URL).
   * This allows accessing endpoints outside the default /api/v1/agents/dynamic base.
   */
  async postAbsolute(apiPath, body, entityType, entityName) {
    return this.requestAbsolute({
      method: "POST",
      path: apiPath,
      body,
      entityType,
      entityName
    });
  }
  /**
   * Make a streaming POST request.
   *
   * Note: Streaming requests don't support automatic retry.
   */
  async postStream(path, body, agentName) {
    const requestId = generateRequestId();
    const url = this.buildUrl(path);
    const headers = this.getHeaders(requestId, true);
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);
    try {
      const response = await fetch(url, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      if (!response.ok) {
        await this.handleError(response, agentName, requestId);
      }
      if (!response.body) {
        throw new AiSdkError("No response body for streaming request");
      }
      return response.body;
    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof AiSdkError) {
        throw error;
      }
      if (error instanceof Error) {
        if (error.name === "AbortError") {
          throw new TimeoutError(this.timeout);
        }
        throw new NetworkError(`Network error: ${error.message}`, error);
      }
      throw new NetworkError("Unknown network error");
    }
  }
  /**
   * Internal request method with retry logic.
   */
  async request(options) {
    const { method, path, body, params, agentName } = options;
    const requestId = generateRequestId();
    const url = this.buildUrl(path, params);
    const headers = this.getHeaders(requestId);
    let lastError = null;
    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);
      try {
        const response = await fetch(url, {
          method,
          headers,
          body: body ? JSON.stringify(body) : void 0,
          signal: controller.signal
        });
        clearTimeout(timeoutId);
        if (response.ok) {
          return await response.json();
        }
        if (this.shouldRetry(response.status, attempt)) {
          const delay = this.getRetryDelay(
            attempt,
            response.headers.get("Retry-After")
          );
          await this.wait(delay);
          continue;
        }
        await this.handleError(response, agentName, requestId);
      } catch (error) {
        clearTimeout(timeoutId);
        if (error instanceof AiSdkError) {
          throw error;
        }
        if (error instanceof Error) {
          if (error.name === "AbortError") {
            lastError = new TimeoutError(this.timeout);
            if (attempt < this.maxRetries) {
              const delay = this.retryDelay * Math.pow(2, attempt);
              await this.wait(delay);
              continue;
            }
            throw lastError;
          }
          lastError = new NetworkError(`Network error: ${error.message}`, error);
          if (attempt < this.maxRetries) {
            const delay = this.retryDelay * Math.pow(2, attempt);
            await this.wait(delay);
            continue;
          }
          throw lastError;
        }
        throw new NetworkError("Unknown network error");
      }
    }
    throw lastError || new NetworkError("Request failed after retries");
  }
  /**
   * Build URL with custom API path (relative to host URL).
   */
  buildAbsoluteUrl(apiPath, params) {
    const fullPath = apiPath.startsWith("/") ? apiPath : `/${apiPath}`;
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
  async requestAbsolute(options) {
    const { method, path, body, params, entityType, entityName } = options;
    const requestId = generateRequestId();
    const url = this.buildAbsoluteUrl(path, params);
    const headers = this.getHeaders(requestId);
    let lastError = null;
    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);
      try {
        const response = await fetch(url, {
          method,
          headers,
          body: body ? JSON.stringify(body) : void 0,
          signal: controller.signal
        });
        clearTimeout(timeoutId);
        if (response.ok) {
          return await response.json();
        }
        if (this.shouldRetry(response.status, attempt)) {
          const delay = this.getRetryDelay(
            attempt,
            response.headers.get("Retry-After")
          );
          await this.wait(delay);
          continue;
        }
        await this.handleError(response, void 0, requestId, entityType, entityName);
      } catch (error) {
        clearTimeout(timeoutId);
        if (error instanceof AiSdkError) {
          throw error;
        }
        if (error instanceof Error) {
          if (error.name === "AbortError") {
            lastError = new TimeoutError(this.timeout);
            if (attempt < this.maxRetries) {
              const delay = this.retryDelay * Math.pow(2, attempt);
              await this.wait(delay);
              continue;
            }
            throw lastError;
          }
          lastError = new NetworkError(`Network error: ${error.message}`, error);
          if (attempt < this.maxRetries) {
            const delay = this.retryDelay * Math.pow(2, attempt);
            await this.wait(delay);
            continue;
          }
          throw lastError;
        }
        throw new NetworkError("Unknown network error");
      }
    }
    throw lastError || new NetworkError("Request failed after retries");
  }
};

// typescript/src/client.ts
var DEFAULT_TIMEOUT = 12e4;
var DEFAULT_MAX_RETRIES = 3;
var DEFAULT_RETRY_DELAY = 1e3;
function mapAgentInfo2(data) {
  return {
    name: data.name,
    displayName: data.displayName || data.name,
    description: data.description || "",
    abilities: data.abilities || [],
    apiEnabled: data.apiEnabled ?? false
  };
}
function mapBotInfo(data) {
  return {
    id: data.id,
    name: data.name,
    displayName: data.displayName,
    description: data.description,
    botUser: data.botUser
  };
}
function mapPersonaInfo(data) {
  return {
    id: data.id,
    name: data.name,
    displayName: data.displayName,
    description: data.description,
    prompt: data.prompt,
    provider: data.provider
  };
}
function mapAbilityInfo(data) {
  return {
    id: data.id,
    name: data.name,
    displayName: data.displayName,
    description: data.description,
    provider: data.provider,
    fullyQualifiedName: data.fullyQualifiedName,
    tools: data.tools || []
  };
}
var AiSdk = class {
  hostUrl;
  http;
  /**
   * Create a new AiSdk client.
   *
   * @param options - Client configuration options
   *
   * @throws {Error} If host or token is empty
   *
   * @example
   * ```typescript
   * // Basic initialization
   * const client = new AiSdk({
   *   host: 'https://openmetadata.example.com',
   *   token: 'your-jwt-token',
   * });
   *
   * // With custom options
   * const client = new AiSdk({
   *   host: 'https://openmetadata.example.com',
   *   token: 'your-jwt-token',
   *   timeout: 60000,      // 60 seconds
   *   maxRetries: 5,       // More retries
   *   retryDelay: 2000,    // Start with 2 second delay
   * });
   * ```
   */
  constructor(options) {
    if (!options.host) {
      throw new Error("Host is required");
    }
    if (!options.token) {
      throw new Error("Token is required");
    }
    this.hostUrl = options.host.replace(/\/$/, "");
    this.http = new HttpClient({
      baseUrl: `${this.hostUrl}/api/v1/agents/dynamic`,
      token: options.token,
      timeout: options.timeout ?? DEFAULT_TIMEOUT,
      maxRetries: options.maxRetries ?? DEFAULT_MAX_RETRIES,
      retryDelay: options.retryDelay ?? DEFAULT_RETRY_DELAY
    });
  }
  /**
   * Get the configured host URL.
   */
  get host() {
    return this.hostUrl;
  }
  /**
   * Paginate through all results from a list endpoint.
   * @internal
   */
  async paginateList(fetcher, mapper, limit, pageSize = 100) {
    const results = [];
    let after = void 0;
    while (true) {
      const params = { limit: pageSize };
      if (after) {
        params.after = after;
      }
      const response = await fetcher(params);
      const data = response.data || [];
      results.push(...data.map(mapper));
      if (limit !== void 0 && results.length >= limit) {
        return results.slice(0, limit);
      }
      after = response.paging?.after;
      if (!after) {
        break;
      }
    }
    return results;
  }
  /**
   * Get a handle to a specific agent.
   *
   * @param name - The agent name (e.g., "DataQualityPlannerAgent")
   * @returns AgentHandle for invoking the agent
   *
   * @example
   * ```typescript
   * const agent = client.agent('DataQualityPlannerAgent');
   *
   * // Invoke the agent
   * const response = await agent.invoke('What tests should I add?');
   * ```
   */
  agent(name) {
    return new AgentHandle(name, this.http);
  }
  /**
   * List all API-enabled agents.
   *
   * Automatically paginates through all results.
   *
   * @param options - Options
   * @param options.limit - Maximum number of agents to return. If not specified, returns all agents.
   * @returns Promise resolving to list of AgentInfo objects
   *
   * @example
   * ```typescript
   * // List all agents
   * const agents = await client.listAgents();
   *
   * // List with limit
   * const agents = await client.listAgents({ limit: 20 });
   *
   * // Display agent information
   * for (const agent of agents) {
   *   console.log(`${agent.name}: ${agent.description}`);
   *   console.log(`  Abilities: ${agent.abilities.join(', ')}`);
   * }
   * ```
   */
  async listAgents(options) {
    return this.paginateList(
      (params) => this.http.get("/", { ...params, apiEnabled: "true" }),
      mapAgentInfo2,
      options?.limit
    );
  }
  /**
   * List all bots in the system.
   *
   * Automatically paginates through all results.
   *
   * @param options - Options
   * @param options.limit - Maximum number of bots to return. If not specified, returns all bots.
   * @returns Promise resolving to list of BotInfo objects
   *
   * @example
   * ```typescript
   * // List all bots
   * const bots = await client.listBots();
   * for (const bot of bots) {
   *   console.log(`${bot.name}: ${bot.description}`);
   * }
   *
   * // List with limit
   * const bots = await client.listBots({ limit: 5 });
   * ```
   */
  async listBots(options) {
    return this.paginateList(
      (params) => this.http.getAbsolute("/api/v1/bots", params),
      mapBotInfo,
      options?.limit
    );
  }
  /**
   * Get a bot by name.
   *
   * @param name - The bot name
   * @returns Promise resolving to BotInfo
   * @throws {BotNotFoundError} If the bot is not found
   *
   * @example
   * ```typescript
   * const bot = await client.getBot('ingestion-bot');
   * console.log(`Bot: ${bot.displayName}`);
   * console.log(`User: ${bot.botUser?.name}`);
   * ```
   */
  async getBot(name) {
    const response = await this.http.getAbsolute(
      `/api/v1/bots/name/${encodeURIComponent(name)}`,
      void 0,
      "bot",
      name
    );
    return mapBotInfo(response);
  }
  /**
   * List all personas in the system.
   *
   * Automatically paginates through all results.
   *
   * @param options - Options
   * @param options.limit - Maximum number of personas to return. If not specified, returns all personas.
   * @returns Promise resolving to list of PersonaInfo objects
   *
   * @example
   * ```typescript
   * // List all personas
   * const personas = await client.listPersonas();
   * for (const persona of personas) {
   *   console.log(`${persona.name}: ${persona.description}`);
   * }
   *
   * // List with limit
   * const personas = await client.listPersonas({ limit: 5 });
   * ```
   */
  async listPersonas(options) {
    return this.paginateList(
      (params) => this.http.getAbsolute("/api/v1/agents/personas", params),
      mapPersonaInfo,
      options?.limit
    );
  }
  /**
   * Get a persona by name.
   *
   * @param name - The persona name
   * @returns Promise resolving to PersonaInfo
   * @throws {PersonaNotFoundError} If the persona is not found
   *
   * @example
   * ```typescript
   * const persona = await client.getPersona('data-analyst');
   * console.log(`Persona: ${persona.displayName}`);
   * console.log(`Prompt: ${persona.prompt}`);
   * ```
   */
  async getPersona(name) {
    const response = await this.http.getAbsolute(
      `/api/v1/agents/personas/name/${encodeURIComponent(name)}`,
      void 0,
      "persona",
      name
    );
    return mapPersonaInfo(response);
  }
  /**
   * Create a new persona.
   *
   * @param request - The persona creation request
   * @returns Promise resolving to the created PersonaInfo
   *
   * @example
   * ```typescript
   * const persona = await client.createPersona({
   *   name: 'custom-analyst',
   *   description: 'A custom data analyst persona',
   *   prompt: 'You are a helpful data analyst...',
   *   displayName: 'Custom Analyst',
   * });
   * console.log(`Created persona: ${persona.id}`);
   * ```
   */
  async createPersona(request) {
    const body = {
      name: request.name,
      description: request.description,
      prompt: request.prompt,
      displayName: request.displayName,
      provider: request.provider ?? "user",
      owners: request.owners
    };
    const response = await this.http.postAbsolute(
      "/api/v1/agents/personas",
      body
    );
    return mapPersonaInfo(response);
  }
  /**
   * Create a new dynamic agent.
   *
   * @param request - The agent creation request
   * @returns Promise resolving to the created AgentInfo
   *
   * @example
   * ```typescript
   * const agent = await client.createAgent({
   *   name: 'my-custom-agent',
   *   description: 'A custom agent for data analysis',
   *   persona: 'data-analyst',
   *   mode: 'chat',
   *   displayName: 'My Custom Agent',
   *   abilities: ['analyze', 'report'],
   *   apiEnabled: true,
   * });
   * console.log(`Created agent: ${agent.name}`);
   *
   * // Invoke the new agent
   * const response = await client.agent(agent.name).invoke('Hello!');
   * ```
   */
  async createAgent(request) {
    const personaInfo = await this.getPersona(request.persona);
    let abilityRefs;
    if (request.abilities && request.abilities.length > 0) {
      abilityRefs = [];
      for (const abilityName of request.abilities) {
        const abilityInfo = await this.getAbility(abilityName);
        abilityRefs.push({ id: abilityInfo.id, type: "ability" });
      }
    }
    const body = {
      name: request.name,
      description: request.description,
      persona: { id: personaInfo.id, type: "persona" },
      mode: request.mode,
      displayName: request.displayName,
      icon: request.icon,
      botName: request.botName,
      abilities: abilityRefs,
      knowledge: request.knowledge,
      prompt: request.prompt,
      schedule: request.schedule,
      apiEnabled: request.apiEnabled ?? false,
      provider: request.provider ?? "user"
    };
    const response = await this.http.postAbsolute(
      "/api/v1/agents/dynamic",
      body
    );
    return mapAgentInfo2(response);
  }
  /**
   * List all abilities in the system.
   *
   * Automatically paginates through all results.
   *
   * @param options - Options
   * @param options.limit - Maximum number of abilities to return. If not specified, returns all abilities.
   * @returns Promise resolving to list of AbilityInfo objects
   *
   * @example
   * ```typescript
   * // List all abilities
   * const abilities = await client.listAbilities();
   * for (const ability of abilities) {
   *   console.log(`${ability.name}: ${ability.description}`);
   *   console.log(`  Tools: ${ability.tools.join(', ')}`);
   * }
   *
   * // List with limit
   * const abilities = await client.listAbilities({ limit: 5 });
   * ```
   */
  async listAbilities(options) {
    return this.paginateList(
      (params) => this.http.getAbsolute(
        "/api/v1/agents/abilities",
        params
      ),
      mapAbilityInfo,
      options?.limit
    );
  }
  /**
   * Get an ability by name.
   *
   * @param name - The ability name
   * @returns Promise resolving to AbilityInfo
   * @throws {AbilityNotFoundError} If the ability is not found
   *
   * @example
   * ```typescript
   * const ability = await client.getAbility('analyze-data');
   * console.log(`Ability: ${ability.displayName}`);
   * console.log(`Tools: ${ability.tools.join(', ')}`);
   * ```
   */
  async getAbility(name) {
    const response = await this.http.getAbsolute(
      `/api/v1/agents/abilities/name/${encodeURIComponent(name)}`,
      void 0,
      "ability",
      name
    );
    return mapAbilityInfo(response);
  }
  /**
   * String representation of the client.
   */
  toString() {
    return `AiSdk(host="${this.hostUrl}")`;
  }
};
export {
  AbilityNotFoundError,
  AgentExecutionError,
  AgentHandle,
  AgentNotEnabledError,
  AgentNotFoundError,
  AuthenticationError,
  BotNotFoundError,
  AiSdk,
  AiSdkError,
  NetworkError,
  PersonaNotFoundError,
  RateLimitError,
  TimeoutError,
  createStreamIterable,
  parseSSEStream
};
