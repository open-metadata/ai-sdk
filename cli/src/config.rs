//! Configuration management for AI SDK CLI.
//!
//! Configuration is stored in `~/.ai-sdk/` with separate files for settings and credentials:
//! - `config.toml`: Host URL, timeout, and other settings
//! - `credentials`: Authentication token (separate for security)
//!
//! Environment variables take precedence over file configuration:
//! - `AI_SDK_HOST`: Server URL
//! - `AI_SDK_TOKEN`: JWT token

use crate::error::{CliError, CliResult};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;

const CONFIG_DIR: &str = ".ai-sdk";
const CONFIG_FILE: &str = "config.toml";
const CREDENTIALS_FILE: &str = "credentials";

/// Main configuration structure.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Config {
    #[serde(flatten)]
    pub profiles: HashMap<String, ProfileConfig>,
}

/// Profile-specific configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProfileConfig {
    #[serde(default)]
    pub host: Option<String>,
    #[serde(default = "default_timeout")]
    pub timeout: u64,
}

impl Default for ProfileConfig {
    fn default() -> Self {
        Self {
            host: None,
            timeout: default_timeout(),
        }
    }
}

fn default_timeout() -> u64 {
    120
}

/// Credentials structure (stored separately).
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Credentials {
    #[serde(flatten)]
    pub profiles: HashMap<String, ProfileCredentials>,
}

/// Profile-specific credentials.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ProfileCredentials {
    #[serde(default)]
    pub token: Option<String>,
}

/// Resolved configuration combining file config and environment variables.
#[derive(Debug, Clone)]
pub struct ResolvedConfig {
    pub host: String,
    pub token: String,
    pub timeout: u64,
}

impl ResolvedConfig {
    /// Load and resolve configuration from all sources.
    ///
    /// Priority (highest to lowest):
    /// 1. Environment variables
    /// 2. Config files
    pub fn load(profile: &str) -> CliResult<Self> {
        let env_host = std::env::var("AI_SDK_HOST").ok();
        let env_token = std::env::var("AI_SDK_TOKEN").ok();

        let config = load_config().unwrap_or_default();
        let credentials = load_credentials().unwrap_or_default();

        let profile_config = config.profiles.get(profile);
        let profile_creds = credentials.profiles.get(profile);

        let host = env_host
            .or_else(|| profile_config.and_then(|p| p.host.clone()))
            .ok_or_else(|| CliError::ConfigNotFound(profile.to_string()))?;

        let token = env_token
            .or_else(|| profile_creds.and_then(|p| p.token.clone()))
            .ok_or_else(|| CliError::ConfigNotFound(profile.to_string()))?;

        let timeout = profile_config
            .map(|p| p.timeout)
            .unwrap_or(default_timeout());

        Ok(Self {
            host,
            token,
            timeout,
        })
    }

    /// Check if configuration is complete.
    #[allow(dead_code)]
    pub fn is_complete(&self) -> bool {
        !self.host.is_empty() && !self.token.is_empty()
    }
}

/// Get the config directory path.
pub fn config_dir() -> CliResult<PathBuf> {
    dirs::home_dir()
        .map(|home| home.join(CONFIG_DIR))
        .ok_or_else(|| CliError::InvalidConfig("Cannot determine home directory".to_string()))
}

/// Get the config file path.
pub fn config_path() -> CliResult<PathBuf> {
    Ok(config_dir()?.join(CONFIG_FILE))
}

/// Get the credentials file path.
pub fn credentials_path() -> CliResult<PathBuf> {
    Ok(config_dir()?.join(CREDENTIALS_FILE))
}

/// Load configuration from file.
pub fn load_config() -> CliResult<Config> {
    let path = config_path()?;
    if !path.exists() {
        return Ok(Config::default());
    }

    let content = fs::read_to_string(&path)?;
    toml::from_str(&content)
        .map_err(|e| CliError::InvalidConfig(format!("Failed to parse config: {e}")))
}

/// Load credentials from file.
pub fn load_credentials() -> CliResult<Credentials> {
    let path = credentials_path()?;
    if !path.exists() {
        return Ok(Credentials::default());
    }

    let content = fs::read_to_string(&path)?;
    toml::from_str(&content)
        .map_err(|e| CliError::InvalidConfig(format!("Failed to parse credentials: {e}")))
}

/// Save configuration to file.
pub fn save_config(config: &Config) -> CliResult<()> {
    let dir = config_dir()?;
    fs::create_dir_all(&dir)?;

    let path = config_path()?;
    let content = toml::to_string_pretty(config)
        .map_err(|e| CliError::InvalidConfig(format!("Failed to serialize config: {e}")))?;

    fs::write(&path, content)?;
    Ok(())
}

/// Save credentials to file with restricted permissions.
pub fn save_credentials(credentials: &Credentials) -> CliResult<()> {
    let dir = config_dir()?;
    fs::create_dir_all(&dir)?;

    let path = credentials_path()?;
    let content = toml::to_string_pretty(credentials)
        .map_err(|e| CliError::InvalidConfig(format!("Failed to serialize credentials: {e}")))?;

    fs::write(&path, &content)?;

    // Set restrictive permissions on Unix
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let mut perms = fs::metadata(&path)?.permissions();
        perms.set_mode(0o600);
        fs::set_permissions(&path, perms)?;
    }

    Ok(())
}

/// Get a specific configuration value.
pub fn get_config_value(profile: &str, key: &str) -> CliResult<Option<String>> {
    let config = load_config()?;
    let credentials = load_credentials()?;

    let profile_config = config.profiles.get(profile);
    let profile_creds = credentials.profiles.get(profile);

    match key {
        "host" => Ok(profile_config.and_then(|p| p.host.clone())),
        "timeout" => Ok(Some(
            profile_config
                .map(|p| p.timeout)
                .unwrap_or(default_timeout())
                .to_string(),
        )),
        "token" => Ok(profile_creds.and_then(|p| p.token.as_ref().map(|t| mask_token(t)))),
        _ => Err(CliError::InvalidConfig(format!("Unknown key: {key}"))),
    }
}

/// Set a specific configuration value.
pub fn set_config_value(profile: &str, key: &str, value: &str) -> CliResult<()> {
    match key {
        "host" => {
            let mut config = load_config()?;
            config.profiles.entry(profile.to_string()).or_default().host = Some(value.to_string());
            save_config(&config)
        }
        "timeout" => {
            let timeout: u64 = value
                .parse()
                .map_err(|_| CliError::InvalidConfig("Timeout must be a number".to_string()))?;
            let mut config = load_config()?;
            config
                .profiles
                .entry(profile.to_string())
                .or_default()
                .timeout = timeout;
            save_config(&config)
        }
        "token" => {
            let mut credentials = load_credentials()?;
            credentials
                .profiles
                .entry(profile.to_string())
                .or_default()
                .token = Some(value.to_string());
            save_credentials(&credentials)
        }
        _ => Err(CliError::InvalidConfig(format!("Unknown key: {key}"))),
    }
}

/// Mask a token for display, showing only first/last 4 characters.
pub fn mask_token(token: &str) -> String {
    let char_count = token.chars().count();
    if char_count <= 12 {
        return "*".repeat(char_count);
    }
    let prefix: String = token.chars().take(4).collect();
    let suffix: String = token.chars().skip(char_count - 4).collect();
    format!("{prefix}...{suffix}")
}

/// List all configuration values.
pub fn list_config(profile: &str) -> CliResult<Vec<(String, String)>> {
    let config = load_config()?;
    let credentials = load_credentials()?;

    let profile_config = config.profiles.get(profile);
    let profile_creds = credentials.profiles.get(profile);

    let mut values = Vec::new();

    let env_host = std::env::var("AI_SDK_HOST").ok();
    let env_token = std::env::var("AI_SDK_TOKEN").ok();

    let host_value = env_host
        .map(|h| format!("{h} (from env)"))
        .or_else(|| profile_config.and_then(|p| p.host.clone()))
        .unwrap_or_else(|| "(not set)".to_string());
    values.push(("host".to_string(), host_value));

    values.push((
        "timeout".to_string(),
        profile_config
            .map(|p| p.timeout)
            .unwrap_or(default_timeout())
            .to_string(),
    ));

    let token_value = env_token
        .map(|t| format!("{} (from env)", mask_token(&t)))
        .or_else(|| profile_creds.and_then(|p| p.token.as_ref().map(|t| mask_token(t))))
        .unwrap_or_else(|| "(not set)".to_string());
    values.push(("token".to_string(), token_value));

    Ok(values)
}

/// List all configured profile names with their hosts.
/// Merges profile names from both config and credentials files.
pub fn list_profiles() -> CliResult<Vec<(String, Option<String>)>> {
    let config = load_config()?;
    let credentials = load_credentials()?;

    let mut profile_names: std::collections::HashSet<String> = std::collections::HashSet::new();
    for name in config.profiles.keys() {
        profile_names.insert(name.clone());
    }
    for name in credentials.profiles.keys() {
        profile_names.insert(name.clone());
    }

    let mut profiles: Vec<(String, Option<String>)> = profile_names
        .into_iter()
        .map(|name| {
            let host = config.profiles.get(&name).and_then(|c| c.host.clone());
            (name, host)
        })
        .collect();
    profiles.sort_by(|a, b| a.0.cmp(&b.0));
    Ok(profiles)
}

/// Remove a profile from config and credentials.
pub fn remove_profile(profile: &str) -> CliResult<()> {
    if profile == "default" {
        return Err(CliError::InvalidConfig(
            "Cannot remove the default profile".to_string(),
        ));
    }

    let mut config = load_config()?;
    let mut credentials = load_credentials()?;

    let removed_config = config.profiles.remove(profile);
    let removed_creds = credentials.profiles.remove(profile);

    if removed_config.is_none() && removed_creds.is_none() {
        return Err(CliError::ProfileNotFound(
            profile.to_string(),
            config
                .profiles
                .keys()
                .cloned()
                .collect::<Vec<_>>()
                .join(", "),
        ));
    }

    save_config(&config)?;
    save_credentials(&credentials)?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mask_token() {
        assert_eq!(mask_token("short"), "*****");
        assert_eq!(mask_token("averylongtoken123"), "aver...n123");
    }

    #[test]
    fn test_default_config() {
        let config = Config::default();
        assert!(config.profiles.is_empty());
    }

    #[test]
    fn test_config_multi_profile_roundtrip() {
        let toml_str = r#"
[default]
host = "https://prod.example.com"
timeout = 120

[dev]
host = "https://dev.example.com"
timeout = 60
"#;
        let config: Config = toml::from_str(toml_str).unwrap();
        assert_eq!(
            config.profiles.get("default").unwrap().host.as_deref(),
            Some("https://prod.example.com")
        );
        assert_eq!(config.profiles.get("dev").unwrap().timeout, 60);

        let serialized = toml::to_string_pretty(&config).unwrap();
        let reparsed: Config = toml::from_str(&serialized).unwrap();
        assert_eq!(
            reparsed.profiles.get("default").unwrap().host,
            config.profiles.get("default").unwrap().host
        );
    }

    #[test]
    fn test_credentials_multi_profile_roundtrip() {
        let toml_str = r#"
[default]
token = "token-prod"

[dev]
token = "token-dev"
"#;
        let creds: Credentials = toml::from_str(toml_str).unwrap();
        assert_eq!(
            creds.profiles.get("default").unwrap().token.as_deref(),
            Some("token-prod")
        );
        assert_eq!(
            creds.profiles.get("dev").unwrap().token.as_deref(),
            Some("token-dev")
        );
    }
}
