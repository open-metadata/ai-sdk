//! Ability management commands.

use crate::client::AiSdkClient;
use crate::config::ResolvedConfig;
use crate::error::CliResult;
use colored::Colorize;

/// List all abilities.
pub async fn run_list(limit: Option<u32>, json: bool) -> CliResult<()> {
    let config = ResolvedConfig::load()?;
    let client = AiSdkClient::new(&config)?;

    // Use pagination - pass limit to respect user-specified limit, or None to fetch all
    let abilities = client.list_abilities_with_limit(limit).await?;

    if json {
        println!(
            "{}",
            serde_json::to_string_pretty(&abilities).unwrap_or_default()
        );
        return Ok(());
    }

    if abilities.is_empty() {
        println!("No abilities found.");
        return Ok(());
    }

    println!("{}", "Abilities:".bold());
    println!();

    for ability in abilities {
        let display_name = ability.display_name.as_deref().unwrap_or(&ability.name);

        println!("  {} {}", "*".cyan(), display_name.bold());
        println!("    Name: {}", ability.name.dimmed());

        if let Some(provider) = &ability.provider {
            println!("    Provider: {}", provider.dimmed());
        }

        if let Some(desc) = &ability.description {
            if !desc.is_empty() {
                // Truncate long descriptions (char-boundary-safe)
                let truncated = if desc.chars().count() > 80 {
                    let t: String = desc.chars().take(77).collect();
                    format!("{t}...")
                } else {
                    desc.clone()
                };
                println!("    {}", truncated.dimmed());
            }
        }

        if !ability.tools.is_empty() {
            println!("    Tools: {}", ability.tools.join(", ").dimmed());
        }
        println!();
    }

    Ok(())
}

/// Get detailed information about a specific ability.
pub async fn run_get(name: &str, json: bool) -> CliResult<()> {
    let config = ResolvedConfig::load()?;
    let client = AiSdkClient::new(&config)?;

    let ability = client.get_ability(name).await?;

    if json {
        println!(
            "{}",
            serde_json::to_string_pretty(&ability).unwrap_or_default()
        );
        return Ok(());
    }

    let display_name = ability.display_name.as_deref().unwrap_or(&ability.name);

    println!("{}", display_name.bold());
    println!();

    println!("  {} {}", "Name:".cyan(), ability.name);

    if let Some(id) = &ability.id {
        println!("  {} {}", "ID:".cyan(), id);
    }

    if let Some(fqn) = &ability.fully_qualified_name {
        println!("  {} {}", "FQN:".cyan(), fqn);
    }

    if let Some(provider) = &ability.provider {
        println!("  {} {}", "Provider:".cyan(), provider);
    }

    if let Some(desc) = &ability.description {
        if !desc.is_empty() {
            println!("  {} {}", "Description:".cyan(), desc);
        }
    }

    if !ability.tools.is_empty() {
        println!("  {}", "Tools:".cyan());
        for tool in &ability.tools {
            println!("    - {tool}");
        }
    }

    Ok(())
}
