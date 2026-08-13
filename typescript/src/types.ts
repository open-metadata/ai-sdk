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
  /** List of skills/capabilities the agent has */
  skills?: string[];
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
 * Information about a Skill.
 *
 * Skills define specific capabilities that can be assigned to agents.
 */
export interface SkillInfo {
  /** Unique identifier of the skill */
  id: string;
  /** Name of the skill (used as identifier) */
  name: string;
  /** Human-readable display name */
  displayName?: string;
  /** Description of the skill's purpose */
  description?: string;
  /** Provider of the skill (e.g., "system", "user") */
  provider?: string;
  /** Fully qualified name */
  fullyQualifiedName?: string;
  /** List of tools provided by this skill */
  tools: string[];
}

/**
 * High-level type of a Context Center memory.
 */
export type MemoryType = 'Preference' | 'UseCase' | 'Note' | 'Runbook' | 'Faq';

/**
 * Scope where a memory applies.
 */
export type MemoryScope = 'UserGlobal' | 'EntityScoped';

/**
 * Visibility level for a memory.
 */
export type MemoryVisibility = 'Private' | 'Entity' | 'Shared';

/**
 * Request body for creating a Context Center memory.
 *
 * `visibility` is flattened from the API's `shareConfig.visibility`; it is
 * re-nested when the request is serialized to the wire format.
 *
 * `tags` accepts a list of tag FQN strings; each one is wrapped into the
 * platform's TagLabel shape on the wire.
 */
export interface CreateContextMemoryRequest {
  /** Stable system name for the memory */
  name: string;
  /** Canonical question / instruction (required) */
  question: string;
  /** Canonical answer / retained guidance (required) */
  answer: string;
  /** Short title shown in Context Center */
  title?: string;
  /** Optional markdown description */
  description?: string;
  /** High-level memory type (default: 'Note') */
  memoryType?: MemoryType;
  /** Scope the memory applies to (default: 'EntityScoped') */
  memoryScope?: MemoryScope;
  /** Visibility level (default: 'Private') */
  visibility?: MemoryVisibility;
  /** Primary entity this memory attaches to */
  primaryEntity?: EntityReference;
  /** Additional related entities */
  relatedEntities?: EntityReference[];
  /** Tag FQN strings; wrapped into TagLabel objects on the wire */
  tags?: string[];
}

/**
 * A Context Center memory.
 */
export interface ContextMemory {
  /** Unique identifier */
  id: string;
  /** Stable system name */
  name: string;
  /** Fully qualified name */
  fullyQualifiedName?: string;
  /** Short title */
  title?: string;
  /** Canonical question / instruction */
  question: string;
  /** Canonical answer / retained guidance */
  answer: string;
  /** Optional summary */
  summary?: string;
  /** High-level memory type */
  memoryType: MemoryType;
  /** Scope the memory applies to */
  memoryScope: MemoryScope;
  /** Visibility (extracted from shareConfig.visibility) */
  visibility: MemoryVisibility;
  /** Primary entity this memory attaches to */
  primaryEntity?: EntityReference;
  /** Number of times this memory has been used */
  usageCount: number;
  /** Last-used timestamp in epoch milliseconds */
  lastUsedAt?: number;
  /** Whether the memory is soft-deleted */
  deleted: boolean;
}

/**
 * A single hit from a hybrid memory search.
 */
export interface MemorySearchHit {
  /** The matched memory */
  memory: ContextMemory;
  /** Relevance score from the search engine */
  score: number;
}

/**
 * Results from a hybrid memory search.
 */
export interface MemorySearchResults {
  /** Total number of matching memories */
  total: number;
  /** Ranked search hits */
  hits: MemorySearchHit[];
}
