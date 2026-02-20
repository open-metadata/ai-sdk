//! Error types for the AI SDK CLI.

use colored::Colorize;
use serde::Deserialize;
use thiserror::Error;

/// CLI-specific error types with user-friendly messages.
#[derive(Error, Debug)]
pub enum CliError {
    #[error("Authentication failed. Run: ai-sdk configure")]
    AuthenticationFailed,

    #[error("Agent '{0}' is not API-enabled. Enable API access in the OpenMetadata UI.")]
    AgentNotEnabled(String),

    #[error("Agent '{0}' not found. Run: ai-sdk agents list")]
    AgentNotFound(String),

    #[error("Rate limit exceeded. Please wait before retrying.")]
    RateLimitExceeded,

    #[error("Configuration not found. Run: ai-sdk configure")]
    ConfigNotFound,

    #[error("Invalid configuration: {0}")]
    InvalidConfig(String),

    #[error("Host not reachable: {0}\nCheck your network connection and verify the host URL with: ai-sdk configure")]
    HostNotReachable(String),

    #[error("Network error: {0}")]
    NetworkError(String),

    #[error(
        "Agents API not available at configured host. Check your host URL and ensure the server supports the Agents API."
    )]
    ApiNotAvailable,

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

/// Structure for parsing JSON error responses from the server.
#[derive(Debug, Deserialize)]
struct ErrorResponse {
    #[serde(default)]
    message: Option<String>,
    #[serde(default)]
    #[allow(dead_code)]
    code: Option<i32>,
}

impl CliError {
    /// Convert HTTP status codes to appropriate CLI errors.
    ///
    /// For 404 errors, attempts to parse the response body to distinguish between:
    /// - Generic "HTTP 404 Not Found" (API endpoint doesn't exist)
    /// - Specific resource not found (e.g., agent doesn't exist)
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
            404 => Self::handle_not_found(body, agent_name),
            429 => CliError::RateLimitExceeded,
            _ => CliError::ServerError(status, body.to_string()),
        }
    }

    /// Handle 404 responses by parsing the body to determine the error type.
    fn handle_not_found(body: &str, agent_name: Option<&str>) -> Self {
        // Try to parse as JSON error response
        if let Ok(error_response) = serde_json::from_str::<ErrorResponse>(body) {
            if let Some(message) = &error_response.message {
                // Generic "HTTP 404 Not Found" indicates the API endpoint doesn't exist
                if message.contains("HTTP 404") || message == "Not Found" {
                    return CliError::ApiNotAvailable;
                }
            }
        }

        // If we have an agent name and it's not a generic 404, it's likely agent not found
        if let Some(name) = agent_name {
            CliError::AgentNotFound(name.to_string())
        } else {
            // For endpoints like listing agents, a 404 means the API isn't available
            CliError::ApiNotAvailable
        }
    }

    /// Convert a reqwest error to the appropriate CLI error.
    ///
    /// Distinguishes between connection failures (host not reachable) and other network errors.
    pub fn from_reqwest(err: reqwest::Error) -> Self {
        let err_string = err.to_string();

        // Check for connection-related errors
        if err.is_connect()
            || err_string.contains("connection refused")
            || err_string.contains("Connection refused")
            || err_string.contains("tcp connect error")
            || err_string.contains("dns error")
            || err_string.contains("No such host")
        {
            // Extract the host from the URL if available
            let host = err
                .url()
                .map(|u| u.host_str().unwrap_or("unknown").to_string())
                .unwrap_or_else(|| "configured host".to_string());
            return CliError::HostNotReachable(host);
        }

        // Check for timeout errors
        if err.is_timeout() {
            return CliError::NetworkError("Request timed out".to_string());
        }

        CliError::NetworkError(err_string)
    }

    /// Format error message for display with color.
    pub fn display(&self) -> String {
        format!("{} {}", "Error:".red().bold(), self)
    }
}

/// Result type alias for CLI operations.
pub type CliResult<T> = Result<T, CliError>;
