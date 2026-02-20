# CLAUDE.md - Rust CLI

## Overview

Rust CLI for Metadata AI agents. Provides both command-line invocation and an interactive TUI chat interface.

## Build Commands

```bash
cargo build              # Debug build
cargo build --release    # Release build (optimized)
cargo test               # Run tests
cargo fmt                # Format code
cargo clippy             # Lint
```

## Project Structure

```
cli/
├── src/
│   ├── main.rs          # Entry point, CLI argument parsing
│   ├── commands/        # Subcommand implementations
│   │   ├── configure.rs # ai-sdk configure
│   │   ├── agents.rs    # ai-sdk agents list/info
│   │   ├── invoke.rs    # ai-sdk invoke
│   │   └── chat.rs      # ai-sdk chat (TUI mode)
│   ├── tui/             # Terminal UI components
│   │   ├── mod.rs       # Module exports
│   │   ├── app.rs       # Application state
│   │   ├── ui.rs        # Layout and rendering
│   │   └── markdown.rs  # Markdown renderer with syntax highlighting
│   ├── client.rs        # HTTP client for AI SDK API
│   ├── config.rs        # Config file management (~/.ai-sdk/)
│   ├── streaming.rs     # SSE parser
│   └── error.rs         # Error types
├── Cargo.toml
└── install.sh           # curl installer script
```

## Config Location

- `~/.ai-sdk/config.toml` - Host and settings
- `~/.ai-sdk/credentials` - Token (0600 permissions)
- Environment override: `AI_SDK_HOST`, `AI_SDK_TOKEN`

## Key Dependencies

- `clap` - CLI argument parsing
- `reqwest` - HTTP client
- `tokio` - Async runtime
- `serde` / `toml` - Serialization
- `ratatui` - TUI framework
- `crossterm` - Terminal events
- `syntect` - Syntax highlighting for code blocks
- `pulldown-cmark` - Markdown parsing

## TUI Chat Mode

The `chat` command launches an interactive terminal interface:

```bash
ai-sdk chat              # Opens agent selector
ai-sdk chat AgentName    # Opens chat with specific agent
ai-sdk chat AgentName -c <conv-id>  # Resume conversation
```

### TUI Features

- **Agent selection menu**: `/agents` or start without agent name
- **Markdown rendering**: Bold, italic, headers, lists
- **Syntax-highlighted code blocks**: SQL, Python, JSON, etc.
- **Thinking display**: Agent reasoning shown in grey, persists in history
- **Scrollable history**: Arrow keys to scroll through conversation
- **Commands**: `/agents`, `/clear`, `/quit`

### TUI Key Bindings

| Key | Action |
|-----|--------|
| `Enter` | Send message |
| `↑`/`↓` | Scroll history (or navigate menu) |
| `Ctrl+C` | Quit |
| `Esc` | Quit (or close menu) |

## Adding a New Command

1. Create `src/commands/newcmd.rs`
2. Add to `src/commands/mod.rs`
3. Add subcommand enum variant in `main.rs`
4. Implement handler function

## DO NOT

- Use blocking HTTP calls (use async/await)
- Store tokens in config.toml (use credentials file)
- Print sensitive data to stdout
- Use `blocking_send` in async contexts (use `try_send`)
