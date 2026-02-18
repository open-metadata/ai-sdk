//! Metadata AI CLI - Command-line tool for Metadata AI Agents.
//!
//! # Usage
//!
//! ```bash
//! # Configuration
//! metadata-ai configure              # Interactive setup
//! metadata-ai configure set host <url>
//! metadata-ai configure get host
//! metadata-ai configure list
//!
//! # Agent discovery
//! metadata-ai agents list            # List API-enabled agents
//! metadata-ai agents info <name>     # Get agent details
//!
//! # Invocation
//! metadata-ai invoke <agent>                       # Uses agent's default prompt
//! metadata-ai invoke <agent> "message"             # Custom message
//! metadata-ai invoke <agent> "message" --stream    # Streaming output
//! metadata-ai invoke <agent> "message" --json      # JSON output
//! metadata-ai invoke <agent> "message" -c <id>     # Continue conversation
//! ```

mod client;
mod commands;
mod config;
mod error;
mod streaming;
mod tui;

use clap::{Parser, Subcommand};

/// Metadata AI CLI - Interact with Metadata AI Agents from the command line.
#[derive(Parser)]
#[command(name = "metadata-ai")]
#[command(author = "OpenMetadata <support@open-metadata.org>")]
#[command(version)]
#[command(about = "Command-line tool for Metadata AI Agents", long_about = None)]
#[command(propagate_version = true)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Configure CLI settings and credentials
    Configure {
        #[command(subcommand)]
        action: Option<ConfigureAction>,
    },

    /// Discover and inspect agents
    Agents {
        #[command(subcommand)]
        action: AgentsAction,
    },

    /// Discover and inspect bots
    Bots {
        #[command(subcommand)]
        action: BotsAction,
    },

    /// Manage personas
    Personas {
        #[command(subcommand)]
        action: PersonasAction,
    },

    /// Manage abilities
    Abilities {
        #[command(subcommand)]
        action: AbilitiesAction,
    },

    /// Invoke an agent with a message
    Invoke {
        /// Name of the agent to invoke
        agent: String,

        /// Message to send to the agent (optional - uses agent's default prompt if omitted)
        message: Option<String>,

        /// Enable streaming output
        #[arg(short, long)]
        stream: bool,

        /// Output response as JSON
        #[arg(long)]
        json: bool,

        /// Continue an existing conversation
        #[arg(short = 'c', long = "conversation")]
        conversation_id: Option<String>,

        /// Show agent thinking/reasoning in grey (requires --stream)
        #[arg(short = 't', long)]
        thinking: bool,

        /// Show debug output for SSE parsing
        #[arg(long)]
        debug: bool,
    },

    /// Start an interactive chat session with an agent
    Chat {
        /// Name of the agent to chat with (optional - select from menu if omitted)
        agent: Option<String>,

        /// Continue an existing conversation
        #[arg(short = 'c', long = "conversation")]
        conversation_id: Option<String>,
    },
}

#[derive(Subcommand)]
enum ConfigureAction {
    /// Set a configuration value
    Set {
        /// Configuration key (host, token, timeout)
        key: String,
        /// Value to set
        value: String,
    },

    /// Get a configuration value
    Get {
        /// Configuration key to retrieve
        key: String,
    },

    /// List all configuration values
    List,
}

#[derive(Subcommand)]
enum AgentsAction {
    /// List all API-enabled agents
    List,

    /// Get detailed information about an agent
    Info {
        /// Name of the agent
        name: String,
    },

    /// Create a new dynamic agent (launches interactive wizard if no args provided)
    Create {
        /// Name of the agent (must be unique)
        #[arg(long)]
        name: Option<String>,

        /// Name of the persona to use
        #[arg(long)]
        persona: Option<String>,

        /// Description of the agent
        #[arg(long)]
        description: Option<String>,

        /// Display name for the agent
        #[arg(long)]
        display_name: Option<String>,

        /// Icon URL or emoji for the agent
        #[arg(long)]
        icon: Option<String>,

        /// Name of the bot to associate with this agent
        #[arg(long)]
        bot_name: Option<String>,

        /// Comma-separated list of abilities
        #[arg(long, value_delimiter = ',')]
        abilities: Option<Vec<String>>,

        /// Enable API access for this agent
        #[arg(long)]
        api_enabled: Option<bool>,

        /// AI provider to use
        #[arg(long)]
        provider: Option<String>,

        /// Output response as JSON
        #[arg(long)]
        json: bool,
    },
}

#[derive(Subcommand)]
enum BotsAction {
    /// List all bots
    List {
        /// Maximum number of bots to return
        #[arg(short, long)]
        limit: Option<u32>,

        /// Output response as JSON
        #[arg(long)]
        json: bool,
    },

    /// Get detailed information about a bot
    Get {
        /// Name of the bot
        name: String,

        /// Output response as JSON
        #[arg(long)]
        json: bool,
    },
}

#[derive(Subcommand)]
enum PersonasAction {
    /// List all personas
    List {
        /// Maximum number of personas to return
        #[arg(short, long)]
        limit: Option<u32>,

        /// Output response as JSON
        #[arg(long)]
        json: bool,
    },

    /// Get detailed information about a persona
    Get {
        /// Name of the persona
        name: String,

        /// Output response as JSON
        #[arg(long)]
        json: bool,
    },

    /// Create a new persona (launches interactive wizard if no args provided)
    Create {
        /// Name of the persona (must be unique)
        #[arg(long)]
        name: Option<String>,

        /// Description of the persona
        #[arg(long)]
        description: Option<String>,

        /// System prompt for the persona
        #[arg(long)]
        prompt: Option<String>,

        /// Display name for the persona
        #[arg(long)]
        display_name: Option<String>,

        /// AI provider to use
        #[arg(long)]
        provider: Option<String>,

        /// Output response as JSON
        #[arg(long)]
        json: bool,
    },
}

#[derive(Subcommand)]
enum AbilitiesAction {
    /// List all abilities
    List {
        /// Maximum number of abilities to return
        #[arg(short, long)]
        limit: Option<u32>,

        /// Output response as JSON
        #[arg(long)]
        json: bool,
    },

    /// Get detailed information about an ability
    Get {
        /// Name of the ability
        name: String,

        /// Output response as JSON
        #[arg(long)]
        json: bool,
    },
}

#[tokio::main]
async fn main() {
    let cli = Cli::parse();

    let result = match cli.command {
        Commands::Configure { action } => match action {
            Some(ConfigureAction::Set { key, value }) => commands::configure::run_set(&key, &value),
            Some(ConfigureAction::Get { key }) => commands::configure::run_get(&key),
            Some(ConfigureAction::List) => commands::configure::run_list(),
            None => commands::configure::run_interactive(),
        },

        Commands::Agents { action } => match action {
            AgentsAction::List => commands::agents::run_list().await,
            AgentsAction::Info { name } => commands::agents::run_info(&name).await,
            AgentsAction::Create {
                name,
                persona,
                description,
                display_name,
                icon,
                bot_name,
                abilities,
                api_enabled,
                provider,
                json,
            } => {
                // If all required args are provided, use CLI mode; otherwise launch TUI wizard
                match (name, description, persona) {
                    (Some(name), Some(description), Some(persona)) => {
                        commands::agents::run_create(
                            &name,
                            &description,
                            &persona,
                            "chat", // Hardcoded mode
                            display_name.as_deref(),
                            icon.as_deref(),
                            bot_name.as_deref(),
                            abilities,
                            api_enabled.or(Some(true)), // Default to true if not specified
                            provider.as_deref(),
                            json,
                        )
                        .await
                    }
                    _ => {
                        // Launch TUI wizard
                        tui::run_create_agent_tui().await
                    }
                }
            }
        },

        Commands::Bots { action } => match action {
            BotsAction::List { limit, json } => commands::bots::run_list(limit, json).await,
            BotsAction::Get { name, json } => commands::bots::run_get(&name, json).await,
        },

        Commands::Personas { action } => match action {
            PersonasAction::List { limit, json } => commands::personas::run_list(limit, json).await,
            PersonasAction::Get { name, json } => commands::personas::run_get(&name, json).await,
            PersonasAction::Create {
                name,
                description,
                prompt,
                display_name,
                provider,
                json,
            } => {
                // If all required args are provided, use CLI mode; otherwise launch TUI wizard
                match (name, description, prompt) {
                    (Some(name), Some(description), Some(prompt)) => {
                        commands::personas::run_create(
                            &name,
                            &description,
                            &prompt,
                            display_name.as_deref(),
                            provider.as_deref(),
                            json,
                        )
                        .await
                    }
                    _ => {
                        // Launch TUI wizard
                        tui::run_create_persona_tui().await
                    }
                }
            }
        },

        Commands::Abilities { action } => match action {
            AbilitiesAction::List { limit, json } => {
                commands::abilities::run_list(limit, json).await
            }
            AbilitiesAction::Get { name, json } => commands::abilities::run_get(&name, json).await,
        },

        Commands::Invoke {
            agent,
            message,
            stream,
            json,
            conversation_id,
            thinking,
            debug,
        } => {
            if stream || thinking {
                commands::invoke::run_stream(
                    &agent,
                    message.as_deref(),
                    conversation_id.as_deref(),
                    json,
                    thinking,
                    debug,
                )
                .await
            } else {
                commands::invoke::run_invoke(
                    &agent,
                    message.as_deref(),
                    conversation_id.as_deref(),
                    json,
                )
                .await
            }
        }

        Commands::Chat {
            agent,
            conversation_id,
        } => commands::chat::run_chat(agent.as_deref(), conversation_id.as_deref()).await,
    };

    if let Err(e) = result {
        eprintln!("{}", e.display());
        std::process::exit(1);
    }
}
