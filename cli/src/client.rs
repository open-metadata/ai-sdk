//! HTTP client for AI SDK API.

use crate::config::ResolvedConfig;
use crate::error::{CliError, CliResult};
use reqwest::{Client, Response};
use serde::{Deserialize, Deserializer, Serialize};
use std::time::Duration;
use urlencoding::encode;

/// API response for agent listing.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentListResponse {
    pub data: Vec<AgentInfo>,
    #[serde(default)]
    pub paging: Option<Paging>,
}

/// Agent information.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AgentInfo {
    pub id: Option<String>,
    pub name: String,
    #[serde(default)]
    pub display_name: Option<String>,
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default)]
    pub abilities: Vec<AbilityRef>,
    #[serde(default)]
    pub api_enabled: bool,
    #[serde(default)]
    pub persona: Option<EntityReference>,
    #[serde(default)]
    pub mode: Option<String>,
    #[serde(default)]
    pub icon: Option<String>,
    #[serde(default)]
    pub bot: Option<EntityReference>,
    #[serde(default)]
    pub provider: Option<String>,
}

/// Generic entity reference used by the API.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct EntityReference {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
    #[serde(rename = "type", skip_serializing_if = "Option::is_none")]
    pub entity_type: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub fully_qualified_name: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub display_name: Option<String>,
}

/// Ability reference that can be either a string (from list) or an object (from create).
#[derive(Debug, Clone, Serialize)]
#[serde(untagged)]
pub enum AbilityRef {
    Name(String),
    Reference(EntityReference),
}

impl AbilityRef {
    /// Get the display name for this ability.
    pub fn display_name(&self) -> &str {
        match self {
            AbilityRef::Name(s) => s,
            AbilityRef::Reference(r) => r
                .display_name
                .as_ref()
                .or(r.name.as_ref())
                .map(|s| s.as_str())
                .unwrap_or("unknown"),
        }
    }
}

impl<'de> Deserialize<'de> for AbilityRef {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        use serde::de::{self, MapAccess, Visitor};

        struct AbilityRefVisitor;

        impl<'de> Visitor<'de> for AbilityRefVisitor {
            type Value = AbilityRef;

            fn expecting(&self, formatter: &mut std::fmt::Formatter) -> std::fmt::Result {
                formatter.write_str("a string or an object with id/name fields")
            }

            fn visit_str<E>(self, value: &str) -> Result<Self::Value, E>
            where
                E: de::Error,
            {
                Ok(AbilityRef::Name(value.to_string()))
            }

            fn visit_string<E>(self, value: String) -> Result<Self::Value, E>
            where
                E: de::Error,
            {
                Ok(AbilityRef::Name(value))
            }

            fn visit_map<M>(self, map: M) -> Result<Self::Value, M::Error>
            where
                M: MapAccess<'de>,
            {
                let entity_ref =
                    EntityReference::deserialize(de::value::MapAccessDeserializer::new(map))?;
                Ok(AbilityRef::Reference(entity_ref))
            }
        }

        deserializer.deserialize_any(AbilityRefVisitor)
    }
}

/// Pagination info from API responses.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct Paging {
    #[serde(default)]
    pub after: Option<String>,
    #[serde(default)]
    pub before: Option<String>,
    #[serde(default)]
    pub total: Option<u32>,
}

/// API response for bot listing.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BotListResponse {
    pub data: Vec<BotInfo>,
    #[serde(default)]
    pub paging: Option<Paging>,
}

/// Bot information.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BotInfo {
    pub id: Option<String>,
    pub name: String,
    #[serde(default)]
    pub display_name: Option<String>,
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default)]
    pub fully_qualified_name: Option<String>,
    #[serde(default)]
    pub bot_user: Option<EntityReference>,
}

/// API response for persona listing.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PersonaListResponse {
    pub data: Vec<PersonaInfo>,
    #[serde(default)]
    pub paging: Option<Paging>,
}

/// Persona information.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PersonaInfo {
    pub id: Option<String>,
    pub name: String,
    #[serde(default)]
    pub display_name: Option<String>,
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default)]
    pub prompt: Option<String>,
    #[serde(default)]
    pub provider: Option<String>,
    #[serde(default)]
    pub fully_qualified_name: Option<String>,
}

/// API response for ability listing.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AbilityListResponse {
    pub data: Vec<AbilityInfo>,
    #[serde(default)]
    pub paging: Option<Paging>,
}

/// Ability information.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AbilityInfo {
    pub id: Option<String>,
    pub name: String,
    #[serde(default)]
    pub display_name: Option<String>,
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default)]
    pub provider: Option<String>,
    #[serde(default)]
    pub fully_qualified_name: Option<String>,
    #[serde(default)]
    pub tools: Vec<String>,
}

/// Request to create a persona.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CreatePersonaRequest {
    pub name: String,
    pub description: String,
    pub prompt: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub display_name: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub provider: Option<String>,
}

/// Request to create an agent.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CreateAgentRequest {
    pub name: String,
    pub description: String,
    pub persona: EntityReference,
    pub mode: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub display_name: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub icon: Option<String>,
    #[serde(rename = "botName", skip_serializing_if = "Option::is_none")]
    pub bot_name: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub abilities: Option<Vec<EntityReference>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub api_enabled: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub provider: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub entity_status: Option<String>,
}

/// Request body for agent invocation.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct InvokeRequest {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub message: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub conversation_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub parameters: Option<serde_json::Value>,
}

/// Response from agent invocation.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct InvokeResponse {
    pub conversation_id: String,
    pub response: String,
    #[serde(default)]
    pub tools_used: Vec<String>,
    #[serde(default)]
    pub thinking_steps: Vec<String>,
    #[serde(default)]
    pub usage: Option<Usage>,
}

/// Token usage information.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Usage {
    #[serde(default)]
    pub prompt_tokens: u32,
    #[serde(default)]
    pub completion_tokens: u32,
    #[serde(default)]
    pub total_tokens: u32,
}

// ==================== Context Memory Types ====================

/// High-level type of a Context Center memory.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub enum MemoryType {
    #[serde(rename = "Preference")]
    Preference,
    #[serde(rename = "UseCase")]
    UseCase,
    #[serde(rename = "Note")]
    Note,
    #[serde(rename = "Runbook")]
    Runbook,
    #[serde(rename = "Faq")]
    Faq,
}

impl MemoryType {
    /// Parse from a CLI string (case-insensitive).
    pub fn from_cli_str(s: &str) -> Result<Self, String> {
        match s.to_ascii_lowercase().as_str() {
            "preference" => Ok(MemoryType::Preference),
            "usecase" | "use_case" | "use-case" => Ok(MemoryType::UseCase),
            "note" => Ok(MemoryType::Note),
            "runbook" => Ok(MemoryType::Runbook),
            "faq" => Ok(MemoryType::Faq),
            other => Err(format!(
                "invalid memory type '{other}' (expected one of: preference, useCase, note, runbook, faq)"
            )),
        }
    }

    /// Wire-format string value.
    pub fn as_wire(&self) -> &'static str {
        match self {
            MemoryType::Preference => "Preference",
            MemoryType::UseCase => "UseCase",
            MemoryType::Note => "Note",
            MemoryType::Runbook => "Runbook",
            MemoryType::Faq => "Faq",
        }
    }
}

/// Scope where a memory applies.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub enum MemoryScope {
    #[serde(rename = "UserGlobal")]
    UserGlobal,
    #[serde(rename = "EntityScoped")]
    EntityScoped,
}

impl MemoryScope {
    pub fn from_cli_str(s: &str) -> Result<Self, String> {
        match s.to_ascii_lowercase().as_str() {
            "userglobal" | "user_global" | "user-global" => Ok(MemoryScope::UserGlobal),
            "entityscoped" | "entity_scoped" | "entity-scoped" => Ok(MemoryScope::EntityScoped),
            other => Err(format!(
                "invalid memory scope '{other}' (expected: userGlobal, entityScoped)"
            )),
        }
    }

    pub fn as_wire(&self) -> &'static str {
        match self {
            MemoryScope::UserGlobal => "UserGlobal",
            MemoryScope::EntityScoped => "EntityScoped",
        }
    }
}

/// Visibility level for a memory.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub enum MemoryVisibility {
    #[serde(rename = "Private")]
    Private,
    #[serde(rename = "Entity")]
    Entity,
    #[serde(rename = "Shared")]
    Shared,
}

impl MemoryVisibility {
    pub fn from_cli_str(s: &str) -> Result<Self, String> {
        match s.to_ascii_lowercase().as_str() {
            "private" => Ok(MemoryVisibility::Private),
            "entity" => Ok(MemoryVisibility::Entity),
            "shared" => Ok(MemoryVisibility::Shared),
            other => Err(format!(
                "invalid visibility '{other}' (expected: private, entity, shared)"
            )),
        }
    }

    pub fn as_wire(&self) -> &'static str {
        match self {
            MemoryVisibility::Private => "Private",
            MemoryVisibility::Entity => "Entity",
            MemoryVisibility::Shared => "Shared",
        }
    }
}

/// Tag label wrapper used on the wire when creating a memory with tags.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct TagLabel {
    #[serde(rename = "tagFQN")]
    pub tag_fqn: String,
    pub label_type: String,
    pub state: String,
    pub source: String,
}

impl TagLabel {
    /// Wrap a tag FQN string in the wire format the API expects.
    pub fn manual(tag_fqn: impl Into<String>) -> Self {
        Self {
            tag_fqn: tag_fqn.into(),
            label_type: "Manual".to_string(),
            state: "Confirmed".to_string(),
            source: "Classification".to_string(),
        }
    }
}

/// Wire-format share configuration carried inside a create request.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ShareConfig {
    pub visibility: MemoryVisibility,
}

/// Request body for creating a Context Center memory.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CreateContextMemoryRequest {
    pub name: String,
    pub question: String,
    pub answer: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub title: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    pub memory_type: MemoryType,
    pub memory_scope: MemoryScope,
    pub share_config: ShareConfig,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub primary_entity: Option<EntityReference>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub related_entities: Option<Vec<EntityReference>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tags: Option<Vec<TagLabel>>,
}

/// A Context Center memory (response shape).
///
/// `visibility` is flattened from the server's `shareConfig.visibility`.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ContextMemory {
    pub id: String,
    pub name: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub fully_qualified_name: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub title: Option<String>,
    #[serde(default)]
    pub question: String,
    #[serde(default)]
    pub answer: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub summary: Option<String>,
    pub memory_type: MemoryType,
    pub memory_scope: MemoryScope,
    pub visibility: MemoryVisibility,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub primary_entity: Option<EntityReference>,
    #[serde(default)]
    pub usage_count: u64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub last_used_at: Option<i64>,
    #[serde(default)]
    pub deleted: bool,
}

impl<'de> Deserialize<'de> for ContextMemory {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        // Deserialize as a generic JSON value, then extract visibility from shareConfig.
        let mut value = serde_json::Value::deserialize(deserializer)?;

        // Extract visibility from shareConfig.visibility, defaulting to "Private".
        let visibility = value
            .get("shareConfig")
            .and_then(|sc| sc.get("visibility"))
            .and_then(|v| v.as_str())
            .unwrap_or("Private")
            .to_string();

        if let Some(obj) = value.as_object_mut() {
            obj.insert(
                "visibility".to_string(),
                serde_json::Value::String(visibility),
            );
        }

        // Helper struct that mirrors the public layout but is only used for parsing.
        #[derive(Deserialize)]
        #[serde(rename_all = "camelCase")]
        struct Raw {
            id: String,
            name: String,
            #[serde(default)]
            fully_qualified_name: Option<String>,
            #[serde(default)]
            title: Option<String>,
            #[serde(default)]
            question: String,
            #[serde(default)]
            answer: String,
            #[serde(default)]
            summary: Option<String>,
            #[serde(default = "default_memory_type")]
            memory_type: MemoryType,
            #[serde(default = "default_memory_scope")]
            memory_scope: MemoryScope,
            #[serde(default = "default_memory_visibility")]
            visibility: MemoryVisibility,
            #[serde(default)]
            primary_entity: Option<EntityReference>,
            #[serde(default)]
            usage_count: u64,
            #[serde(default)]
            last_used_at: Option<i64>,
            #[serde(default)]
            deleted: bool,
        }

        let raw: Raw = serde_json::from_value(value).map_err(serde::de::Error::custom)?;
        Ok(ContextMemory {
            id: raw.id,
            name: raw.name,
            fully_qualified_name: raw.fully_qualified_name,
            title: raw.title,
            question: raw.question,
            answer: raw.answer,
            summary: raw.summary,
            memory_type: raw.memory_type,
            memory_scope: raw.memory_scope,
            visibility: raw.visibility,
            primary_entity: raw.primary_entity,
            usage_count: raw.usage_count,
            last_used_at: raw.last_used_at,
            deleted: raw.deleted,
        })
    }
}

fn default_memory_type() -> MemoryType {
    MemoryType::Note
}

fn default_memory_scope() -> MemoryScope {
    MemoryScope::EntityScoped
}

fn default_memory_visibility() -> MemoryVisibility {
    MemoryVisibility::Private
}

/// Paginated list response for memories.
#[derive(Debug, Clone, Deserialize)]
struct MemoryListResponse {
    #[serde(default)]
    data: Vec<ContextMemory>,
    #[serde(default)]
    paging: Option<Paging>,
}

/// A single hit from a hybrid memory search.
#[derive(Debug, Clone, Serialize)]
pub struct MemorySearchHit {
    pub memory: ContextMemory,
    pub score: f64,
}

/// Results from a hybrid memory search.
#[derive(Debug, Clone, Serialize)]
pub struct MemorySearchResults {
    pub total: u64,
    pub hits: Vec<MemorySearchHit>,
}

impl MemorySearchResults {
    /// Parse from an OpenSearch-shaped response (`hits.total.value`, `hits.hits[]`).
    pub fn from_opensearch(value: &serde_json::Value) -> CliResult<Self> {
        let hits_block = value.get("hits");
        let total = hits_block
            .and_then(|h| h.get("total"))
            .map(|t| {
                if let Some(obj) = t.as_object() {
                    obj.get("value").and_then(|v| v.as_u64()).unwrap_or(0)
                } else {
                    t.as_u64().unwrap_or(0)
                }
            })
            .unwrap_or(0);

        let raw_hits = hits_block
            .and_then(|h| h.get("hits"))
            .and_then(|h| h.as_array())
            .cloned()
            .unwrap_or_default();

        let mut hits = Vec::with_capacity(raw_hits.len());
        for hit in raw_hits {
            let source = hit
                .get("_source")
                .cloned()
                .unwrap_or(serde_json::Value::Object(Default::default()));
            let memory: ContextMemory =
                serde_json::from_value(source).map_err(|e| CliError::ParseError(e.to_string()))?;
            let score = hit.get("_score").and_then(|s| s.as_f64()).unwrap_or(0.0);
            hits.push(MemorySearchHit { memory, score });
        }

        Ok(Self { total, hits })
    }
}

/// AI SDK API client.
///
/// Uses two underlying reqwest clients:
/// - `client`: standard HTTP requests, bounded by `config.timeout`.
/// - `streaming_client`: SSE endpoints, with no request timeout — agent runs
///   can take many minutes and the stream itself indicates progress.
#[derive(Clone)]
pub struct AISdkClient {
    client: Client,
    streaming_client: Client,
    base_url: String,
    token: String,
}

impl AISdkClient {
    /// Create a new client from resolved configuration.
    pub fn new(config: &ResolvedConfig) -> CliResult<Self> {
        let client = Client::builder()
            .timeout(Duration::from_secs(config.timeout))
            .build()
            .map_err(CliError::from_reqwest)?;

        // No `.timeout(...)` → reqwest waits indefinitely for the response
        // body, which is what we want for SSE: the server may take minutes
        // to finish a multi-step agent run, and the stream itself signals
        // liveness via thinking/message events.
        let streaming_client = Client::builder().build().map_err(CliError::from_reqwest)?;

        // Normalize base URL (remove trailing slash)
        let base_url = config.host.trim_end_matches('/').to_string();

        Ok(Self {
            client,
            streaming_client,
            base_url,
            token: config.token.clone(),
        })
    }

    /// Get the base URL for dynamic agent endpoints.
    fn agents_url(&self, path: &str) -> String {
        format!("{}/api/v1/agents/dynamic{}", self.base_url, path)
    }

    /// Add authorization header to request.
    fn auth_header(&self) -> String {
        format!("Bearer {}", self.token)
    }

    /// Handle HTTP response, converting errors to CLI errors.
    async fn handle_response(
        &self,
        response: Response,
        agent_name: Option<&str>,
    ) -> CliResult<String> {
        let status = response.status().as_u16();

        if (200..300).contains(&status) {
            response.text().await.map_err(CliError::from_reqwest)
        } else {
            let body = response.text().await.unwrap_or_default();
            Err(CliError::from_status(status, &body, agent_name))
        }
    }

    /// List all API-enabled agents.
    /// Automatically paginates through all results.
    pub async fn list_agents(&self) -> CliResult<Vec<AgentInfo>> {
        self.list_agents_with_limit(None).await
    }

    /// List API-enabled agents with optional limit.
    /// Automatically paginates through all results.
    pub async fn list_agents_with_limit(&self, limit: Option<u32>) -> CliResult<Vec<AgentInfo>> {
        const PAGE_SIZE: u32 = 100;
        let mut results = Vec::new();
        let mut after: Option<String> = None;

        loop {
            let url = match &after {
                Some(cursor) => self.agents_url(&format!(
                    "?apiEnabled=true&limit={PAGE_SIZE}&after={cursor}"
                )),
                None => self.agents_url(&format!("?apiEnabled=true&limit={PAGE_SIZE}")),
            };

            let response = self
                .client
                .get(&url)
                .header("Authorization", self.auth_header())
                .send()
                .await
                .map_err(CliError::from_reqwest)?;

            let body = self.handle_response(response, None).await?;

            let list: AgentListResponse =
                serde_json::from_str(&body).map_err(|e| CliError::ParseError(e.to_string()))?;

            results.extend(list.data);

            // Check if we've hit the requested limit
            if let Some(max) = limit {
                if results.len() >= max as usize {
                    results.truncate(max as usize);
                    return Ok(results);
                }
            }

            // Check for more pages
            after = list.paging.and_then(|p| p.after);
            if after.is_none() {
                break;
            }
        }

        Ok(results)
    }

    /// Get agent information by name.
    /// Note: This endpoint returns minimal info; use `get_dynamic_agent` for full details.
    pub async fn get_agent(&self, name: &str) -> CliResult<AgentInfo> {
        let encoded_name = encode(name);
        let response = self
            .client
            .get(self.agents_url(&format!("/name/{encoded_name}")))
            .header("Authorization", self.auth_header())
            .send()
            .await
            .map_err(CliError::from_reqwest)?;

        let body = self.handle_response(response, Some(name)).await?;

        serde_json::from_str(&body).map_err(|e| CliError::ParseError(e.to_string()))
    }

    /// Invoke an agent synchronously.
    pub async fn invoke(
        &self,
        agent_name: &str,
        message: Option<&str>,
        conversation_id: Option<&str>,
    ) -> CliResult<InvokeResponse> {
        let encoded_name = encode(agent_name);
        let request = InvokeRequest {
            message: message.map(String::from),
            conversation_id: conversation_id.map(String::from),
            parameters: None,
        };

        let response = self
            .client
            .post(self.agents_url(&format!("/name/{encoded_name}/invoke")))
            .header("Authorization", self.auth_header())
            .header("Content-Type", "application/json")
            .json(&request)
            .send()
            .await
            .map_err(CliError::from_reqwest)?;

        let body = self.handle_response(response, Some(agent_name)).await?;

        serde_json::from_str(&body).map_err(|e| CliError::ParseError(e.to_string()))
    }

    /// Create a new chat conversation for the default agent (PLANNER).
    /// Returns the conversation ID.
    /// The title is truncated to 50 characters to match the chat UI behaviour.
    pub async fn create_chat_conversation(&self, title: &str) -> CliResult<String> {
        let truncated: String = title.chars().take(50).collect();
        let url = format!("{}/api/v1/assistants/chatConversations", self.base_url);
        let body = serde_json::json!({ "title": truncated });

        let response = self
            .client
            .post(&url)
            .header("Authorization", self.auth_header())
            .header("Content-Type", "application/json")
            .json(&body)
            .send()
            .await
            .map_err(CliError::from_reqwest)?;

        let status = response.status().as_u16();
        if !(200..300).contains(&status) {
            let body = response.text().await.unwrap_or_default();
            return Err(CliError::from_status(status, &body, None));
        }

        let json: serde_json::Value = response.json().await.map_err(|e| {
            CliError::ParseError(format!("Failed to parse conversation response: {e}"))
        })?;

        json["id"]
            .as_str()
            .map(|s| s.to_string())
            .ok_or_else(|| CliError::ParseError("Conversation response missing 'id' field".into()))
    }

    /// Synchronously invoke the platform's default agent (PLANNER / CHAT_MODE).
    /// Auto-creates a chat conversation when no conversation ID is supplied.
    pub async fn invoke_default_agent(
        &self,
        message: &str,
        conversation_id: Option<&str>,
    ) -> CliResult<InvokeResponse> {
        let cid = match conversation_id {
            Some(c) => c.to_string(),
            None => self.create_chat_conversation(message).await?,
        };

        let url = format!("{}/api/v1/agents/invoke", self.base_url);
        let body = serde_json::json!({
            "message": message,
            "conversationId": cid,
            "agentType": "PLANNER",
            "agentMode": "CHAT_MODE",
        });

        let response = self
            .client
            .post(&url)
            .header("Authorization", self.auth_header())
            .header("Content-Type", "application/json")
            .json(&body)
            .send()
            .await
            .map_err(CliError::from_reqwest)?;

        let body_str = self.handle_response(response, None).await?;
        serde_json::from_str(&body_str).map_err(|e| CliError::ParseError(e.to_string()))
    }

    /// Stream a response from the platform's default agent (PLANNER / CHAT_MODE).
    /// Auto-creates a chat conversation when no conversation ID is supplied.
    pub async fn stream_default_agent(
        &self,
        message: &str,
        conversation_id: Option<&str>,
    ) -> CliResult<Response> {
        let cid = match conversation_id {
            Some(c) => c.to_string(),
            None => self.create_chat_conversation(message).await?,
        };

        let url = format!("{}/api/v1/agents/run", self.base_url);
        let body = serde_json::json!({
            "message": message,
            "conversationId": cid,
            "agentType": "PLANNER",
            "agentMode": "CHAT_MODE",
        });

        let response = self
            .streaming_client
            .post(&url)
            .header("Authorization", self.auth_header())
            .header("Content-Type", "application/json")
            .header("Accept", "text/event-stream")
            .json(&body)
            .send()
            .await
            .map_err(CliError::from_reqwest)?;

        let status = response.status().as_u16();
        if (200..300).contains(&status) {
            Ok(response)
        } else {
            let body = response.text().await.unwrap_or_default();
            Err(CliError::from_status(status, &body, None))
        }
    }

    /// Get a streaming response from an agent.
    /// Returns the raw response for SSE processing.
    pub async fn stream(
        &self,
        agent_name: &str,
        message: Option<&str>,
        conversation_id: Option<&str>,
    ) -> CliResult<Response> {
        let encoded_name = encode(agent_name);
        let request = InvokeRequest {
            message: message.map(String::from),
            conversation_id: conversation_id.map(String::from),
            parameters: None,
        };

        let response = self
            .streaming_client
            .post(self.agents_url(&format!("/name/{encoded_name}/stream")))
            .header("Authorization", self.auth_header())
            .header("Content-Type", "application/json")
            .header("Accept", "text/event-stream")
            .json(&request)
            .send()
            .await
            .map_err(CliError::from_reqwest)?;

        let status = response.status().as_u16();
        if (200..300).contains(&status) {
            Ok(response)
        } else {
            let body = response.text().await.unwrap_or_default();
            Err(CliError::from_status(status, &body, Some(agent_name)))
        }
    }

    // ==================== Bot Operations ====================

    /// Get the base URL for bot endpoints.
    fn bots_url(&self, path: &str) -> String {
        format!("{}/api/v1/bots{}", self.base_url, path)
    }

    /// List all bots.
    /// Automatically paginates through all results.
    pub async fn list_bots(&self) -> CliResult<Vec<BotInfo>> {
        self.list_bots_with_limit(None).await
    }

    /// List bots with optional limit.
    /// Automatically paginates through all results.
    pub async fn list_bots_with_limit(&self, limit: Option<u32>) -> CliResult<Vec<BotInfo>> {
        const PAGE_SIZE: u32 = 100;
        let mut results = Vec::new();
        let mut after: Option<String> = None;

        loop {
            let url = match &after {
                Some(cursor) => self.bots_url(&format!("?limit={PAGE_SIZE}&after={cursor}")),
                None => self.bots_url(&format!("?limit={PAGE_SIZE}")),
            };

            let response = self
                .client
                .get(&url)
                .header("Authorization", self.auth_header())
                .send()
                .await
                .map_err(CliError::from_reqwest)?;

            let body = self.handle_response(response, None).await?;

            let list: BotListResponse =
                serde_json::from_str(&body).map_err(|e| CliError::ParseError(e.to_string()))?;

            results.extend(list.data);

            // Check if we've hit the requested limit
            if let Some(max) = limit {
                if results.len() >= max as usize {
                    results.truncate(max as usize);
                    return Ok(results);
                }
            }

            // Check for more pages
            after = list.paging.and_then(|p| p.after);
            if after.is_none() {
                break;
            }
        }

        Ok(results)
    }

    /// Get bot information by name.
    pub async fn get_bot(&self, name: &str) -> CliResult<BotInfo> {
        let encoded_name = encode(name);
        let response = self
            .client
            .get(self.bots_url(&format!("/name/{encoded_name}")))
            .header("Authorization", self.auth_header())
            .send()
            .await
            .map_err(CliError::from_reqwest)?;

        let body = self.handle_response(response, None).await?;

        serde_json::from_str(&body).map_err(|e| CliError::ParseError(e.to_string()))
    }

    // ==================== Persona Operations ====================

    /// Get the base URL for persona endpoints.
    fn personas_url(&self, path: &str) -> String {
        format!("{}/api/v1/agents/personas{}", self.base_url, path)
    }

    /// Get the base URL for ability endpoints.
    fn abilities_url(&self, path: &str) -> String {
        format!("{}/api/v1/agents/abilities{}", self.base_url, path)
    }

    /// List all personas.
    /// Automatically paginates through all results.
    pub async fn list_personas(&self) -> CliResult<Vec<PersonaInfo>> {
        self.list_personas_with_limit(None).await
    }

    /// List personas with optional limit.
    /// Automatically paginates through all results.
    pub async fn list_personas_with_limit(
        &self,
        limit: Option<u32>,
    ) -> CliResult<Vec<PersonaInfo>> {
        const PAGE_SIZE: u32 = 100;
        let mut results = Vec::new();
        let mut after: Option<String> = None;

        loop {
            let url = match &after {
                Some(cursor) => self.personas_url(&format!("?limit={PAGE_SIZE}&after={cursor}")),
                None => self.personas_url(&format!("?limit={PAGE_SIZE}")),
            };

            let response = self
                .client
                .get(&url)
                .header("Authorization", self.auth_header())
                .send()
                .await
                .map_err(CliError::from_reqwest)?;

            let body = self.handle_response(response, None).await?;

            let list: PersonaListResponse =
                serde_json::from_str(&body).map_err(|e| CliError::ParseError(e.to_string()))?;

            results.extend(list.data);

            // Check if we've hit the requested limit
            if let Some(max) = limit {
                if results.len() >= max as usize {
                    results.truncate(max as usize);
                    return Ok(results);
                }
            }

            // Check for more pages
            after = list.paging.and_then(|p| p.after);
            if after.is_none() {
                break;
            }
        }

        Ok(results)
    }

    /// Get persona information by name.
    pub async fn get_persona(&self, name: &str) -> CliResult<PersonaInfo> {
        let encoded_name = encode(name);
        let response = self
            .client
            .get(self.personas_url(&format!("/name/{encoded_name}")))
            .header("Authorization", self.auth_header())
            .send()
            .await
            .map_err(CliError::from_reqwest)?;

        let body = self.handle_response(response, None).await?;

        serde_json::from_str(&body).map_err(|e| CliError::ParseError(e.to_string()))
    }

    /// Create a new persona.
    pub async fn create_persona(&self, request: CreatePersonaRequest) -> CliResult<PersonaInfo> {
        let response = self
            .client
            .post(self.personas_url(""))
            .header("Authorization", self.auth_header())
            .header("Content-Type", "application/json")
            .json(&request)
            .send()
            .await
            .map_err(CliError::from_reqwest)?;

        let body = self.handle_response(response, None).await?;

        serde_json::from_str(&body).map_err(|e| CliError::ParseError(e.to_string()))
    }

    // ==================== Ability Operations ====================

    /// List all abilities.
    /// Automatically paginates through all results.
    pub async fn list_abilities(&self) -> CliResult<Vec<AbilityInfo>> {
        self.list_abilities_with_limit(None).await
    }

    /// List abilities with optional limit.
    /// Automatically paginates through all results.
    pub async fn list_abilities_with_limit(
        &self,
        limit: Option<u32>,
    ) -> CliResult<Vec<AbilityInfo>> {
        const PAGE_SIZE: u32 = 100;
        let mut results = Vec::new();
        let mut after: Option<String> = None;

        loop {
            let url = match &after {
                Some(cursor) => self.abilities_url(&format!("?limit={PAGE_SIZE}&after={cursor}")),
                None => self.abilities_url(&format!("?limit={PAGE_SIZE}")),
            };

            let response = self
                .client
                .get(&url)
                .header("Authorization", self.auth_header())
                .send()
                .await
                .map_err(CliError::from_reqwest)?;

            let body = self.handle_response(response, None).await?;

            let list: AbilityListResponse =
                serde_json::from_str(&body).map_err(|e| CliError::ParseError(e.to_string()))?;

            results.extend(list.data);

            // Check if we've hit the requested limit
            if let Some(max) = limit {
                if results.len() >= max as usize {
                    results.truncate(max as usize);
                    return Ok(results);
                }
            }

            // Check for more pages
            after = list.paging.and_then(|p| p.after);
            if after.is_none() {
                break;
            }
        }

        Ok(results)
    }

    /// Get ability information by name.
    pub async fn get_ability(&self, name: &str) -> CliResult<AbilityInfo> {
        let encoded_name = encode(name);
        let response = self
            .client
            .get(self.abilities_url(&format!("/name/{encoded_name}")))
            .header("Authorization", self.auth_header())
            .send()
            .await
            .map_err(CliError::from_reqwest)?;

        let body = self.handle_response(response, None).await?;

        serde_json::from_str(&body).map_err(|e| CliError::ParseError(e.to_string()))
    }

    // ==================== Agent Operations ====================

    /// Get full agent details from the dynamic agents endpoint (includes persona, abilities).
    pub async fn get_dynamic_agent(&self, name: &str) -> CliResult<AgentInfo> {
        let encoded_name = encode(name);
        let response = self
            .client
            .get(self.agents_url(&format!(
                "/name/{encoded_name}?fields=persona,bot,abilities"
            )))
            .header("Authorization", self.auth_header())
            .send()
            .await
            .map_err(CliError::from_reqwest)?;

        let body = self.handle_response(response, Some(name)).await?;

        serde_json::from_str(&body).map_err(|e| CliError::ParseError(e.to_string()))
    }

    /// Create a new dynamic agent.
    pub async fn create_agent(&self, request: CreateAgentRequest) -> CliResult<AgentInfo> {
        let response = self
            .client
            .post(self.agents_url(""))
            .header("Authorization", self.auth_header())
            .header("Content-Type", "application/json")
            .json(&request)
            .send()
            .await
            .map_err(CliError::from_reqwest)?;

        let body = self.handle_response(response, None).await?;

        serde_json::from_str(&body).map_err(|e| CliError::ParseError(e.to_string()))
    }

    // ==================== Context Memory Operations ====================

    /// Base URL for the Context Center memories endpoints.
    fn memories_url(&self, path: &str) -> String {
        format!("{}/api/v1/contextCenter/memories{}", self.base_url, path)
    }

    /// List Context Center memories, paginating through all results.
    ///
    /// `primary_entity_fqn` filters to memories attached to a given entity FQN.
    /// `limit` caps the total number returned; `None` returns everything.
    pub async fn list_memories(
        &self,
        primary_entity_fqn: Option<&str>,
        limit: Option<usize>,
    ) -> CliResult<Vec<ContextMemory>> {
        const PAGE_SIZE: usize = 100;
        let mut results = Vec::new();
        let mut after: Option<String> = None;

        loop {
            let mut query = format!("?limit={PAGE_SIZE}");
            if let Some(fqn) = primary_entity_fqn {
                query.push_str(&format!("&primaryEntityFqn={}", encode(fqn)));
            }
            if let Some(cursor) = &after {
                query.push_str(&format!("&after={}", encode(cursor)));
            }

            let response = self
                .client
                .get(self.memories_url(&query))
                .header("Authorization", self.auth_header())
                .send()
                .await
                .map_err(CliError::from_reqwest)?;

            let body = self.handle_response(response, None).await?;
            let list: MemoryListResponse =
                serde_json::from_str(&body).map_err(|e| CliError::ParseError(e.to_string()))?;

            results.extend(list.data);

            if let Some(max) = limit {
                if results.len() >= max {
                    results.truncate(max);
                    return Ok(results);
                }
            }

            after = list.paging.and_then(|p| p.after);
            if after.is_none() {
                break;
            }
        }

        Ok(results)
    }

    /// Get a Context Center memory by ID.
    pub async fn get_memory(&self, id: &str) -> CliResult<ContextMemory> {
        let encoded_id = encode(id);
        let response = self
            .client
            .get(self.memories_url(&format!("/{encoded_id}")))
            .header("Authorization", self.auth_header())
            .send()
            .await
            .map_err(CliError::from_reqwest)?;

        let body = self.handle_response(response, None).await?;
        serde_json::from_str(&body).map_err(|e| CliError::ParseError(e.to_string()))
    }

    /// Create a Context Center memory.
    pub async fn create_memory(
        &self,
        request: &CreateContextMemoryRequest,
    ) -> CliResult<ContextMemory> {
        let response = self
            .client
            .post(self.memories_url(""))
            .header("Authorization", self.auth_header())
            .header("Content-Type", "application/json")
            .json(request)
            .send()
            .await
            .map_err(CliError::from_reqwest)?;

        let body = self.handle_response(response, None).await?;
        serde_json::from_str(&body).map_err(|e| CliError::ParseError(e.to_string()))
    }

    /// Delete a Context Center memory by ID. Soft-delete by default.
    pub async fn delete_memory(&self, id: &str, hard: bool) -> CliResult<()> {
        let encoded_id = encode(id);
        let response = self
            .client
            .delete(self.memories_url(&format!("/{encoded_id}?hardDelete={hard}")))
            .header("Authorization", self.auth_header())
            .send()
            .await
            .map_err(CliError::from_reqwest)?;

        let status = response.status().as_u16();
        if (200..300).contains(&status) {
            Ok(())
        } else {
            let body = response.text().await.unwrap_or_default();
            Err(CliError::from_status(status, &body, None))
        }
    }

    /// Hybrid NLQ search over the `contextMemory` index.
    ///
    /// `filters` is a JSON object mapping field name -> list of values; it is
    /// serialized and passed as the `filters` query parameter.
    pub async fn search_memories(
        &self,
        q: &str,
        filters: Option<&serde_json::Value>,
        size: usize,
        from: usize,
    ) -> CliResult<MemorySearchResults> {
        let mut url = format!(
            "{}/api/v1/hybrid/nlq/search?index=contextMemory&q={}&size={size}&from={from}",
            self.base_url,
            encode(q),
        );
        if let Some(f) = filters {
            let json = serde_json::to_string(f)
                .map_err(|e| CliError::ParseError(format!("invalid filters JSON: {e}")))?;
            url.push_str(&format!("&filters={}", encode(&json)));
        }

        let response = self
            .client
            .get(&url)
            .header("Authorization", self.auth_header())
            .send()
            .await
            .map_err(CliError::from_reqwest)?;

        let body = self.handle_response(response, None).await?;
        let value: serde_json::Value =
            serde_json::from_str(&body).map_err(|e| CliError::ParseError(e.to_string()))?;
        MemorySearchResults::from_opensearch(&value)
    }
}

// ==================== Tests ====================

#[cfg(test)]
mod default_agent_tests {
    use super::*;
    use serde_json::json;
    use wiremock::matchers::{method, path};
    use wiremock::{Mock, MockServer, ResponseTemplate};

    /// Build a test client that points at `base_url` with the given token.
    fn make_client(base_url: &str, token: &str) -> AISdkClient {
        let config = ResolvedConfig {
            host: base_url.to_string(),
            token: token.to_string(),
            timeout: 30,
        };
        AISdkClient::new(&config).expect("failed to build test client")
    }

    #[tokio::test]
    async fn create_chat_conversation_returns_id() {
        let server = MockServer::start().await;

        Mock::given(method("POST"))
            .and(path("/api/v1/assistants/chatConversations"))
            .respond_with(
                ResponseTemplate::new(200)
                    .set_body_json(json!({ "id": "aaaabbbb-1111-2222-3333-ccccddddeeee" })),
            )
            .mount(&server)
            .await;

        let client = make_client(&server.uri(), "test-token");
        let id = client
            .create_chat_conversation("Hello world")
            .await
            .unwrap();
        assert_eq!(id, "aaaabbbb-1111-2222-3333-ccccddddeeee");
    }

    #[tokio::test]
    async fn invoke_default_agent_creates_conversation_then_calls_invoke() {
        let server = MockServer::start().await;

        Mock::given(method("POST"))
            .and(path("/api/v1/assistants/chatConversations"))
            .respond_with(
                ResponseTemplate::new(200)
                    .set_body_json(json!({ "id": "11111111-1111-1111-1111-111111111111" })),
            )
            .mount(&server)
            .await;

        Mock::given(method("POST"))
            .and(path("/api/v1/agents/invoke"))
            .respond_with(ResponseTemplate::new(200).set_body_json(json!({
                "conversationId": "11111111-1111-1111-1111-111111111111",
                "response": "Hello from the default agent"
            })))
            .mount(&server)
            .await;

        let client = make_client(&server.uri(), "test-token");
        let resp = client.invoke_default_agent("Say hi", None).await.unwrap();
        assert_eq!(resp.conversation_id, "11111111-1111-1111-1111-111111111111");
        assert_eq!(resp.response, "Hello from the default agent");
    }

    #[tokio::test]
    async fn invoke_default_agent_reuses_supplied_conversation_id() {
        let server = MockServer::start().await;

        // Conversation creation must NOT be called when an ID is already supplied.
        Mock::given(method("POST"))
            .and(path("/api/v1/assistants/chatConversations"))
            .respond_with(ResponseTemplate::new(500))
            .mount(&server)
            .await;

        Mock::given(method("POST"))
            .and(path("/api/v1/agents/invoke"))
            .respond_with(ResponseTemplate::new(200).set_body_json(json!({
                "conversationId": "existing-conv-id",
                "response": "Reused conversation"
            })))
            .mount(&server)
            .await;

        let client = make_client(&server.uri(), "test-token");
        // Supplying an existing conversation ID means no call to chatConversations.
        let resp = client
            .invoke_default_agent("Follow up", Some("existing-conv-id"))
            .await
            .unwrap();
        assert_eq!(resp.conversation_id, "existing-conv-id");
    }

    #[tokio::test]
    async fn invoke_default_agent_surfaces_thinking_steps() {
        let server = MockServer::start().await;

        Mock::given(method("POST"))
            .and(path("/api/v1/assistants/chatConversations"))
            .respond_with(
                ResponseTemplate::new(200)
                    .set_body_json(json!({ "id": "55555555-5555-5555-5555-555555555555" })),
            )
            .mount(&server)
            .await;

        Mock::given(method("POST"))
            .and(path("/api/v1/agents/invoke"))
            .respond_with(ResponseTemplate::new(200).set_body_json(json!({
                "conversationId": "55555555-5555-5555-5555-555555555555",
                "response": "Found it.",
                "thinkingSteps": ["Exploring assets...", "Synthesizing answer..."]
            })))
            .mount(&server)
            .await;

        let client = make_client(&server.uri(), "test-token");
        let resp = client.invoke_default_agent("question", None).await.unwrap();
        assert_eq!(resp.response, "Found it.");
        assert_eq!(
            resp.thinking_steps,
            vec!["Exploring assets...", "Synthesizing answer..."]
        );
    }

    #[tokio::test]
    async fn invoke_default_agent_defaults_thinking_steps_to_empty() {
        let server = MockServer::start().await;

        Mock::given(method("POST"))
            .and(path("/api/v1/assistants/chatConversations"))
            .respond_with(
                ResponseTemplate::new(200)
                    .set_body_json(json!({ "id": "11111111-1111-1111-1111-111111111111" })),
            )
            .mount(&server)
            .await;

        Mock::given(method("POST"))
            .and(path("/api/v1/agents/invoke"))
            .respond_with(ResponseTemplate::new(200).set_body_json(json!({
                "conversationId": "11111111-1111-1111-1111-111111111111",
                "response": "Hello from the default agent"
            })))
            .mount(&server)
            .await;

        let client = make_client(&server.uri(), "test-token");
        let resp = client.invoke_default_agent("Say hi", None).await.unwrap();
        assert!(resp.thinking_steps.is_empty());
    }

    #[tokio::test]
    async fn stream_default_agent_creates_conversation_then_calls_run() {
        let server = MockServer::start().await;

        Mock::given(method("POST"))
            .and(path("/api/v1/assistants/chatConversations"))
            .respond_with(
                ResponseTemplate::new(200).set_body_json(json!({ "id": "stream-conv-id" })),
            )
            .mount(&server)
            .await;

        Mock::given(method("POST"))
            .and(path("/api/v1/agents/run"))
            .respond_with(ResponseTemplate::new(200).set_body_string("data: done\n\n"))
            .mount(&server)
            .await;

        let client = make_client(&server.uri(), "test-token");
        let response = client.stream_default_agent("Stream me", None).await;
        // We just need a successful HTTP response back — SSE parsing is tested elsewhere.
        assert!(response.is_ok());
    }
}

#[cfg(test)]
mod memory_tests {
    use super::*;
    use serde_json::json;
    use wiremock::matchers::{method, path, query_param};
    use wiremock::{Mock, MockServer, ResponseTemplate};

    fn make_client(base_url: &str, token: &str) -> AISdkClient {
        let config = ResolvedConfig {
            host: base_url.to_string(),
            token: token.to_string(),
            timeout: 30,
        };
        AISdkClient::new(&config).expect("failed to build test client")
    }

    #[test]
    fn context_memory_flattens_visibility_from_share_config() {
        let raw = json!({
            "id": "abc-123",
            "name": "my-memory",
            "question": "What?",
            "answer": "Because.",
            "memoryType": "Note",
            "memoryScope": "EntityScoped",
            "shareConfig": {"visibility": "Shared"},
            "usageCount": 7
        });
        let memory: ContextMemory = serde_json::from_value(raw).unwrap();
        assert_eq!(memory.id, "abc-123");
        assert_eq!(memory.visibility, MemoryVisibility::Shared);
        assert_eq!(memory.usage_count, 7);
    }

    #[test]
    fn context_memory_defaults_visibility_when_share_config_missing() {
        let raw = json!({
            "id": "abc-123",
            "name": "my-memory",
            "memoryType": "Note",
            "memoryScope": "EntityScoped"
        });
        let memory: ContextMemory = serde_json::from_value(raw).unwrap();
        assert_eq!(memory.visibility, MemoryVisibility::Private);
    }

    #[test]
    fn create_request_serializes_visibility_into_share_config() {
        let req = CreateContextMemoryRequest {
            name: "test".into(),
            question: "Q".into(),
            answer: "A".into(),
            title: None,
            description: None,
            memory_type: MemoryType::Note,
            memory_scope: MemoryScope::EntityScoped,
            share_config: ShareConfig {
                visibility: MemoryVisibility::Private,
            },
            primary_entity: None,
            related_entities: None,
            tags: Some(vec![TagLabel::manual("PII.Sensitive")]),
        };
        let value = serde_json::to_value(&req).unwrap();
        assert_eq!(value["memoryType"], "Note");
        assert_eq!(value["memoryScope"], "EntityScoped");
        assert_eq!(value["shareConfig"]["visibility"], "Private");
        assert_eq!(value["tags"][0]["tagFQN"], "PII.Sensitive");
        assert_eq!(value["tags"][0]["labelType"], "Manual");
    }

    #[test]
    fn search_results_parse_opensearch_shape() {
        let raw = json!({
            "hits": {
                "total": {"value": 42},
                "hits": [
                    {
                        "_score": 1.5,
                        "_source": {
                            "id": "m1",
                            "name": "first",
                            "memoryType": "Note",
                            "memoryScope": "EntityScoped",
                            "shareConfig": {"visibility": "Private"}
                        }
                    }
                ]
            }
        });
        let results = MemorySearchResults::from_opensearch(&raw).unwrap();
        assert_eq!(results.total, 42);
        assert_eq!(results.hits.len(), 1);
        assert_eq!(results.hits[0].score, 1.5);
        assert_eq!(results.hits[0].memory.id, "m1");
    }

    #[tokio::test]
    async fn list_memories_paginates_through_results() {
        let server = MockServer::start().await;

        Mock::given(method("GET"))
            .and(path("/api/v1/contextCenter/memories"))
            .respond_with(ResponseTemplate::new(200).set_body_json(json!({
                "data": [
                    {"id": "1", "name": "one", "memoryType": "Note", "memoryScope": "EntityScoped"}
                ],
                "paging": {"after": null}
            })))
            .mount(&server)
            .await;

        let client = make_client(&server.uri(), "tok");
        let memories = client.list_memories(None, None).await.unwrap();
        assert_eq!(memories.len(), 1);
        assert_eq!(memories[0].id, "1");
    }

    #[tokio::test]
    async fn get_memory_returns_parsed_response() {
        let server = MockServer::start().await;

        Mock::given(method("GET"))
            .and(path("/api/v1/contextCenter/memories/abc"))
            .respond_with(ResponseTemplate::new(200).set_body_json(json!({
                "id": "abc",
                "name": "test",
                "memoryType": "Faq",
                "memoryScope": "UserGlobal",
                "shareConfig": {"visibility": "Entity"}
            })))
            .mount(&server)
            .await;

        let client = make_client(&server.uri(), "tok");
        let memory = client.get_memory("abc").await.unwrap();
        assert_eq!(memory.id, "abc");
        assert_eq!(memory.memory_type, MemoryType::Faq);
        assert_eq!(memory.memory_scope, MemoryScope::UserGlobal);
        assert_eq!(memory.visibility, MemoryVisibility::Entity);
    }

    #[tokio::test]
    async fn delete_memory_passes_hard_delete_param() {
        let server = MockServer::start().await;

        Mock::given(method("DELETE"))
            .and(path("/api/v1/contextCenter/memories/xyz"))
            .and(query_param("hardDelete", "true"))
            .respond_with(ResponseTemplate::new(200))
            .mount(&server)
            .await;

        let client = make_client(&server.uri(), "tok");
        client.delete_memory("xyz", true).await.unwrap();
    }
}
