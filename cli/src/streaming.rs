//! Server-Sent Events (SSE) parser for streaming responses.
//!
//! Parses the SSE format:
//! ```
//! event: message
//! data: {"streamId": "...", "conversationId": "...", "data": {"message": ChatMessage}}
//! ```

use crate::error::{CliError, CliResult};
use futures_util::StreamExt;
use reqwest::Response;
use serde::Deserialize;
use std::io::Write;
use std::path::Path;

/// Sender types matching ChatMessage.
#[derive(Debug, Clone, PartialEq, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Sender {
    Assistant,
    Human,
    System, // System messages are "thinking" content
}

/// Text message can be a string or an object with message field.
#[derive(Debug, Clone, Deserialize)]
#[serde(untagged)]
pub enum TextMessage {
    Plain(String),
    Object(TextMessageObject),
}

impl TextMessage {
    /// Extract the text content from either variant.
    pub fn text(&self) -> &str {
        match self {
            TextMessage::Plain(s) => s,
            TextMessage::Object(obj) => obj.message.as_deref().unwrap_or(""),
        }
    }
}

/// Structured text message object (e.g., {"type": "markdown", "message": "..."}).
#[derive(Debug, Clone, Deserialize)]
pub struct TextMessageObject {
    pub message: Option<String>,
    // Note: "type" field is ignored but present in API response
}

/// Tool usage information.
#[derive(Debug, Clone, Deserialize)]
pub struct Tool {
    pub name: String,
}

/// A content block within a message.
#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct MessageBlock {
    #[serde(default)]
    pub text_message: Option<TextMessage>,
    #[serde(default)]
    pub tools: Option<Vec<Tool>>,
    // Note: component, attachments fields are ignored
}

/// A chat message from the streaming API.
#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ChatMessage {
    pub sender: Sender,
    #[serde(default)]
    pub content: Vec<MessageBlock>,
    pub conversation_id: String,
    // Note: id, index, timestamp, tokens, actions, stopReason, truncated, attachments are ignored
}

impl ChatMessage {
    /// Extract all text content from the message.
    pub fn text_content(&self) -> String {
        self.content
            .iter()
            .filter_map(|block| block.text_message.as_ref())
            .map(|tm| tm.text())
            .collect::<Vec<_>>()
            .join("")
    }

    /// Extract all tool names used in this message.
    pub fn tools_used(&self) -> Vec<String> {
        self.content
            .iter()
            .filter_map(|block| block.tools.as_ref())
            .flatten()
            .map(|tool| tool.name.clone())
            .collect()
    }
}

/// Inner data wrapper containing the message.
#[derive(Debug, Clone, Deserialize)]
pub struct MessageData {
    pub message: Option<ChatMessage>,
    // Note: "type" field ("update") is ignored
}

/// SSE data payload structure.
#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SSEPayload {
    #[serde(default)]
    pub conversation_id: Option<String>,
    #[serde(default)]
    pub data: Option<MessageData>,
    // Note: streamId, sequence fields are ignored
}

/// SSE event types.
#[derive(Debug, Clone, PartialEq)]
pub enum SSEEventType {
    StreamStart,
    Message,
    StreamCompleted,
    Unknown(String),
}

impl From<&str> for SSEEventType {
    fn from(s: &str) -> Self {
        match s {
            "stream-start" => SSEEventType::StreamStart,
            "message" => SSEEventType::Message,
            "stream-completed" => SSEEventType::StreamCompleted,
            other => SSEEventType::Unknown(other.to_string()),
        }
    }
}

/// Parse a single SSE event string and extract the event type and payload.
fn parse_event(event_str: &str) -> Option<(SSEEventType, SSEPayload)> {
    let mut event_type: Option<&str> = None;
    let mut data: Option<&str> = None;

    for line in event_str.lines() {
        let line = line.trim();
        if let Some(value) = line.strip_prefix("event:") {
            event_type = Some(value.trim());
        } else if let Some(value) = line.strip_prefix("data:") {
            data = Some(value.trim());
        }
        // Ignore id:, retry:, and comments
    }

    let data = data?;
    if data.is_empty() {
        return None;
    }

    let parsed_event_type = event_type
        .map(SSEEventType::from)
        .unwrap_or(SSEEventType::Unknown("".to_string()));

    let payload: SSEPayload = serde_json::from_str(data).ok()?;

    Some((parsed_event_type, payload))
}

/// Process a streaming response and yield chat messages.
pub async fn process_stream<F>(response: Response, handler: F) -> CliResult<Option<String>>
where
    F: FnMut(ChatMessage),
{
    process_stream_inner(response, handler, None).await
}

/// Process a streaming response with debug events optionally written to stderr.
pub async fn process_stream_with_debug<F>(
    response: Response,
    handler: F,
    debug: bool,
) -> CliResult<Option<String>>
where
    F: FnMut(ChatMessage),
{
    let writer: Option<Box<dyn Write + Send>> = if debug {
        Some(Box::new(std::io::stderr()))
    } else {
        None
    };
    process_stream_inner(response, handler, writer).await
}

/// Process a streaming response and append debug events to a file.
///
/// The file is opened in append mode so multiple streams in the same session
/// accumulate into one log. Callers that want a fresh log per session should
/// truncate the file once before invoking this.
pub async fn process_stream_with_debug_file<F>(
    response: Response,
    handler: F,
    debug_log_path: &Path,
) -> CliResult<Option<String>>
where
    F: FnMut(ChatMessage),
{
    let file = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(debug_log_path)?;
    process_stream_inner(response, handler, Some(Box::new(file))).await
}

/// Shared implementation for stream processing.
async fn process_stream_inner<F>(
    response: Response,
    mut handler: F,
    mut debug_writer: Option<Box<dyn Write + Send>>,
) -> CliResult<Option<String>>
where
    F: FnMut(ChatMessage),
{
    let mut stream = response.bytes_stream();
    let mut buffer = String::new();
    let mut conversation_id: Option<String> = None;
    let mut event_count = 0;
    let mut message_count = 0;

    while let Some(chunk) = stream.next().await {
        let chunk = match chunk {
            Ok(c) => c,
            Err(e) => {
                // Surface where the stream died — the most useful detail when
                // debugging "error decoding response body" failures.
                if let Some(w) = debug_writer.as_mut() {
                    let _ = writeln!(
                        w,
                        "[DEBUG] Stream error after {event_count} events, {message_count} messages: {e}"
                    );
                    if !buffer.is_empty() {
                        let _ = writeln!(
                            w,
                            "[DEBUG] Unparsed buffer at error ({} bytes): {buffer:?}",
                            buffer.len()
                        );
                    }
                    let _ = w.flush();
                }
                return Err(CliError::NetworkError(e.to_string()));
            }
        };
        let text = String::from_utf8_lossy(&chunk);
        buffer.push_str(&text);

        // Process complete events (delimited by double newlines)
        while let Some(pos) = buffer.find("\n\n") {
            let event_str = buffer[..pos].to_string();
            buffer = buffer[pos + 2..].to_string();

            if let Some((event_type, payload)) = parse_event(&event_str) {
                event_count += 1;
                if let Some(w) = debug_writer.as_mut() {
                    let _ = writeln!(w, "[DEBUG] Event #{event_count}: {event_type:?}");
                }

                // Capture conversation ID from any event
                if let Some(id) = &payload.conversation_id {
                    conversation_id = Some(id.clone());
                }

                // Only process message events with actual messages
                if event_type == SSEEventType::Message {
                    if let Some(data) = payload.data {
                        if let Some(message) = data.message {
                            message_count += 1;
                            if let Some(w) = debug_writer.as_mut() {
                                let _ = writeln!(
                                    w,
                                    "[DEBUG] Message #{}: sender={:?}, content_blocks={}",
                                    message_count,
                                    message.sender,
                                    message.content.len()
                                );
                            }
                            handler(message);
                        }
                    }
                }
            }
        }
    }

    // Process any remaining buffer content
    if !buffer.trim().is_empty() {
        if let Some((event_type, payload)) = parse_event(&buffer) {
            event_count += 1;
            if let Some(w) = debug_writer.as_mut() {
                let _ = writeln!(w, "[DEBUG] Final Event #{event_count}: {event_type:?}");
            }

            if let Some(id) = &payload.conversation_id {
                conversation_id = Some(id.clone());
            }
            if event_type == SSEEventType::Message {
                if let Some(data) = payload.data {
                    if let Some(message) = data.message {
                        message_count += 1;
                        if let Some(w) = debug_writer.as_mut() {
                            let _ = writeln!(
                                w,
                                "[DEBUG] Final Message #{}: sender={:?}",
                                message_count, message.sender
                            );
                        }
                        handler(message);
                    }
                }
            }
        }
    }

    if let Some(w) = debug_writer.as_mut() {
        let _ = writeln!(
            w,
            "[DEBUG] Stream complete: {event_count} events, {message_count} messages"
        );
        let _ = w.flush();
    }

    Ok(conversation_id)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_message_event() {
        // Test the actual API format with nested data.message
        let event_str = r#"event: message
data: {"conversationId":"conv-1","data":{"message":{"sender":"assistant","content":[{"textMessage":{"type":"markdown","message":"Hello world"}}],"conversationId":"conv-1"}}}"#;

        let (event_type, payload) = parse_event(event_str).unwrap();
        assert_eq!(event_type, SSEEventType::Message);
        assert_eq!(payload.conversation_id.as_deref(), Some("conv-1"));

        let message = payload.data.unwrap().message.unwrap();
        assert_eq!(message.sender, Sender::Assistant);
        assert_eq!(message.text_content(), "Hello world");
    }

    #[test]
    fn test_parse_system_message() {
        let event_str = r#"event: message
data: {"conversationId":"conv-1","data":{"message":{"sender":"system","content":[{"textMessage":"Thinking..."}],"conversationId":"conv-1"}}}"#;

        let (_, payload) = parse_event(event_str).unwrap();
        let message = payload.data.unwrap().message.unwrap();
        assert_eq!(message.sender, Sender::System);
        assert_eq!(message.text_content(), "Thinking...");
    }

    #[test]
    fn test_parse_stream_start_event() {
        let event_str = r#"event: stream-start
data: {"streamId":"abc123","conversationId":"conv-1","sequence":0}"#;

        let (event_type, payload) = parse_event(event_str).unwrap();
        assert_eq!(event_type, SSEEventType::StreamStart);
        assert_eq!(payload.conversation_id.as_deref(), Some("conv-1"));
    }

    #[test]
    fn test_parse_stream_completed_event() {
        let event_str = r#"event: stream-completed
data: {"message":"total messages: 1","type":"completed"}"#;

        let (event_type, _) = parse_event(event_str).unwrap();
        assert_eq!(event_type, SSEEventType::StreamCompleted);
    }

    #[test]
    fn test_event_type_from_string() {
        assert_eq!(
            SSEEventType::from("stream-start"),
            SSEEventType::StreamStart
        );
        assert_eq!(SSEEventType::from("message"), SSEEventType::Message);
        assert_eq!(
            SSEEventType::from("stream-completed"),
            SSEEventType::StreamCompleted
        );
        assert!(matches!(
            SSEEventType::from("unknown"),
            SSEEventType::Unknown(_)
        ));
    }

    #[test]
    fn test_text_message_plain() {
        let tm = TextMessage::Plain("Hello".to_string());
        assert_eq!(tm.text(), "Hello");
    }

    #[test]
    fn test_text_message_object() {
        let tm = TextMessage::Object(TextMessageObject {
            message: Some("World".to_string()),
        });
        assert_eq!(tm.text(), "World");
    }

    #[test]
    fn test_message_with_tools() {
        let event_str = r#"event: message
data: {"conversationId":"conv-1","data":{"message":{"sender":"assistant","content":[{"textMessage":{"message":"Searching..."},"tools":[{"name":"searchMetadata"}]}],"conversationId":"conv-1"}}}"#;

        let (_, payload) = parse_event(event_str).unwrap();
        let message = payload.data.unwrap().message.unwrap();
        let tools = message.tools_used();
        assert_eq!(tools, vec!["searchMetadata"]);
    }

    #[tokio::test]
    async fn test_process_stream_with_debug_file_writes_events() {
        use wiremock::matchers::{method, path};
        use wiremock::{Mock, MockServer, ResponseTemplate};

        let server = MockServer::start().await;
        let body = "event: stream-start\ndata: {\"streamId\":\"s1\",\"conversationId\":\"c1\",\"sequence\":0}\n\nevent: message\ndata: {\"conversationId\":\"c1\",\"data\":{\"message\":{\"sender\":\"assistant\",\"content\":[{\"textMessage\":\"hi\"}],\"conversationId\":\"c1\"}}}\n\nevent: stream-completed\ndata: {\"message\":\"done\",\"type\":\"completed\"}\n\n";

        Mock::given(method("GET"))
            .and(path("/sse"))
            .respond_with(
                ResponseTemplate::new(200)
                    .insert_header("content-type", "text/event-stream")
                    .set_body_string(body),
            )
            .mount(&server)
            .await;

        let response = reqwest::get(format!("{}/sse", server.uri())).await.unwrap();

        let log_path =
            std::env::temp_dir().join(format!("ai-sdk-test-debug-{}.log", uuid::Uuid::new_v4()));
        // Ensure clean slate
        let _ = std::fs::remove_file(&log_path);

        let conv_id = process_stream_with_debug_file(response, |_msg| {}, &log_path)
            .await
            .unwrap();
        assert_eq!(conv_id.as_deref(), Some("c1"));

        let contents = std::fs::read_to_string(&log_path).unwrap();
        assert!(contents.contains("Event #1: StreamStart"));
        assert!(contents.contains("Event #2: Message"));
        assert!(contents.contains("Message #1: sender=Assistant"));
        assert!(contents.contains("Event #3: StreamCompleted"));
        assert!(contents.contains("Stream complete: 3 events, 1 messages"));

        let _ = std::fs::remove_file(&log_path);
    }
}
