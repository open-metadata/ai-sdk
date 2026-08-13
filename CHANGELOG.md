# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `client.memories` namespace with `list`, `get`, `create`, `delete`, and
  `search` (hybrid NLQ search over the `contextMemory` index) for Context
  Center memories. All methods support sync and async in Python and async in
  TypeScript; sync-only in Java; subcommands in the Rust CLI.
- Memory model types across all SDKs: `ContextMemory`,
  `CreateContextMemoryRequest`, `MemorySearchHit`, `MemorySearchResults`,
  `MemoryType`, `MemoryScope`, `MemoryVisibility`.
- `CHANGELOG.md` for release notes.

### Changed (BREAKING)

**Ability is now Skill.** Collate renamed the entity server-side, so every SDK
follows. There is no backwards-compatible alias — the old endpoints no longer
exist.

| Old                                    | New                                 |
| -------------------------------------- | ----------------------------------- |
| `GET /api/v1/agents/abilities`          | `GET /api/v1/agents/skills`         |
| `GET /api/v1/agents/abilities/name/{n}` | `GET /api/v1/agents/skills/name/{n}` |
| `client.abilities`                      | `client.skills`                     |
| `AbilityInfo`                           | `SkillInfo`                         |
| `AbilityNotFoundError` / `...Exception` | `SkillNotFoundError` / `...Exception` |
| `CreateAgentRequest.abilities`          | `CreateAgentRequest.skills`         |
| `AgentInfo.abilities`                   | `AgentInfo.skills`                  |
| `ai-sdk abilities list/get`             | `ai-sdk skills list/get`            |

The agent payload field is `skills`, the entity reference `type` is `"skill"`,
and the agent detail query is `?fields=persona,bot,skills`.

All client CRUD methods now live on namespaces. The `client.agent(name)`
handle factory and `client.mcp` namespace are unchanged.

**Python migration:**

| Old (removed)                | New                            |
| ---------------------------- | ------------------------------ |
| `client.list_agents()`       | `client.agents.list()`         |
| `client.create_agent(req)`   | `client.agents.create(req)`    |
| `client.list_bots()`         | `client.bots.list()`           |
| `client.get_bot(name)`       | `client.bots.get(name)`        |
| `client.list_personas()`     | `client.personas.list()`       |
| `client.get_persona(name)`   | `client.personas.get(name)`    |
| `client.create_persona(req)` | `client.personas.create(req)`  |
| `client.list_abilities()`    | `client.skills.list()`         |
| `client.get_ability(name)`   | `client.skills.get(name)`      |

All `aXxx` async variants follow the same pattern: `client.X.aYyy()`.

**TypeScript migration:**

Same shape as Python with camelCase methods and accessed as fields
(`client.agents.list()`, `client.bots.get(name)`, etc.).

**Java migration:**

Namespaces are exposed as methods rather than fields:
`client.agents().list()`, `client.bots().get(name)`,
`client.memories().search(query)`, etc.

**Rust CLI:**

The CLI was already namespace-shaped via subcommands. New `memories`
subcommand added: `ai-sdk memories list`, `ai-sdk memories search "..."`,
etc.
