//! Configuration management commands.

use crate::config::{
    get_config_value, list_config, load_config, load_credentials, save_config, save_credentials,
};
use crate::error::{CliError, CliResult};
use colored::Colorize;
use std::io::{self, Write};

/// Run interactive configuration setup.
pub fn run_interactive() -> CliResult<()> {
    println!("{}", "Metadata AI Configuration".bold());
    println!("This will configure your Metadata AI CLI credentials.\n");

    // Load existing config
    let mut config = load_config().unwrap_or_default();
    let mut credentials = load_credentials().unwrap_or_default();

    // Prompt for host
    let current_host = config.default.host.clone().unwrap_or_default();
    print!(
        "Metadata Host URL [{}]: ",
        if current_host.is_empty() {
            "https://your-metadata-instance.com"
        } else {
            &current_host
        }
    );
    io::stdout().flush()?;

    let mut host_input = String::new();
    io::stdin().read_line(&mut host_input)?;
    let host_input = host_input.trim();

    if !host_input.is_empty() {
        config.default.host = Some(host_input.to_string());
    } else if config.default.host.is_none() {
        return Err(CliError::InvalidConfig("Host URL is required".to_string()));
    }

    // Prompt for token
    print!("API Token: ");
    io::stdout().flush()?;

    let mut token_input = String::new();
    io::stdin().read_line(&mut token_input)?;
    let token_input = token_input.trim();

    if !token_input.is_empty() {
        credentials.default.token = Some(token_input.to_string());
    } else if credentials.default.token.is_none() {
        return Err(CliError::InvalidConfig("API token is required".to_string()));
    }

    // Prompt for timeout (optional)
    print!("Timeout in seconds [{}]: ", config.default.timeout);
    io::stdout().flush()?;

    let mut timeout_input = String::new();
    io::stdin().read_line(&mut timeout_input)?;
    let timeout_input = timeout_input.trim();

    if !timeout_input.is_empty() {
        config.default.timeout = timeout_input
            .parse()
            .map_err(|_| CliError::InvalidConfig("Timeout must be a number".to_string()))?;
    }

    // Save configuration
    save_config(&config)?;
    save_credentials(&credentials)?;

    println!("\n{}", "Configuration saved successfully!".green());
    println!("Config location: ~/.ai-sdk/config.toml");
    println!("Credentials location: ~/.ai-sdk/credentials");

    Ok(())
}

/// Set a specific configuration value.
pub fn run_set(key: &str, value: &str) -> CliResult<()> {
    crate::config::set_config_value(key, value)?;
    println!("{} {} = {}", "Set".green(), key.bold(), value);
    Ok(())
}

/// Get a specific configuration value.
pub fn run_get(key: &str) -> CliResult<()> {
    match get_config_value(key)? {
        Some(value) => println!("{value}"),
        None => println!("(not set)"),
    }
    Ok(())
}

/// List all configuration values.
pub fn run_list() -> CliResult<()> {
    let values = list_config()?;

    println!("{}", "Current Configuration:".bold());
    println!();

    for (key, value) in values {
        println!("  {} = {}", key.cyan(), value);
    }

    Ok(())
}
