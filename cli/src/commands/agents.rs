//! Agent discovery and management commands.

use crate::client::{CreateAgentRequest, EntityReference, MetadataClient};
use crate::config::ResolvedConfig;
use crate::error::CliResult;
use colored::Colorize;

/// List all API-enabled agents.
pub async fn run_list() -> CliResult<()> {
    let config = ResolvedConfig::load()?;
    let client = MetadataClient::new(&config)?;

    let agents = client.list_agents().await?;

    if agents.is_empty() {
        println!("No API-enabled agents found.");
        println!(
            "\n{}",
            "Tip: Enable API access for agents in the Metadata UI.".dimmed()
        );
        return Ok(());
    }

    println!("{}", "API-Enabled Agents:".bold());
    println!();

    for agent in agents {
        let display_name = agent.display_name.as_deref().unwrap_or(&agent.name);

        println!("  {} {}", "*".cyan(), display_name.bold());
        println!("    Name: {}", agent.name.dimmed());

        if let Some(desc) = &agent.description {
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

/// Get detailed information about a specific agent.
pub async fn run_info(name: &str) -> CliResult<()> {
    let config = ResolvedConfig::load()?;
    let client = MetadataClient::new(&config)?;

    let agent = client.get_agent(name).await?;

    let display_name = agent.display_name.as_deref().unwrap_or(&agent.name);

    println!("{}", display_name.bold());
    println!();

    println!("  {} {}", "Name:".cyan(), agent.name);

    if let Some(desc) = &agent.description {
        if !desc.is_empty() {
            println!("  {} {}", "Description:".cyan(), desc);
        }
    }

    println!(
        "  {} {}",
        "API Enabled:".cyan(),
        if agent.api_enabled {
            "Yes".green()
        } else {
            "No".red()
        }
    );

    if !agent.abilities.is_empty() {
        println!("  {}", "Abilities:".cyan());
        for ability in &agent.abilities {
            println!("    - {}", ability.display_name());
        }
    }

    Ok(())
}

/// Create a new dynamic agent.
#[allow(clippy::too_many_arguments)]
pub async fn run_create(
    name: &str,
    description: &str,
    persona: &str,
    mode: &str,
    display_name: Option<&str>,
    icon: Option<&str>,
    bot_name: Option<&str>,
    abilities: Option<Vec<String>>,
    api_enabled: Option<bool>,
    provider: Option<&str>,
    json: bool,
) -> CliResult<()> {
    let config = ResolvedConfig::load()?;
    let client = MetadataClient::new(&config)?;

    // Look up the persona by name to get its ID (required by the API schema)
    let persona_info = client.get_persona(persona).await?;
    let persona_id = persona_info
        .id
        .ok_or_else(|| crate::error::CliError::Other(format!("Persona '{}' has no ID", persona)))?;

    // Build ability references if provided
    let ability_refs = if let Some(ability_names) = abilities {
        let mut refs = Vec::new();
        for ability_name in ability_names {
            let ability_info = client.get_ability(&ability_name).await?;
            let ability_id = ability_info.id.ok_or_else(|| {
                crate::error::CliError::Other(format!("Ability '{}' has no ID", ability_name))
            })?;
            refs.push(EntityReference {
                id: Some(ability_id),
                name: Some(ability_info.name),
                entity_type: Some("ability".to_string()),
                fully_qualified_name: ability_info.fully_qualified_name,
                display_name: ability_info.display_name,
            });
        }
        Some(refs)
    } else {
        None
    };

    let request = CreateAgentRequest {
        name: name.to_string(),
        description: description.to_string(),
        persona: EntityReference {
            id: Some(persona_id),
            name: Some(persona_info.name),
            entity_type: Some("aiPersona".to_string()),
            fully_qualified_name: persona_info.fully_qualified_name,
            display_name: persona_info.display_name,
        },
        mode: mode.to_string(),
        display_name: display_name.map(String::from),
        icon: icon.map(String::from),
        bot_name: bot_name.map(String::from),
        abilities: ability_refs,
        api_enabled: Some(api_enabled.unwrap_or(true)),
        provider: Some(provider.unwrap_or("user").to_string()),
        entity_status: Some("Approved".to_string()),
    };

    let agent = client.create_agent(request).await?;

    if json {
        println!(
            "{}",
            serde_json::to_string_pretty(&agent).unwrap_or_default()
        );
        return Ok(());
    }

    println!(
        "{} Created agent: {}",
        "Success!".green().bold(),
        agent.name
    );

    if let Some(id) = &agent.id {
        println!("  {} {}", "ID:".cyan(), id);
    }

    if let Some(display) = &agent.display_name {
        println!("  {} {}", "Display Name:".cyan(), display);
    }

    if let Some(persona) = &agent.persona {
        if let Some(persona_name) = &persona.name {
            println!("  {} {}", "Persona:".cyan(), persona_name);
        }
    }

    if let Some(mode) = &agent.mode {
        println!("  {} {}", "Mode:".cyan(), mode);
    }

    println!(
        "  {} {}",
        "API Enabled:".cyan(),
        if agent.api_enabled {
            "Yes".green()
        } else {
            "No".red()
        }
    );

    Ok(())
}
