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

/// AI SDK API client.
#[derive(Clone)]
pub struct AISdkClient {
    client: Client,
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

        // Normalize base URL (remove trailing slash)
        let base_url = config.host.trim_end_matches('/').to_string();

        Ok(Self {
            client,
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
            .client
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
}
