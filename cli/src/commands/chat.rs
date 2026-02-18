//! Interactive chat command with TUI interface.

use crate::error::CliResult;
use crate::tui::run_tui;

/// Run interactive chat session with an agent.
/// If agent_name is None, the TUI will show agent selection on start.
pub async fn run_chat(agent_name: Option<&str>, conversation_id: Option<&str>) -> CliResult<()> {
    run_tui(agent_name, conversation_id.map(String::from)).await
}
