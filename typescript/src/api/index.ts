/**
 * API namespace classes for the AI SDK.
 *
 * Each module exposes a small class holding the HttpClient(s) it needs and
 * verb methods (list/get/create/delete/etc.). The top-level AISdk wires
 * these together and exposes them as readonly fields.
 */

export { AbilitiesApi, type AbilitiesListOptions } from './abilities.js';
export { AgentsApi, type AgentsListOptions } from './agents.js';
export { BotsApi, type BotsListOptions } from './bots.js';
export {
  MemoriesApi,
  type MemoriesListOptions,
  type MemoriesSearchOptions,
} from './memories.js';
export { PersonasApi, type PersonasListOptions } from './personas.js';
