# n8n-nodes-metadata

Community node package for [n8n](https://n8n.io/), enabling workflow automation with OpenMetadata DynamicAgents.

**Uses the TypeScript SDK** (`@openmetadata/ai-sdk`) for all API communication.

## Directory Structure

```
n8n-nodes-metadata/
├── credentials/
│   └── MetadataApi.credentials.ts    # OAuth/JWT credential configuration
├── nodes/
│   └── MetadataAgent/
│       ├── MetadataAgent.node.ts     # Main node implementation
│       ├── metadata.png              # Node icon (PNG format)
│       └── metadata.svg              # Node icon (SVG format, legacy)
├── index.ts                         # Package exports
├── Makefile                         # Development commands
├── package.json                     # npm package configuration
├── tsconfig.json                    # TypeScript configuration
└── logo.png                         # Source logo file
```

## Development Commands

Use the Makefile for common tasks:

```bash
make help        # Show all available commands
make setup       # Full setup: install, build, and link to n8n
make run         # Start n8n with the linked node
make rebuild     # Clean and rebuild the node
make dev         # Watch mode for development
```

Or use npm directly:

```bash
npm install              # Install dependencies
npm run build            # Compile TypeScript and copy icons to dist/
npm run dev              # Watch mode for development
npm run lint             # Run ESLint
npm run lint:fix         # Auto-fix ESLint issues
```

## How It Works

### Node: MetadataAgent

The `MetadataAgent` node allows n8n workflows to invoke OpenMetadata DynamicAgents via the API.

**Inputs:**
- `agentName` (required): Name of the DynamicAgent to invoke
- `message` (required): The message/query to send to the agent

**Output:** JSON response from the agent containing:
- `response`: Agent's text response
- Other metadata from the agent execution (note: `toolsUsed` is filtered out)

### Credentials: MetadataApi

Stores the OpenMetadata server URL and JWT token for authentication.

**Configuration:**
- `serverUrl`: Base URL of the OpenMetadata instance (e.g., `https://openmetadata.example.com`)
- `jwtToken`: JWT authentication token from OpenMetadata

## Adding to n8n

### Option 1: Local Development

```bash
# Link to local n8n installation
npm run build
npm link
cd ~/.n8n/nodes
npm link n8n-nodes-metadata
```

### Option 2: npm Install

```bash
cd ~/.n8n/nodes
npm install n8n-nodes-metadata
```

Then restart n8n to load the node.

## Modifying the Node

### Adding New Parameters

Edit `nodes/MetadataAgent/MetadataAgent.node.ts` and add to the `properties` array:

```typescript
{
    displayName: 'New Parameter',
    name: 'newParam',
    type: 'string',  // or 'number', 'boolean', 'options', 'json'
    default: '',
    description: 'Description of the parameter',
}
```

### Updating the Icon

1. Place icon file in `nodes/MetadataAgent/` (PNG or SVG format)
2. Update `icon` property in the node description to reference the new file
3. Update `copy:icons` script in `package.json` if using a new file extension

### Error Handling

The node handles common API errors with descriptive messages:
- `401`: Invalid or expired JWT token
- `403`: Agent not API-enabled
- `404`: Agent not found
- `500`: Agent execution failed

## Package Configuration

The `package.json` includes n8n-specific configuration:

```json
{
  "n8n": {
    "n8nNodesApiVersion": 1,
    "credentials": ["dist/credentials/MetadataApi.credentials.js"],
    "nodes": ["dist/nodes/MetadataAgent/MetadataAgent.node.js"]
  }
}
```

- `n8nNodesApiVersion`: API version for node compatibility
- `credentials`: List of credential types provided
- `nodes`: List of nodes provided

## Testing

To test the node:

1. Build the package: `npm run build`
2. Link to n8n or install locally
3. Restart n8n
4. Create a workflow with the Metadata Agent node
5. Configure credentials with a valid OpenMetadata instance
6. Execute a test workflow

## SDK Dependency

This node uses the TypeScript SDK (`@openmetadata/ai-sdk`) as a local dependency:

```json
"dependencies": {
  "@openmetadata/ai-sdk": "file:../typescript"
}
```

The SDK handles:
- HTTP requests and authentication
- Error handling and retries
- SSE streaming (if needed)

**DO NOT** add direct HTTP calls - use the SDK.

## Related Resources

- [n8n Community Node Documentation](https://docs.n8n.io/integrations/creating-nodes/)
- [TypeScript SDK](../typescript) - The SDK this node depends on
- [OpenMetadata API Documentation](https://docs.open-metadata.org/)
