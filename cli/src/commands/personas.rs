//! Persona management commands.

use crate::client::{CreatePersonaRequest, MetadataClient};
use crate::config::ResolvedConfig;
use crate::error::CliResult;
use colored::Colorize;

/// List all personas.
pub async fn run_list(limit: Option<u32>, json: bool) -> CliResult<()> {
    let config = ResolvedConfig::load()?;
    let client = MetadataClient::new(&config)?;

    // Use pagination - pass limit to respect user-specified limit, or None to fetch all
    let personas = client.list_personas_with_limit(limit).await?;

    if json {
        println!(
            "{}",
            serde_json::to_string_pretty(&personas).unwrap_or_default()
        );
        return Ok(());
    }

    if personas.is_empty() {
        println!("No personas found.");
        return Ok(());
    }

    println!("{}", "Personas:".bold());
    println!();

    for persona in personas {
        let display_name = persona.display_name.as_deref().unwrap_or(&persona.name);

        println!("  {} {}", "*".cyan(), display_name.bold());
        println!("    Name: {}", persona.name.dimmed());

        if let Some(provider) = &persona.provider {
            println!("    Provider: {}", provider.dimmed());
        }

        if let Some(desc) = &persona.description {
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

/// Get detailed information about a specific persona.
pub async fn run_get(name: &str, json: bool) -> CliResult<()> {
    let config = ResolvedConfig::load()?;
    let client = MetadataClient::new(&config)?;

    let persona = client.get_persona(name).await?;

    if json {
        println!(
            "{}",
            serde_json::to_string_pretty(&persona).unwrap_or_default()
        );
        return Ok(());
    }

    let display_name = persona.display_name.as_deref().unwrap_or(&persona.name);

    println!("{}", display_name.bold());
    println!();

    println!("  {} {}", "Name:".cyan(), persona.name);

    if let Some(id) = &persona.id {
        println!("  {} {}", "ID:".cyan(), id);
    }

    if let Some(fqn) = &persona.fully_qualified_name {
        println!("  {} {}", "FQN:".cyan(), fqn);
    }

    if let Some(provider) = &persona.provider {
        println!("  {} {}", "Provider:".cyan(), provider);
    }

    if let Some(desc) = &persona.description {
        if !desc.is_empty() {
            println!("  {} {}", "Description:".cyan(), desc);
        }
    }

    if let Some(prompt) = &persona.prompt {
        if !prompt.is_empty() {
            println!("  {}", "Prompt:".cyan());
            // Display prompt with indentation
            for line in prompt.lines() {
                println!("    {line}");
            }
        }
    }

    Ok(())
}

/// Create a new persona.
pub async fn run_create(
    name: &str,
    description: &str,
    prompt: &str,
    display_name: Option<&str>,
    provider: Option<&str>,
    json: bool,
) -> CliResult<()> {
    let config = ResolvedConfig::load()?;
    let client = MetadataClient::new(&config)?;

    let request = CreatePersonaRequest {
        name: name.to_string(),
        description: description.to_string(),
        prompt: prompt.to_string(),
        display_name: display_name.map(String::from),
        provider: Some(provider.unwrap_or("user").to_string()),
    };

    let persona = client.create_persona(request).await?;

    if json {
        println!(
            "{}",
            serde_json::to_string_pretty(&persona).unwrap_or_default()
        );
        return Ok(());
    }

    println!(
        "{} Created persona: {}",
        "Success!".green().bold(),
        persona.name
    );

    if let Some(id) = &persona.id {
        println!("  {} {}", "ID:".cyan(), id);
    }

    if let Some(display) = &persona.display_name {
        println!("  {} {}", "Display Name:".cyan(), display);
    }

    if let Some(provider) = &persona.provider {
        println!("  {} {}", "Provider:".cyan(), provider);
    }

    Ok(())
}
