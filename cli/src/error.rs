//! Error types for the Metadata AI CLI.

use colored::Colorize;
use thiserror::Error;

/// CLI-specific error types with user-friendly messages.
#[derive(Error, Debug)]
pub enum CliError {
    #[error("Authentication failed. Run: metadata-ai configure")]
    AuthenticationFailed,

    #[error("Agent '{0}' is not API-enabled. Enable API access in the Metadata UI.")]
    AgentNotEnabled(String),

    #[error("Agent '{0}' not found. Run: metadata-ai agents list")]
    AgentNotFound(String),

    #[error("Rate limit exceeded. Please wait before retrying.")]
    RateLimitExceeded,

    #[error("Configuration not found. Run: metadata-ai configure")]
    ConfigNotFound,

    #[error("Invalid configuration: {0}")]
    InvalidConfig(String),

    #[error("Network error: {0}")]
    NetworkError(String),

    #[error("Server error ({0}): {1}")]
    ServerError(u16, String),

    #[error("Failed to parse response: {0}")]
    ParseError(String),

    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),

    #[allow(dead_code)]
    #[error("{0}")]
    Other(String),
}

impl CliError {
    /// Convert HTTP status codes to appropriate CLI errors.
    pub fn from_status(status: u16, body: &str, agent_name: Option<&str>) -> Self {
        match status {
            401 => CliError::AuthenticationFailed,
            403 => {
                if let Some(name) = agent_name {
                    CliError::AgentNotEnabled(name.to_string())
                } else {
                    CliError::AuthenticationFailed
                }
            }
            404 => {
                if let Some(name) = agent_name {
                    CliError::AgentNotFound(name.to_string())
                } else {
                    CliError::ServerError(404, "Resource not found".to_string())
                }
            }
            429 => CliError::RateLimitExceeded,
            _ => CliError::ServerError(status, body.to_string()),
        }
    }

    /// Format error message for display with color.
    pub fn display(&self) -> String {
        format!("{} {}", "Error:".red().bold(), self)
    }
}

/// Result type alias for CLI operations.
pub type CliResult<T> = Result<T, CliError>;
