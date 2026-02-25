/**
 * Extended type definitions for the Metadata AI SDK.
 *
 * These interfaces define the structures for bots, personas,
 * agents, and related entities in the OpenMetadata platform.
 */

/**
 * A reference to another entity in the OpenMetadata platform.
 */
export interface EntityReference {
  /** Unique identifier of the entity */
  id: string;
  /** Type of the entity (e.g., "user", "team", "service") */
  type: string;
  /** Name of the entity */
  name?: string;
  /** Human-readable display name */
  displayName?: string;
}

/**
 * Information about a bot entity.
 *
 * Bots are service accounts that can execute agents and
 * perform automated actions in the OpenMetadata platform.
 */
export interface BotInfo {
  /** Unique identifier of the bot */
  id: string;
  /** Name of the bot (used as identifier) */
  name: string;
  /** Human-readable display name */
  displayName?: string;
  /** Description of the bot's purpose */
  description?: string;
  /** Reference to the user entity associated with this bot */
  botUser?: EntityReference;
}

/**
 * Information about an AI Persona.
 *
 * Personas define the behavior and personality of AI agents
 * through system prompts and configuration.
 */
export interface PersonaInfo {
  /** Unique identifier of the persona */
  id: string;
  /** Name of the persona (used as identifier) */
  name: string;
  /** Human-readable display name */
  displayName?: string;
  /** Description of the persona's purpose */
  description?: string;
  /** System prompt that defines the persona's behavior */
  prompt?: string;
  /** Provider of the persona (e.g., "system", "user") */
  provider: string;
}

/**
 * Defines the scope of knowledge and data access for an agent.
 *
 * This determines what entities and services the agent can
 * access when answering questions or performing actions.
 */
export interface KnowledgeScope {
  /** Types of entities the agent can access (e.g., ["table", "dashboard"]) */
  entityTypes?: string[];
  /** Specific services the agent has access to */
  services?: EntityReference[];
}

/**
 * Request body for creating a new persona.
 */
export interface CreatePersonaRequest {
  /** Name of the persona (used as identifier) */
  name: string;
  /** Description of the persona's purpose */
  description: string;
  /** System prompt that defines the persona's behavior */
  prompt: string;
  /** Human-readable display name */
  displayName?: string;
  /** Provider of the persona (default: "user") */
  provider?: string;
  /** Owners of the persona */
  owners?: EntityReference[];
}

/**
 * Request body for creating a new dynamic agent.
 */
export interface CreateAgentRequest {
  /** Name of the agent (used as identifier) */
  name: string;
  /** Description of the agent's purpose */
  description: string;
  /** Name of the persona that defines the agent's behavior (required) */
  persona: string;
  /** Operating mode of the agent (required) */
  mode: 'chat' | 'agent' | 'both';
  /** Human-readable display name */
  displayName?: string;
  /** Icon identifier or URL for the agent */
  icon?: string;
  /** Name of the bot that executes this agent */
  botName?: string;
  /** List of abilities/capabilities the agent has */
  abilities?: string[];
  /** Scope of data and entities the agent can access */
  knowledge?: KnowledgeScope;
  /** Workflow definition prompt */
  prompt?: string;
  /** Cron expression for scheduled execution */
  schedule?: string;
  /** Whether the agent can be invoked via API (default: false) */
  apiEnabled?: boolean;
  /** Provider of the agent (default: "user") */
  provider?: string;
}

/**
 * Information about an Ability.
 *
 * Abilities define specific capabilities that can be assigned to agents.
 */
export interface AbilityInfo {
  /** Unique identifier of the ability */
  id: string;
  /** Name of the ability (used as identifier) */
  name: string;
  /** Human-readable display name */
  displayName?: string;
  /** Description of the ability's purpose */
  description?: string;
  /** Provider of the ability (e.g., "system", "user") */
  provider?: string;
  /** Fully qualified name */
  fullyQualifiedName?: string;
  /** List of tools provided by this ability */
  tools: string[];
}
