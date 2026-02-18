//! Configuration management for Metadata AI CLI.
//!
//! Configuration is stored in `~/.metadata-ai/` with separate files for settings and credentials:
//! - `config.toml`: Host URL, timeout, and other settings
//! - `credentials`: Authentication token (separate for security)
//!
//! Environment variables take precedence over file configuration:
//! - `METADATA_HOST`: Server URL
//! - `METADATA_TOKEN`: JWT token

use crate::error::{CliError, CliResult};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

const CONFIG_DIR: &str = ".metadata-ai";
const CONFIG_FILE: &str = "config.toml";
const CREDENTIALS_FILE: &str = "credentials";

/// Main configuration structure.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Config {
    #[serde(default)]
    pub default: ProfileConfig,
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
    #[serde(default)]
    pub default: ProfileCredentials,
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
    pub fn load() -> CliResult<Self> {
        let env_host = std::env::var("METADATA_HOST").ok();
        let env_token = std::env::var("METADATA_TOKEN").ok();

        // Load file config
        let config = load_config().unwrap_or_default();
        let credentials = load_credentials().unwrap_or_default();

        // Resolve with priority
        let host = env_host
            .or(config.default.host.clone())
            .ok_or(CliError::ConfigNotFound)?;

        let token = env_token
            .or(credentials.default.token.clone())
            .ok_or(CliError::ConfigNotFound)?;

        let timeout = config.default.timeout;

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
pub fn get_config_value(key: &str) -> CliResult<Option<String>> {
    let config = load_config()?;
    let credentials = load_credentials()?;

    match key {
        "host" => Ok(config.default.host),
        "timeout" => Ok(Some(config.default.timeout.to_string())),
        "token" => Ok(credentials.default.token.map(|t| mask_token(&t))),
        _ => Err(CliError::InvalidConfig(format!("Unknown key: {key}"))),
    }
}

/// Set a specific configuration value.
pub fn set_config_value(key: &str, value: &str) -> CliResult<()> {
    match key {
        "host" => {
            let mut config = load_config()?;
            config.default.host = Some(value.to_string());
            save_config(&config)
        }
        "timeout" => {
            let timeout: u64 = value
                .parse()
                .map_err(|_| CliError::InvalidConfig("Timeout must be a number".to_string()))?;
            let mut config = load_config()?;
            config.default.timeout = timeout;
            save_config(&config)
        }
        "token" => {
            let mut credentials = load_credentials()?;
            credentials.default.token = Some(value.to_string());
            save_credentials(&credentials)
        }
        _ => Err(CliError::InvalidConfig(format!("Unknown key: {key}"))),
    }
}

/// Mask a token for display, showing only first/last 4 characters.
pub fn mask_token(token: &str) -> String {
    if token.len() <= 12 {
        return "*".repeat(token.len());
    }
    format!("{}...{}", &token[..4], &token[token.len() - 4..])
}

/// List all configuration values.
pub fn list_config() -> CliResult<Vec<(String, String)>> {
    let config = load_config()?;
    let credentials = load_credentials()?;

    let mut values = Vec::new();

    // Check environment variables
    let env_host = std::env::var("METADATA_HOST").ok();
    let env_token = std::env::var("METADATA_TOKEN").ok();

    // Host
    let host_value = env_host
        .map(|h| format!("{h} (from env)"))
        .or_else(|| config.default.host.clone())
        .unwrap_or_else(|| "(not set)".to_string());
    values.push(("host".to_string(), host_value));

    // Timeout
    values.push(("timeout".to_string(), config.default.timeout.to_string()));

    // Token
    let token_value = env_token
        .map(|t| format!("{} (from env)", mask_token(&t)))
        .or_else(|| credentials.default.token.map(|t| mask_token(&t)))
        .unwrap_or_else(|| "(not set)".to_string());
    values.push(("token".to_string(), token_value));

    Ok(values)
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
        assert!(config.default.host.is_none());
        assert_eq!(config.default.timeout, 120);
    }
}
