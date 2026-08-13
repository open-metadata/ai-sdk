//! Skill management commands.

use crate::client::AISdkClient;
use crate::config::ResolvedConfig;
use crate::error::CliResult;
use colored::Colorize;

/// List all skills.
pub async fn run_list(profile: &str, limit: Option<u32>, json: bool) -> CliResult<()> {
    let config = ResolvedConfig::load(profile)?;
    let client = AISdkClient::new(&config)?;

    // Use pagination - pass limit to respect user-specified limit, or None to fetch all
    let skills = client.list_skills_with_limit(limit).await?;

    if json {
        println!(
            "{}",
            serde_json::to_string_pretty(&skills).unwrap_or_default()
        );
        return Ok(());
    }

    if skills.is_empty() {
        println!("No skills found.");
        return Ok(());
    }

    println!("{}", "Skills:".bold());
    println!();

    for skill in skills {
        let display_name = skill.display_name.as_deref().unwrap_or(&skill.name);

        println!("  {} {}", "*".cyan(), display_name.bold());
        println!("    Name: {}", skill.name.dimmed());

        if let Some(provider) = &skill.provider {
            println!("    Provider: {}", provider.dimmed());
        }

        if let Some(desc) = &skill.description {
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

        if !skill.tools.is_empty() {
            println!("    Tools: {}", skill.tools.join(", ").dimmed());
        }
        println!();
    }

    Ok(())
}

/// Get detailed information about a specific skill.
pub async fn run_get(profile: &str, name: &str, json: bool) -> CliResult<()> {
    let config = ResolvedConfig::load(profile)?;
    let client = AISdkClient::new(&config)?;

    let skill = client.get_skill(name).await?;

    if json {
        println!(
            "{}",
            serde_json::to_string_pretty(&skill).unwrap_or_default()
        );
        return Ok(());
    }

    let display_name = skill.display_name.as_deref().unwrap_or(&skill.name);

    println!("{}", display_name.bold());
    println!();

    println!("  {} {}", "Name:".cyan(), skill.name);

    if let Some(id) = &skill.id {
        println!("  {} {}", "ID:".cyan(), id);
    }

    if let Some(fqn) = &skill.fully_qualified_name {
        println!("  {} {}", "FQN:".cyan(), fqn);
    }

    if let Some(provider) = &skill.provider {
        println!("  {} {}", "Provider:".cyan(), provider);
    }

    if let Some(desc) = &skill.description {
        if !desc.is_empty() {
            println!("  {} {}", "Description:".cyan(), desc);
        }
    }

    if !skill.tools.is_empty() {
        println!("  {}", "Tools:".cyan());
        for tool in &skill.tools {
            println!("    - {tool}");
        }
    }

    Ok(())
}
