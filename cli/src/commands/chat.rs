//! Interactive chat command with TUI interface.

use crate::config;
use crate::error::CliResult;
use crate::tui::run_tui;
use std::path::PathBuf;

/// Run interactive chat session with an agent.
///
/// Routing logic:
/// - `use_default = true` → use the platform's default agent (PLANNER / CHAT_MODE).
///   The TUI calls `stream_default_agent` for each message.
/// - `agent_name = Some(name)` → use the named dynamic agent (existing behaviour).
/// - both `None` / `false` → show the agent-selection menu on start.
///
/// The `debug` argument carries the raw clap value:
/// - `None`: debug disabled
/// - `Some("")`: enabled, write to default path (`~/.ai-sdk/chat-debug.log`)
/// - `Some(path)`: enabled, write to caller-provided path
pub async fn run_chat(
    profile: &str,
    agent_name: Option<&str>,
    use_default: bool,
    conversation_id: Option<&str>,
    debug: Option<String>,
) -> CliResult<()> {
    let debug_log_path: Option<PathBuf> = match debug {
        None => None,
        Some(s) if s.is_empty() => Some(config::config_dir()?.join("chat-debug.log")),
        Some(s) => Some(PathBuf::from(s)),
    };

    if let Some(path) = debug_log_path.as_ref() {
        eprintln!(
            "[ai-sdk] SSE debug events will be written to {}",
            path.display()
        );
    }

    run_tui(
        profile,
        agent_name,
        use_default,
        conversation_id.map(String::from),
        debug_log_path,
    )
    .await
}
