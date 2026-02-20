//! Bot discovery commands.

use crate::client::MetadataClient;
use crate::config::ResolvedConfig;
use crate::error::CliResult;
use colored::Colorize;

/// List all bots.
pub async fn run_list(limit: Option<u32>, json: bool) -> CliResult<()> {
    let config = ResolvedConfig::load()?;
    let client = MetadataClient::new(&config)?;

    // Use pagination - pass limit to respect user-specified limit, or None to fetch all
    let bots = client.list_bots_with_limit(limit).await?;

    if json {
        println!(
            "{}",
            serde_json::to_string_pretty(&bots).unwrap_or_default()
        );
        return Ok(());
    }

    if bots.is_empty() {
        println!("No bots found.");
        return Ok(());
    }

    println!("{}", "Bots:".bold());
    println!();

    for bot in bots {
        let display_name = bot.display_name.as_deref().unwrap_or(&bot.name);

        println!("  {} {}", "*".cyan(), display_name.bold());
        println!("    Name: {}", bot.name.dimmed());

        if let Some(desc) = &bot.description {
            if !desc.is_empty() {
                // Truncate long descriptions
                let truncated = if desc.len() > 80 {
                    format!("{}...", &desc[..77])
                } else {
                    desc.clone()
                };
                println!("    {}", truncated.dimmed());
            }
        }
        println!();
    }

    Ok(())
}

/// Get detailed information about a specific bot.
pub async fn run_get(name: &str, json: bool) -> CliResult<()> {
    let config = ResolvedConfig::load()?;
    let client = MetadataClient::new(&config)?;

    let bot = client.get_bot(name).await?;

    if json {
        println!("{}", serde_json::to_string_pretty(&bot).unwrap_or_default());
        return Ok(());
    }

    let display_name = bot.display_name.as_deref().unwrap_or(&bot.name);

    println!("{}", display_name.bold());
    println!();

    println!("  {} {}", "Name:".cyan(), bot.name);

    if let Some(id) = &bot.id {
        println!("  {} {}", "ID:".cyan(), id);
    }

    if let Some(fqn) = &bot.fully_qualified_name {
        println!("  {} {}", "FQN:".cyan(), fqn);
    }

    if let Some(desc) = &bot.description {
        if !desc.is_empty() {
            println!("  {} {}", "Description:".cyan(), desc);
        }
    }

    Ok(())
}
