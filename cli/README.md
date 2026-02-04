# Metadata AI CLI

Command-line tool for interacting with Metadata AI Agents.

## Installation

### Quick Install (Recommended)

Install the Metadata AI CLI with a single command:

```bash
curl -sSL https://open-metadata.org/cli | sh
```

This script will:
- Detect your OS (macOS or Linux) and architecture (x64 or arm64)
- Download the appropriate binary from GitHub releases
- Install to `~/.local/bin` (or `/usr/local/bin` as fallback)
- Verify the installation

**Supported platforms:**
- macOS (Intel and Apple Silicon)
- Linux (x64 and arm64)
- Windows users: Please use [WSL](https://docs.microsoft.com/en-us/windows/wsl/install)

### From Source

```bash
cd cli
cargo build --release
# Binary will be at target/release/metadata-ai
```

### Using Cargo

```bash
cargo install --path .
```

### Manual Download

Download the appropriate binary for your platform from the [releases page](https://github.com/open-metadata/metadata-ai-sdk/releases):

| Platform | Architecture | Download |
|----------|--------------|----------|
| macOS | Intel (x64) | `metadata-ai-darwin-x64.tar.gz` |
| macOS | Apple Silicon (arm64) | `metadata-ai-darwin-arm64.tar.gz` |
| Linux | x64 | `metadata-ai-linux-x64.tar.gz` |
| Linux | arm64 | `metadata-ai-linux-arm64.tar.gz` |

Extract and move to a directory in your PATH:

```bash
tar -xzf metadata-ai-<os>-<arch>.tar.gz
mv metadata-ai ~/.local/bin/
```

## Configuration

The CLI stores configuration in `~/.metadata-ai/`:

- `config.toml` - Host URL and settings
- `credentials` - Authentication token (stored with restricted permissions)

### Interactive Setup

```bash
metadata-ai configure
```

### Manual Configuration

```bash
# Set individual values
metadata-ai configure set host https://your-metadata-instance.com
metadata-ai configure set token your-jwt-token
metadata-ai configure set timeout 120

# View configuration
metadata-ai configure list
metadata-ai configure get host
```

### Environment Variables

Environment variables take precedence over file configuration:

```bash
export METADATA_HOST="https://your-metadata-instance.com"
export METADATA_TOKEN="your-jwt-token"
```

## Usage

### Interactive Chat (TUI)

The `chat` command launches a rich terminal interface for conversational interactions:

```bash
# Open TUI with agent selection menu
metadata-ai chat

# Open TUI with a specific agent
metadata-ai chat semantic-layer-agent

# Resume an existing conversation
metadata-ai chat semantic-layer-agent -c <conversation-id>
```

**TUI Features:**
- **Agent selection**: Type `/agents` or start without an agent to see available agents
- **Markdown rendering**: Bold, italic, headers, lists render properly
- **Syntax-highlighted code blocks**: SQL, Python, JSON, and more
- **Thinking/reasoning display**: Agent's thought process shown in grey
- **Scrollable history**: Use arrow keys to scroll through the conversation
- **In-chat commands**: `/agents`, `/clear`, `/quit`

**Key Bindings:**

| Key | Action |
|-----|--------|
| `Enter` | Send message |
| `↑`/`↓` | Scroll history / navigate menu |
| `Ctrl+C` | Quit |
| `Esc` | Quit / close menu |

### Discover Agents

```bash
# List all API-enabled agents
metadata-ai agents list

# Get detailed information about an agent
metadata-ai agents info semantic-layer-agent
```

### Create Agents

```bash
# Interactive wizard (recommended)
metadata-ai agents create

# Or provide all options via CLI
metadata-ai agents create \
  --name "MyAgent" \
  --description "Agent description" \
  --persona "PersonaName" \
  --api-enabled true

# Create with additional options
metadata-ai agents create \
  --name "AdvancedAgent" \
  --description "An advanced agent" \
  --persona "DataAnalyst" \
  --display-name "Advanced Agent" \
  --bot-name "MyBot" \
  --abilities search,analyze \
  --provider openai \
  --json
```

**Interactive Wizard:**

When you run `metadata-ai agents create` without required arguments, an interactive TUI wizard guides you through:

1. **Basic Details** - Enter name and description
2. **Select Persona** - Choose from available personas with filter/search
3. **Select Abilities** - Multi-select abilities (optional)
4. **Actions** - Configure task prompt and bot (optional)

The wizard automatically sets `apiEnabled: true` for created agents.

### Manage Bots

```bash
# List all bots
metadata-ai bots list

# List with options
metadata-ai bots list --limit 10 --json

# Get bot information
metadata-ai bots get <bot-name>

# Get bot info as JSON
metadata-ai bots get <bot-name> --json
```

### Manage Personas

```bash
# List all personas
metadata-ai personas list

# List with options
metadata-ai personas list --limit 10 --json

# Get persona information
metadata-ai personas get <persona-name>

# Interactive wizard (recommended)
metadata-ai personas create

# Or provide all options via CLI
metadata-ai personas create \
  --name "MyPersona" \
  --description "A helpful data assistant" \
  --prompt "You are a helpful data assistant..."

# Create with additional options
metadata-ai personas create \
  --name "DataExpert" \
  --description "Expert in data analysis" \
  --prompt "You are an expert data analyst..." \
  --display-name "Data Expert" \
  --provider openai \
  --json
```

**Interactive Wizard:**

When you run `metadata-ai personas create` without required arguments, an interactive TUI wizard guides you through:

1. **Basic Details** - Enter name and description
2. **System Prompt** - Write the persona's system prompt (multiline)
3. **Review & Submit** - Review and confirm creation

### Manage Abilities

```bash
# List all abilities
metadata-ai abilities list

# List with options
metadata-ai abilities list --limit 50 --json

# Get ability information
metadata-ai abilities get <ability-name>

# Get ability info as JSON
metadata-ai abilities get <ability-name> --json
```

### Invoke Agents (One-shot)

For scripting or single queries, use the `invoke` command:

```bash
# Simple invocation
metadata-ai invoke semantic-layer-agent "What tables are available?"

# Stream response in real-time
metadata-ai invoke semantic-layer-agent "Analyze data quality" --stream

# Show agent thinking/reasoning
metadata-ai invoke semantic-layer-agent "Explain this" --stream --thinking

# Get JSON output for scripting
metadata-ai invoke semantic-layer-agent "List all pipelines" --json

# Continue a conversation
metadata-ai invoke semantic-layer-agent "Tell me more" -c <conversation-id>

# Combine options
metadata-ai invoke planner "Create a test plan" --stream --json
```

### Output Formats

**Default (Human-readable):**
```
The available tables include:
- customers
- orders
- products

Tools used:
  - searchMetadata

Conversation ID: abc123-def456
```

**JSON (`--json`):**
```json
{
  "conversationId": "abc123-def456",
  "response": "The available tables include...",
  "toolsUsed": ["searchMetadata"],
  "usage": {
    "promptTokens": 150,
    "completionTokens": 200,
    "totalTokens": 350
  }
}
```

## Error Messages

| Error | Solution |
|-------|----------|
| Authentication failed | Run `metadata-ai configure` to set credentials |
| Agent is not API-enabled | Enable API access in the Metadata UI |
| Agent not found | Check agent name with `metadata-ai agents list` |
| Rate limit exceeded | Wait before retrying |
| Configuration not found | Run `metadata-ai configure` |

## Development

### Building

```bash
cargo build
```

### Running Tests

```bash
cargo test
```

### Release Build

```bash
cargo build --release
```

The release build is optimized for size with LTO enabled.

## Architecture

```
src/
├── main.rs          # CLI entry point and argument parsing
├── commands/        # Command implementations
│   ├── configure.rs # Configuration management
│   ├── agents.rs    # Agent discovery and creation
│   ├── abilities.rs # Ability listing and info
│   ├── bots.rs      # Bot management
│   ├── personas.rs  # Persona management
│   ├── invoke.rs    # Agent invocation (one-shot)
│   └── chat.rs      # Interactive TUI chat
├── tui/             # Terminal UI components
│   ├── mod.rs       # Module exports
│   ├── app.rs       # Application state (chat)
│   ├── ui.rs        # Layout, rendering, event loop
│   ├── markdown.rs  # Markdown-to-terminal renderer
│   ├── wizard.rs    # Shared wizard framework
│   ├── create_persona.rs  # Persona creation wizard
│   └── create_agent.rs    # Agent creation wizard
├── client.rs        # HTTP client for Metadata API
├── config.rs        # Configuration file handling
├── streaming.rs     # SSE parser for streaming responses
└── error.rs         # Error types and handling
```

## License

Apache-2.0
