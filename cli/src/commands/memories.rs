//! Context Center memory management commands.

use crate::client::{
    AISdkClient, ContextMemory, CreateContextMemoryRequest, EntityReference, MemoryScope,
    MemorySearchResults, MemoryType, MemoryVisibility, ShareConfig, TagLabel,
};
use crate::config::ResolvedConfig;
use crate::error::{CliError, CliResult};
use clap::Subcommand;
use colored::Colorize;

/// Memory subcommands for `ai-sdk memories`.
#[derive(Subcommand)]
#[allow(clippy::large_enum_variant)]
pub enum MemoriesCommand {
    /// List Context Center memories
    List {
        /// Filter to memories attached to this primary-entity FQN
        #[arg(long = "entity-fqn")]
        entity_fqn: Option<String>,

        /// Maximum number of memories to return
        #[arg(short, long)]
        limit: Option<usize>,

        /// Output response as JSON
        #[arg(long)]
        json: bool,
    },

    /// Get a Context Center memory by ID
    Get {
        /// Memory ID (UUID)
        id: String,

        /// Output response as JSON
        #[arg(long)]
        json: bool,
    },

    /// Create a new Context Center memory
    Create {
        /// Stable system name for the memory (must be unique)
        #[arg(long)]
        name: String,

        /// Canonical question / instruction
        #[arg(long)]
        question: String,

        /// Canonical answer / retained guidance
        #[arg(long)]
        answer: String,

        /// Short title shown in the Context Center
        #[arg(long)]
        title: Option<String>,

        /// Optional markdown description
        #[arg(long)]
        description: Option<String>,

        /// Memory type (preference, useCase, note, runbook, faq)
        #[arg(long = "memory-type", default_value = "note")]
        memory_type: String,

        /// Memory scope (userGlobal, entityScoped)
        #[arg(long = "memory-scope", default_value = "entityScoped")]
        memory_scope: String,

        /// Visibility level (private, entity, shared)
        #[arg(long, default_value = "private")]
        visibility: String,

        /// ID of the primary entity this memory attaches to
        #[arg(long = "primary-entity-id")]
        primary_entity_id: Option<String>,

        /// Type of the primary entity (e.g. table, dashboard)
        #[arg(long = "primary-entity-type")]
        primary_entity_type: Option<String>,

        /// FQN of the primary entity
        #[arg(long = "primary-entity-fqn")]
        primary_entity_fqn: Option<String>,

        /// Comma-separated list of tag FQNs
        #[arg(long, value_delimiter = ',')]
        tags: Option<Vec<String>>,

        /// Output response as JSON
        #[arg(long)]
        json: bool,
    },

    /// Delete a Context Center memory by ID
    Delete {
        /// Memory ID (UUID)
        id: String,

        /// Hard delete (default is soft delete)
        #[arg(long)]
        hard: bool,
    },

    /// Hybrid NLQ search over Context Center memories
    Search {
        /// Natural-language query string
        query: String,

        /// Number of results to return (1-100)
        #[arg(long, default_value_t = 15)]
        size: usize,

        /// Pagination offset
        #[arg(long, default_value_t = 0)]
        from: usize,

        /// Output response as JSON
        #[arg(long)]
        json: bool,
    },
}

/// Dispatch for the `memories` subcommand.
pub async fn run(profile: &str, cmd: MemoriesCommand) -> CliResult<()> {
    let config = ResolvedConfig::load(profile)?;
    let client = AISdkClient::new(&config)?;

    match cmd {
        MemoriesCommand::List {
            entity_fqn,
            limit,
            json,
        } => run_list(&client, entity_fqn.as_deref(), limit, json).await,
        MemoriesCommand::Get { id, json } => run_get(&client, &id, json).await,
        MemoriesCommand::Create {
            name,
            question,
            answer,
            title,
            description,
            memory_type,
            memory_scope,
            visibility,
            primary_entity_id,
            primary_entity_type,
            primary_entity_fqn,
            tags,
            json,
        } => {
            run_create(
                &client,
                CreateArgs {
                    name,
                    question,
                    answer,
                    title,
                    description,
                    memory_type,
                    memory_scope,
                    visibility,
                    primary_entity_id,
                    primary_entity_type,
                    primary_entity_fqn,
                    tags,
                },
                json,
            )
            .await
        }
        MemoriesCommand::Delete { id, hard } => run_delete(&client, &id, hard).await,
        MemoriesCommand::Search {
            query,
            size,
            from,
            json,
        } => run_search(&client, &query, size, from, json).await,
    }
}

/// Internal struct grouping create arguments to keep the dispatcher signature small.
struct CreateArgs {
    name: String,
    question: String,
    answer: String,
    title: Option<String>,
    description: Option<String>,
    memory_type: String,
    memory_scope: String,
    visibility: String,
    primary_entity_id: Option<String>,
    primary_entity_type: Option<String>,
    primary_entity_fqn: Option<String>,
    tags: Option<Vec<String>>,
}

async fn run_list(
    client: &AISdkClient,
    entity_fqn: Option<&str>,
    limit: Option<usize>,
    json: bool,
) -> CliResult<()> {
    let memories = client.list_memories(entity_fqn, limit).await?;

    if json {
        println!(
            "{}",
            serde_json::to_string_pretty(&memories).unwrap_or_default()
        );
        return Ok(());
    }

    if memories.is_empty() {
        println!("No memories found.");
        return Ok(());
    }

    println!("{}", "Memories:".bold());
    println!();

    for memory in &memories {
        print_memory_summary(memory);
        println!();
    }

    Ok(())
}

async fn run_get(client: &AISdkClient, id: &str, json: bool) -> CliResult<()> {
    let memory = client.get_memory(id).await?;

    if json {
        println!(
            "{}",
            serde_json::to_string_pretty(&memory).unwrap_or_default()
        );
        return Ok(());
    }

    print_memory_detail(&memory);
    Ok(())
}

async fn run_create(client: &AISdkClient, args: CreateArgs, json: bool) -> CliResult<()> {
    let memory_type = MemoryType::from_cli_str(&args.memory_type)
        .map_err(|e| CliError::Other(format!("--memory-type: {e}")))?;
    let memory_scope = MemoryScope::from_cli_str(&args.memory_scope)
        .map_err(|e| CliError::Other(format!("--memory-scope: {e}")))?;
    let visibility = MemoryVisibility::from_cli_str(&args.visibility)
        .map_err(|e| CliError::Other(format!("--visibility: {e}")))?;

    let primary_entity = build_entity_reference(
        args.primary_entity_id,
        args.primary_entity_type,
        args.primary_entity_fqn,
    );

    let tags = args
        .tags
        .map(|ts| ts.into_iter().map(TagLabel::manual).collect::<Vec<_>>());

    let request = CreateContextMemoryRequest {
        name: args.name,
        question: args.question,
        answer: args.answer,
        title: args.title,
        description: args.description,
        memory_type,
        memory_scope,
        share_config: ShareConfig { visibility },
        primary_entity,
        related_entities: None,
        tags,
    };

    let memory = client.create_memory(&request).await?;

    if json {
        println!(
            "{}",
            serde_json::to_string_pretty(&memory).unwrap_or_default()
        );
        return Ok(());
    }

    println!(
        "{} Created memory: {}",
        "Success!".green().bold(),
        memory.name
    );
    println!("  {} {}", "ID:".cyan(), memory.id);
    if let Some(title) = &memory.title {
        println!("  {} {}", "Title:".cyan(), title);
    }
    println!("  {} {}", "Type:".cyan(), memory.memory_type.as_wire());
    println!("  {} {}", "Scope:".cyan(), memory.memory_scope.as_wire());
    println!("  {} {}", "Visibility:".cyan(), memory.visibility.as_wire());
    Ok(())
}

async fn run_delete(client: &AISdkClient, id: &str, hard: bool) -> CliResult<()> {
    client.delete_memory(id, hard).await?;
    let mode = if hard { "hard" } else { "soft" };
    println!(
        "{} Deleted memory {} ({} delete)",
        "Success!".green().bold(),
        id,
        mode
    );
    Ok(())
}

async fn run_search(
    client: &AISdkClient,
    query: &str,
    size: usize,
    from: usize,
    json: bool,
) -> CliResult<()> {
    let results: MemorySearchResults = client.search_memories(query, None, size, from).await?;

    if json {
        println!(
            "{}",
            serde_json::to_string_pretty(&results).unwrap_or_default()
        );
        return Ok(());
    }

    if results.hits.is_empty() {
        println!("No memories matched.");
        return Ok(());
    }

    println!(
        "{} {} {}",
        "Search Results:".bold(),
        results.hits.len(),
        format!("(of {} total)", results.total).dimmed()
    );
    println!();

    for hit in &results.hits {
        println!(
            "  {} {} {}",
            "*".cyan(),
            hit.memory
                .title
                .as_deref()
                .unwrap_or(&hit.memory.name)
                .bold(),
            format!("[score: {:.3}]", hit.score).dimmed()
        );
        println!("    Name: {}", hit.memory.name.dimmed());
        println!("    ID: {}", hit.memory.id.dimmed());
        if !hit.memory.question.is_empty() {
            let q = truncate_for_display(&hit.memory.question, 80);
            println!("    Q: {}", q.dimmed());
        }
        println!();
    }

    Ok(())
}

fn build_entity_reference(
    id: Option<String>,
    entity_type: Option<String>,
    fqn: Option<String>,
) -> Option<EntityReference> {
    if id.is_none() && entity_type.is_none() && fqn.is_none() {
        return None;
    }
    Some(EntityReference {
        id,
        name: None,
        entity_type,
        fully_qualified_name: fqn,
        display_name: None,
    })
}

fn print_memory_summary(memory: &ContextMemory) {
    let display = memory.title.as_deref().unwrap_or(&memory.name);
    println!("  {} {}", "*".cyan(), display.bold());
    println!("    Name: {}", memory.name.dimmed());
    println!("    ID: {}", memory.id.dimmed());
    println!(
        "    Type: {} | Scope: {} | Visibility: {}",
        memory.memory_type.as_wire().dimmed(),
        memory.memory_scope.as_wire().dimmed(),
        memory.visibility.as_wire().dimmed()
    );
    if !memory.question.is_empty() {
        let q = truncate_for_display(&memory.question, 80);
        println!("    Q: {}", q.dimmed());
    }
    if let Some(entity) = &memory.primary_entity {
        if let Some(fqn) = &entity.fully_qualified_name {
            println!("    Entity: {}", fqn.dimmed());
        }
    }
}

fn print_memory_detail(memory: &ContextMemory) {
    let display = memory.title.as_deref().unwrap_or(&memory.name);
    println!("{}", display.bold());
    println!();
    println!("  {} {}", "Name:".cyan(), memory.name);
    println!("  {} {}", "ID:".cyan(), memory.id);
    if let Some(fqn) = &memory.fully_qualified_name {
        println!("  {} {}", "FQN:".cyan(), fqn);
    }
    println!("  {} {}", "Type:".cyan(), memory.memory_type.as_wire());
    println!("  {} {}", "Scope:".cyan(), memory.memory_scope.as_wire());
    println!("  {} {}", "Visibility:".cyan(), memory.visibility.as_wire());
    if !memory.question.is_empty() {
        println!("  {}", "Question:".cyan());
        for line in memory.question.lines() {
            println!("    {line}");
        }
    }
    if !memory.answer.is_empty() {
        println!("  {}", "Answer:".cyan());
        for line in memory.answer.lines() {
            println!("    {line}");
        }
    }
    if let Some(summary) = &memory.summary {
        if !summary.is_empty() {
            println!("  {} {}", "Summary:".cyan(), summary);
        }
    }
    if let Some(entity) = &memory.primary_entity {
        let label = entity
            .fully_qualified_name
            .as_deref()
            .or(entity.name.as_deref())
            .unwrap_or("");
        if !label.is_empty() {
            println!("  {} {}", "Primary Entity:".cyan(), label);
        }
    }
    println!("  {} {}", "Usage Count:".cyan(), memory.usage_count);
    if let Some(ts) = memory.last_used_at {
        println!("  {} {}", "Last Used (epoch ms):".cyan(), ts);
    }
    if memory.deleted {
        println!("  {} {}", "Deleted:".cyan(), "yes".red());
    }
}

/// Truncate a string at character boundaries for display.
fn truncate_for_display(s: &str, max_chars: usize) -> String {
    if s.chars().count() <= max_chars {
        s.to_string()
    } else {
        let prefix: String = s.chars().take(max_chars.saturating_sub(3)).collect();
        format!("{prefix}...")
    }
}
