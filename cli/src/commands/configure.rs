//! Configuration management commands.

use crate::config::{
    get_config_value, list_config, list_profiles, load_config, load_credentials, mask_token,
    remove_profile, save_config, save_credentials,
};
use crate::error::{CliError, CliResult};
use colored::Colorize;
use std::io::{self, Write};

/// Run interactive configuration setup.
pub fn run_interactive(profile: &str) -> CliResult<()> {
    println!("{}", "AI SDK Configuration".bold());
    println!("Configuring profile: {}\n", profile.cyan());

    // Load existing config
    let mut config = load_config().unwrap_or_default();
    let mut credentials = load_credentials().unwrap_or_default();

    let profile_config = config.profiles.entry(profile.to_string()).or_default();

    // Prompt for host
    let current_host = profile_config.host.clone().unwrap_or_default();
    print!(
        "Host URL [{}]: ",
        if current_host.is_empty() {
            "https://your-instance.getcollate.io"
        } else {
            &current_host
        }
    );
    io::stdout().flush()?;

    let mut host_input = String::new();
    io::stdin().read_line(&mut host_input)?;
    let host_input = host_input.trim();

    if !host_input.is_empty() {
        config.profiles.entry(profile.to_string()).or_default().host = Some(host_input.to_string());
    } else if config
        .profiles
        .get(profile)
        .and_then(|p| p.host.as_ref())
        .is_none()
    {
        return Err(CliError::InvalidConfig("Host URL is required".to_string()));
    }

    // Prompt for token
    print!("API Token: ");
    io::stdout().flush()?;

    let mut token_input = String::new();
    io::stdin().read_line(&mut token_input)?;
    let token_input = token_input.trim();

    let profile_creds = credentials.profiles.entry(profile.to_string()).or_default();

    if !token_input.is_empty() {
        profile_creds.token = Some(token_input.to_string());
    } else if profile_creds.token.is_none() {
        return Err(CliError::InvalidConfig("API token is required".to_string()));
    }

    // Prompt for timeout (optional)
    let current_timeout = config
        .profiles
        .get(profile)
        .map(|p| p.timeout)
        .unwrap_or(120);
    print!("Timeout in seconds [{current_timeout}]: ");
    io::stdout().flush()?;

    let mut timeout_input = String::new();
    io::stdin().read_line(&mut timeout_input)?;
    let timeout_input = timeout_input.trim();

    if !timeout_input.is_empty() {
        config
            .profiles
            .entry(profile.to_string())
            .or_default()
            .timeout = timeout_input
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
pub fn run_set(profile: &str, key: &str, value: &str) -> CliResult<()> {
    crate::config::set_config_value(profile, key, value)?;
    let display_value = if key == "token" {
        mask_token(value)
    } else {
        value.to_string()
    };
    println!(
        "{} [{}] {} = {}",
        "Set".green(),
        profile.cyan(),
        key.bold(),
        display_value
    );
    Ok(())
}

/// Get a specific configuration value.
pub fn run_get(profile: &str, key: &str) -> CliResult<()> {
    match get_config_value(profile, key)? {
        Some(value) => println!("{value}"),
        None => println!("(not set)"),
    }
    Ok(())
}

/// List all configuration values.
pub fn run_list(profile: &str) -> CliResult<()> {
    let values = list_config(profile)?;

    println!(
        "{}",
        format!("Current Configuration (profile: {profile}):").bold()
    );
    println!();

    for (key, value) in values {
        println!("  {} = {}", key.cyan(), value);
    }

    Ok(())
}

/// List all configured profiles.
pub fn run_list_profiles() -> CliResult<()> {
    let profiles = list_profiles()?;

    if profiles.is_empty() {
        println!("No profiles configured.");
        println!(
            "\n{}",
            "Tip: Run 'ai-sdk configure' to create a default profile.".dimmed()
        );
        return Ok(());
    }

    println!("{}", "Configured Profiles:".bold());
    println!();

    for (name, host) in profiles {
        let host_display = host.unwrap_or_else(|| "(no host set)".to_string());
        println!(
            "  {} {} ({})",
            "*".cyan(),
            name.bold(),
            host_display.dimmed()
        );
    }

    Ok(())
}

/// Remove a profile.
pub fn run_remove_profile(name: &str) -> CliResult<()> {
    remove_profile(name)?;
    println!("{} Removed profile: {}", "Success!".green().bold(), name);
    Ok(())
}
