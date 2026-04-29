//! Interactive chat command with TUI interface.

use crate::error::CliResult;
use crate::tui::run_tui;

/// Run interactive chat session with an agent.
///
/// Routing logic:
/// - `use_default = true` → use the platform's default agent (PLANNER / CHAT_MODE).
///   The TUI calls `stream_default_agent` for each message.
/// - `agent_name = Some(name)` → use the named dynamic agent (existing behaviour).
/// - both `None` / `false` → show the agent-selection menu on start.
pub async fn run_chat(
    profile: &str,
    agent_name: Option<&str>,
    use_default: bool,
    conversation_id: Option<&str>,
) -> CliResult<()> {
    run_tui(
        profile,
        agent_name,
        use_default,
        conversation_id.map(String::from),
    )
    .await
}
