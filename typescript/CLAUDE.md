# CLAUDE.md - TypeScript SDK

## Overview

TypeScript SDK for Metadata AI agents. Zero runtime dependencies, uses native fetch.

## Build Commands

```bash
npm install          # Install dependencies
npm run build        # Compile TypeScript
npm test             # Run tests (vitest)
npm run lint         # Run ESLint
```

## Project Structure

```
typescript/
├── src/
│   ├── index.ts      # Public exports
│   ├── client.ts     # AiSdk main client
│   ├── agent.ts      # AgentHandle class
│   ├── models.ts     # TypeScript interfaces
│   ├── errors.ts     # Error classes
│   ├── http.ts       # HTTP client wrapper
│   └── streaming.ts  # SSE parser
├── tests/
│   └── client.test.ts
├── package.json
└── tsconfig.json
```

## Key Design Decisions

- **Node 18+** - Uses native fetch, no axios/node-fetch
- **Zero runtime deps** - Only devDependencies for build/test
- **Async iterators** - Streaming uses `for await...of` pattern
- **Error classes** - Typed errors for each HTTP status code

## API Pattern

```typescript
const client = new AiSdk({ host, token });
const response = await client.agent('name').invoke('message');

// Streaming
for await (const event of client.agent('name').stream('message')) {
  // handle event
}
```

## Adding a New Method

1. Add method to `AgentHandle` class in `agent.ts`
2. Add types to `models.ts`
3. Update `index.ts` exports if needed
4. Add tests

## DO NOT

- Add runtime dependencies without strong justification
- Use CommonJS syntax (ESM only)
- Break the async iterator streaming pattern
