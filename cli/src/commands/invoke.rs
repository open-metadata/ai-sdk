//! Agent invocation commands.

use crate::client::{AISdkClient, InvokeResponse};
use crate::config::ResolvedConfig;
use crate::error::{CliError, CliResult};
use crate::streaming::{process_stream_with_debug, Sender};
use colored::Colorize;
use std::io::{self, Write};

/// Invoke an agent synchronously.
///
/// When `use_default` is `true` (or `agent_name` is `None`), the platform's
/// default agent (PLANNER / CHAT_MODE) is used instead of a named dynamic agent.
pub async fn run_invoke(
    profile: &str,
    agent_name: Option<&str>,
    use_default: bool,
    message: Option<&str>,
    conversation_id: Option<&str>,
    json_output: bool,
) -> CliResult<()> {
    let config = ResolvedConfig::load(profile)?;
    let client = AISdkClient::new(&config)?;

    let response = match (use_default, agent_name) {
        (false, Some(name)) => client.invoke(name, message, conversation_id).await?,
        _ => {
            let msg = message.ok_or_else(|| {
                CliError::Other("A message is required when using the default agent".into())
            })?;
            client.invoke_default_agent(msg, conversation_id).await?
        }
    };

    if json_output {
        print_json(&response)?;
    } else {
        print_response(&response);
    }

    Ok(())
}

/// Invoke an agent with streaming output.
///
/// When `use_default` is `true` (or `agent_name` is `None`), the platform's
/// default agent (PLANNER / CHAT_MODE) is used instead of a named dynamic agent.
#[allow(clippy::too_many_arguments)]
pub async fn run_stream(
    profile: &str,
    agent_name: Option<&str>,
    use_default: bool,
    message: Option<&str>,
    conversation_id: Option<&str>,
    json_output: bool,
    show_thinking: bool,
    debug: bool,
) -> CliResult<()> {
    let config = ResolvedConfig::load(profile)?;
    let client = AISdkClient::new(&config)?;

    let response = match (use_default, agent_name) {
        (false, Some(name)) => client.stream(name, message, conversation_id).await?,
        _ => {
            let msg = message.ok_or_else(|| {
                CliError::Other("A message is required when using the default agent".into())
            })?;
            client.stream_default_agent(msg, conversation_id).await?
        }
    };

    if json_output {
        // For JSON output, collect all content and output as JSON at the end
        let mut full_content = String::new();
        let mut tools_used: Vec<String> = Vec::new();
        let mut final_conversation_id: Option<String> = None;

        process_stream_with_debug(
            response,
            |message| {
                final_conversation_id = Some(message.conversation_id.clone());

                match message.sender {
                    Sender::Assistant => {
                        let text = message.text_content();
                        if !text.is_empty() {
                            full_content.push_str(&text);
                        }
                        let tools = message.tools_used();
                        tools_used.extend(tools);
                    }
                    Sender::System => {
                        // Thinking messages not included in JSON output
                    }
                    Sender::Human => {
                        // Human messages ignored in output
                    }
                }
            },
            debug,
        )
        .await?;

        let response = InvokeResponse {
            conversation_id: final_conversation_id.unwrap_or_default(),
            response: full_content,
            tools_used,
            thinking_steps: Vec::new(),
            usage: None,
        };

        print_json(&response)?;
    } else {
        // Stream to terminal in real-time
        let mut in_thinking = false;

        process_stream_with_debug(
            response,
            |message| {
                match message.sender {
                    Sender::System => {
                        // System messages are "thinking" content. Each step
                        // is a discrete reasoning event, so render one per
                        // line for readability.
                        if show_thinking {
                            let text = message.text_content();
                            if !text.is_empty() {
                                in_thinking = true;
                                let trimmed = text.trim_end();
                                println!("{}", trimmed.bright_black());
                                let _ = io::stdout().flush();
                            }
                        }
                    }
                    Sender::Assistant => {
                        if in_thinking {
                            // Transition from thinking to content - add newline separator
                            println!();
                            in_thinking = false;
                        }

                        let text = message.text_content();
                        if !text.is_empty() {
                            print!("{text}");
                            let _ = io::stdout().flush();
                        }

                        // Show tool usage
                        let tools = message.tools_used();
                        for tool_name in tools {
                            print!("\n{} {}\n", "[Using tool:".dimmed(), tool_name.dimmed());
                            let _ = io::stdout().flush();
                        }
                    }
                    Sender::Human => {
                        // Human messages ignored in streaming output
                    }
                }
            },
            debug,
        )
        .await?;

        // Ensure newline at end
        println!();
    }

    Ok(())
}

/// Print response in human-readable format.
fn print_response(response: &InvokeResponse) {
    println!("{}", response.response);

    if !response.tools_used.is_empty() {
        println!();
        println!("{}", "Tools used:".dimmed());
        for tool in &response.tools_used {
            println!("  - {}", tool.dimmed());
        }
    }

    if let Some(usage) = &response.usage {
        println!();
        println!(
            "{}",
            format!(
                "Tokens: {} prompt, {} completion, {} total",
                usage.prompt_tokens, usage.completion_tokens, usage.total_tokens
            )
            .dimmed()
        );
    }

    println!();
    println!(
        "{} {}",
        "Conversation ID:".dimmed(),
        response.conversation_id.dimmed()
    );
}

/// Print response as JSON.
fn print_json(response: &InvokeResponse) -> CliResult<()> {
    let json = serde_json::to_string_pretty(response)
        .map_err(|e| crate::error::CliError::ParseError(e.to_string()))?;
    println!("{json}");
    Ok(())
}
