# @openmetadata/ai-sdk

TypeScript SDK for interacting with OpenMetadata Dynamic Agents.

## Installation

```bash
npm install @openmetadata/ai-sdk
```

**Requirements**: Node.js >= 18.0.0 (uses native `fetch`)

## Quick Start

```typescript
import { MetadataAI } from '@openmetadata/ai-sdk';

// Initialize the client
const client = new MetadataAI({
  host: 'https://openmetadata.example.com',
  token: 'your-bot-jwt-token',
});

// Invoke an agent
const response = await client.agent('DataQualityPlannerAgent')
  .invoke('What tables have quality issues?');

console.log(response.response);
console.log('Tools used:', response.toolsUsed);
```

## Usage

### Synchronous Invocation

```typescript
const agent = client.agent('DataQualityPlannerAgent');
const response = await agent.invoke('Analyze the orders table');

console.log(response.response);
console.log(response.conversationId);
console.log(response.toolsUsed);
```

### Streaming Response

```typescript
for await (const event of client.agent('DataQualityPlannerAgent')
  .stream('Analyze data quality')) {
  switch (event.type) {
    case 'start':
      console.log('Started conversation:', event.conversationId);
      break;
    case 'content':
      process.stdout.write(event.content || '');
      break;
    case 'tool_use':
      console.log('\nUsing tool:', event.toolName);
      break;
    case 'end':
      console.log('\nCompleted');
      break;
    case 'error':
      console.error('Error:', event.error);
      break;
  }
}
```

### Multi-Turn Conversations

```typescript
const agent = client.agent('DataQualityPlannerAgent');

// First message
const r1 = await agent.invoke('Analyze the orders table');
console.log(r1.response);

// Follow-up using the same conversation
const r2 = await agent.invoke('Now create tests for the issues you found', {
  conversationId: r1.conversationId,
});
console.log(r2.response);
```

### List Available Agents

```typescript
const agents = await client.listAgents();

for (const agent of agents) {
  console.log(`${agent.displayName}: ${agent.description}`);
  console.log(`  Abilities: ${agent.abilities.join(', ')}`);
}

// With pagination
const moreAgents = await client.listAgents({ limit: 20, offset: 10 });
```

### Get Agent Information

```typescript
const agent = client.agent('DataQualityPlannerAgent');
const info = await agent.getInfo();

console.log('Name:', info.displayName);
console.log('Description:', info.description);
console.log('Abilities:', info.abilities);
console.log('API Enabled:', info.apiEnabled);
```

### Create Agents

```typescript
const newAgent = await client.createAgent({
  name: 'MyCustomAgent',
  description: 'A custom agent for data analysis',
  persona: 'DataAnalyst',
  apiEnabled: true,
  abilities: ['search', 'query'],
});

console.log('Created agent:', newAgent.name);
```

### Bots

```typescript
// List all bots
const bots = await client.listBots();
for (const bot of bots) {
  console.log(`${bot.name}: ${bot.displayName}`);
}

// Get a specific bot
const bot = await client.getBot('my-bot-name');
console.log('Bot:', bot.name);
```

### Personas

```typescript
// List all personas
const personas = await client.listPersonas();
for (const persona of personas) {
  console.log(`${persona.name}: ${persona.description}`);
}

// Get a specific persona
const persona = await client.getPersona('DataAnalyst');

// Create a new persona
const newPersona = await client.createPersona({
  name: 'CustomAnalyst',
  description: 'A specialized data analyst',
  prompt: 'You are an expert data analyst who helps users understand their data...',
});
console.log('Created persona:', newPersona.name);
```

### Abilities

```typescript
// List all abilities
const abilities = await client.listAbilities();
for (const ability of abilities) {
  console.log(`${ability.name}: ${ability.description}`);
}

// Get a specific ability
const ability = await client.getAbility('search');
console.log('Ability:', ability.name);
```

## Configuration Options

```typescript
const client = new MetadataAI({
  // Required
  host: 'https://openmetadata.example.com',  // OpenMetadata server URL
  token: 'your-jwt-token',               // Bot JWT token

  // Optional
  timeout: 120000,    // Request timeout in ms (default: 120000)
  maxRetries: 3,      // Max retry attempts (default: 3)
  retryDelay: 1000,   // Base retry delay in ms (default: 1000)
});
```

## Error Handling

The SDK provides specific error classes for different failure modes:

```typescript
import {
  MetadataAI,
  AuthenticationError,
  AgentNotFoundError,
  AgentNotEnabledError,
  BotNotFoundError,
  PersonaNotFoundError,
  AbilityNotFoundError,
  RateLimitError,
  AgentExecutionError,
  NetworkError,
  TimeoutError,
} from '@openmetadata/ai-sdk';

try {
  const response = await client.agent('MyAgent').invoke('Hello');
} catch (error) {
  if (error instanceof AuthenticationError) {
    console.error('Invalid token - please check your credentials');
  } else if (error instanceof AgentNotFoundError) {
    console.error(`Agent not found: ${error.agentName}`);
  } else if (error instanceof AgentNotEnabledError) {
    console.error(`Agent not API-enabled: ${error.agentName}`);
  } else if (error instanceof BotNotFoundError) {
    console.error(`Bot not found: ${error.botName}`);
  } else if (error instanceof PersonaNotFoundError) {
    console.error(`Persona not found: ${error.personaName}`);
  } else if (error instanceof AbilityNotFoundError) {
    console.error(`Ability not found: ${error.abilityName}`);
  } else if (error instanceof RateLimitError) {
    console.error(`Rate limited - retry after ${error.retryAfter} seconds`);
  } else if (error instanceof TimeoutError) {
    console.error(`Request timed out after ${error.timeoutMs}ms`);
  } else if (error instanceof NetworkError) {
    console.error('Network error:', error.message);
  } else if (error instanceof AgentExecutionError) {
    console.error('Agent execution failed:', error.message);
  }
}
```

## Type Definitions

### InvokeResponse

```typescript
interface InvokeResponse {
  conversationId: string;  // ID for multi-turn conversations
  response: string;        // Agent's response text
  toolsUsed: string[];     // Tools used during execution
  usage?: Usage;           // Token usage statistics
}
```

### StreamEvent

```typescript
interface StreamEvent {
  type: 'start' | 'content' | 'tool_use' | 'end' | 'error';
  content?: string;        // Content for 'content' events
  toolName?: string;       // Tool name for 'tool_use' events
  conversationId?: string; // Available on 'start' and 'end'
  error?: string;          // Error message for 'error' events
}
```

### AgentInfo

```typescript
interface AgentInfo {
  name: string;            // Agent identifier
  displayName: string;     // Human-readable name
  description: string;     // Agent description
  abilities: string[];     // List of capabilities
  apiEnabled: boolean;     // Whether API access is enabled
}
```

### BotInfo

```typescript
interface BotInfo {
  name: string;            // Bot identifier
  displayName: string;     // Human-readable name
  description: string;     // Bot description
}
```

### PersonaInfo

```typescript
interface PersonaInfo {
  name: string;            // Persona identifier
  displayName: string;     // Human-readable name
  description: string;     // Persona description
  prompt: string;          // System prompt
}
```

### AbilityInfo

```typescript
interface AbilityInfo {
  name: string;            // Ability identifier
  displayName: string;     // Human-readable name
  description: string;     // Ability description
}
```

### CreateAgentRequest

```typescript
interface CreateAgentRequest {
  name: string;            // Required: unique identifier
  description: string;     // Required: agent description
  persona: string;         // Required: persona name
  displayName?: string;    // Human-readable name
  apiEnabled?: boolean;    // Enable API access
  abilities?: string[];    // List of ability names
  prompt?: string;         // Default task/prompt
  provider?: string;       // LLM provider
  botName?: string;        // Bot for actions
}
```

### CreatePersonaRequest

```typescript
interface CreatePersonaRequest {
  name: string;            // Required: unique identifier
  description: string;     // Required: persona description
  prompt: string;          // Required: system prompt
  displayName?: string;    // Human-readable name
  provider?: string;       // LLM provider
}
```

## Environment Variables

For convenience, you can use environment variables:

```typescript
const client = new MetadataAI({
  host: process.env.OPENMETADATA_HOST!,
  token: process.env.OPENMETADATA_TOKEN!,
});
```

## License

Apache-2.0
