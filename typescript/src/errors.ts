/**
 * Error classes for the Metadata AI SDK.
 *
 * This module provides a hierarchy of error classes for handling
 * various error conditions from the Metadata AI Agent API.
 */

/**
 * Base error class for all Metadata AI SDK errors.
 */
export class MetadataError extends Error {
  /** HTTP status code associated with the error */
  public readonly statusCode?: number;

  constructor(message: string, statusCode?: number) {
    super(message);
    this.name = 'MetadataError';
    this.statusCode = statusCode;
    // Maintains proper stack trace for where error was thrown (V8 engines)
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, this.constructor);
    }
  }
}

/**
 * Error thrown when authentication fails (401).
 *
 * This typically indicates an invalid or expired JWT token.
 */
export class AuthenticationError extends MetadataError {
  constructor(message = 'Invalid or expired token') {
    super(message, 401);
    this.name = 'AuthenticationError';
  }
}

/**
 * Error thrown when the specified agent is not found (404).
 */
export class AgentNotFoundError extends MetadataError {
  /** The name of the agent that was not found */
  public readonly agentName: string;

  constructor(agentName: string) {
    super(`Agent not found: ${agentName}`, 404);
    this.name = 'AgentNotFoundError';
    this.agentName = agentName;
  }
}

/**
 * Error thrown when the agent exists but is not API-enabled (403).
 *
 * Enable API access for the agent by setting apiEnabled=true in the agent configuration.
 */
export class AgentNotEnabledError extends MetadataError {
  /** The name of the agent that is not enabled */
  public readonly agentName: string;

  constructor(agentName: string) {
    super(
      `Agent '${agentName}' is not enabled for API access. Set apiEnabled=true on the agent to enable SDK access.`,
      403
    );
    this.name = 'AgentNotEnabledError';
    this.agentName = agentName;
  }
}

/**
 * Error thrown when rate limit is exceeded (429).
 */
export class RateLimitError extends MetadataError {
  /** Number of seconds to wait before retrying (from Retry-After header) */
  public readonly retryAfter?: number;

  constructor(message = 'Rate limit exceeded', retryAfter?: number) {
    super(message, 429);
    this.name = 'RateLimitError';
    this.retryAfter = retryAfter;
  }
}

/**
 * Error thrown when agent execution fails (500).
 */
export class AgentExecutionError extends MetadataError {
  /** The name of the agent that failed (if known) */
  public readonly agentName?: string;

  constructor(message: string, agentName?: string) {
    super(message, 500);
    this.name = 'AgentExecutionError';
    this.agentName = agentName;
  }
}

/**
 * Error thrown when a network or connection error occurs.
 */
export class NetworkError extends MetadataError {
  /** The original error that caused the network failure */
  public readonly cause?: Error;

  constructor(message: string, cause?: Error) {
    super(message);
    this.name = 'NetworkError';
    this.cause = cause;
  }
}

/**
 * Error thrown when a request times out.
 */
export class TimeoutError extends MetadataError {
  /** The timeout duration in milliseconds */
  public readonly timeoutMs: number;

  constructor(timeoutMs: number) {
    super(`Request timed out after ${timeoutMs}ms`);
    this.name = 'TimeoutError';
    this.timeoutMs = timeoutMs;
  }
}

/**
 * Error thrown when the specified bot is not found (404).
 */
export class BotNotFoundError extends MetadataError {
  /** The name of the bot that was not found */
  public readonly botName: string;

  constructor(botName: string) {
    super(`Bot not found: ${botName}`, 404);
    this.name = 'BotNotFoundError';
    this.botName = botName;
  }
}

/**
 * Error thrown when the specified persona is not found (404).
 */
export class PersonaNotFoundError extends MetadataError {
  /** The name of the persona that was not found */
  public readonly personaName: string;

  constructor(personaName: string) {
    super(`Persona not found: ${personaName}`, 404);
    this.name = 'PersonaNotFoundError';
    this.personaName = personaName;
  }
}

/**
 * Error thrown when the specified ability is not found (404).
 */
export class AbilityNotFoundError extends MetadataError {
  /** The name of the ability that was not found */
  public readonly abilityName: string;

  constructor(abilityName: string) {
    super(`Ability not found: ${abilityName}`, 404);
    this.name = 'AbilityNotFoundError';
    this.abilityName = abilityName;
  }
}
