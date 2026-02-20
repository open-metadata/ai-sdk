# n8n-nodes-metadata

This is an n8n community node that lets you invoke [OpenMetadata](https://open-metadata.org) DynamicAgents in your n8n workflows.

DynamicAgents are AI-powered agents in OpenMetadata that can answer questions about your data, run queries, and perform various data operations.

## Installation

### In n8n Cloud or Self-Hosted

1. Go to **Settings > Community Nodes**
2. Select **Install**
3. Enter `n8n-nodes-metadata` and confirm

### Manual Installation

```bash
npm install n8n-nodes-metadata
```

## Prerequisites

1. A running OpenMetadata instance
2. A JWT token for authentication (bot token or personal access token)
3. A DynamicAgent with **API access enabled**

### Enabling API Access for an Agent

1. In OpenMetadata, navigate to your DynamicAgent
2. Edit the agent settings
3. Enable the "API Access" toggle
4. Save the agent

## Credentials

The node requires OpenMetadata API credentials:

| Field | Description |
|-------|-------------|
| Server URL | Your OpenMetadata instance URL (e.g., `https://openmetadata.example.com`) |
| JWT Token | Authentication token (bot token recommended for production) |

## Node Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| Agent Name | Yes | Name of the DynamicAgent to invoke |
| Message | Yes | The query or message to send to the agent |
| Conversation ID | No | For multi-turn conversations, pass the conversation ID from a previous response |
| Parameters | No | Additional parameters as JSON object |

## Output

The node outputs the agent's response:

```json
{
  "conversationId": "550e8400-e29b-41d4-a716-446655440000",
  "response": "The total revenue for Q4 2024 was $1.2M...",
  "toolsUsed": ["SemanticLayerQuery"],
  "usage": {
    "inputTokens": 150,
    "outputTokens": 280,
    "totalTokens": 430
  }
}
```

## Multi-Turn Conversations

To maintain conversation context across multiple agent calls:

1. First call: Leave `Conversation ID` empty
2. Capture `conversationId` from the response
3. Subsequent calls: Pass the captured `conversationId`

## Local Development & Testing

### Prerequisites

- Node.js 18+
- npm or pnpm
- n8n installed globally or locally

### Build the Node

```bash
cd n8n-nodes-metadata
npm install
npm run build
```

### Option 1: Using N8N_CUSTOM_EXTENSIONS (Recommended)

1. Build the node:
   ```bash
   npm run build
   ```

2. Set the environment variable and start n8n from THIS directory:
   ```bash
   export N8N_CUSTOM_EXTENSIONS=$(pwd)
   N8N_SECURE_COOKIE=false npx n8n
   ```

3. Open n8n at http://localhost:5678

4. Search for "Metadata Agent" in the node palette

### Development Workflow

For active development with auto-rebuild:

```bash
# Terminal 1: Watch for changes
npm run dev

# Terminal 2: Start n8n (restart after changes)
N8N_CUSTOM_EXTENSIONS="$(pwd)" n8n start
```

Note: n8n caches nodes on startup, so you need to restart n8n after rebuilding.

### Testing with a Local OpenMetadata Instance

1. Start your local OpenMetadata instance
2. Create a bot and get its JWT token
3. Create a DynamicAgent and enable API access
4. Configure the OpenMetadata API credentials in n8n with:
   - Server URL: `http://localhost:8585` (or your local URL)
   - JWT Token: Your bot's JWT token

## Troubleshooting

### "Agent not found" Error

- Verify the agent name is correct (case-sensitive)
- Check the agent exists in your OpenMetadata instance

### "Agent is not API-enabled" Error

- Open the agent in OpenMetadata UI
- Enable the "API Access" setting
- Save the agent

### "Authentication failed" Error

- Verify your JWT token is valid and not expired
- Ensure the token has permissions to access the agent
- Try generating a new token

### Connection Errors

- Verify the Server URL is correct and accessible
- Check if there are any firewalls blocking the connection
- For local development, ensure OpenMetadata is running

## License

Apache-2.0
