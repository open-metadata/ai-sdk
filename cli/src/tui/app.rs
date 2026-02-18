//! Application state for the TUI chat interface.

use super::wizard::{SelectItem, SingleSelect};
use crate::streaming::Sender;

/// Connection/streaming status.
#[derive(Debug, Clone)]
pub enum Status {
    Connected,
    Streaming { stage: String },
    Error(String),
}

impl Status {
    pub fn is_streaming(&self) -> bool {
        matches!(self, Status::Streaming { .. })
    }
}

/// A message ready for display in the chat.
#[derive(Debug, Clone)]
pub struct DisplayMessage {
    pub sender: Sender,
    pub content: String,
    /// Optional thinking/reasoning that preceded this message.
    pub thinking: Option<String>,
}

impl DisplayMessage {
    pub fn user(content: String) -> Self {
        Self {
            sender: Sender::Human,
            content,
            thinking: None,
        }
    }

    #[allow(dead_code)]
    pub fn assistant(content: String) -> Self {
        Self {
            sender: Sender::Assistant,
            content,
            thinking: None,
        }
    }

    pub fn assistant_with_thinking(content: String, thinking: Option<String>) -> Self {
        Self {
            sender: Sender::Assistant,
            content,
            thinking,
        }
    }

    #[allow(dead_code)]
    pub fn system(content: String) -> Self {
        Self {
            sender: Sender::System,
            content,
            thinking: None,
        }
    }
}

/// Spinner animation frames.
const SPINNER_FRAMES: &[char] = &['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'];

/// Main application state.
pub struct App {
    /// Name of the agent being chatted with.
    pub agent_name: String,
    /// Conversation ID for multi-turn conversations.
    pub conversation_id: Option<String>,
    /// Chat message history.
    pub messages: Vec<DisplayMessage>,
    /// Current input buffer.
    pub input: String,
    /// Cursor position in input.
    pub cursor_position: usize,
    /// Scroll offset for chat history.
    pub scroll_offset: usize,
    /// Maximum scroll offset (set during render).
    pub max_scroll: usize,
    /// Current connection/streaming status.
    pub status: Status,
    /// Current spinner frame index.
    spinner_frame: usize,
    /// Content being streamed (accumulated).
    pub streaming_content: String,
    /// Thinking content being streamed (accumulated).
    pub thinking_content: String,
    /// Whether the app should quit.
    pub should_quit: bool,
    /// Whether to show agent selection menu.
    pub show_agent_menu: bool,
    /// Agent selection component with filtering and virtual scrolling.
    pub agent_select: SingleSelect,
}

impl App {
    /// Create a new app instance.
    pub fn new(agent_name: String, conversation_id: Option<String>) -> Self {
        let mut agent_select = SingleSelect::new("Select Agent");
        agent_select.focused = true;
        Self {
            agent_name,
            conversation_id,
            messages: Vec::new(),
            input: String::new(),
            cursor_position: 0,
            scroll_offset: 0,
            max_scroll: 0,
            status: Status::Connected,
            spinner_frame: 0,
            streaming_content: String::new(),
            thinking_content: String::new(),
            should_quit: false,
            show_agent_menu: false,
            agent_select,
        }
    }

    /// Get the current spinner character.
    pub fn spinner(&self) -> char {
        SPINNER_FRAMES[self.spinner_frame]
    }

    /// Advance the spinner animation.
    pub fn tick_spinner(&mut self) {
        self.spinner_frame = (self.spinner_frame + 1) % SPINNER_FRAMES.len();
    }

    /// Start streaming mode.
    pub fn start_streaming(&mut self, stage: &str) {
        self.status = Status::Streaming {
            stage: stage.to_string(),
        };
        self.streaming_content.clear();
        self.thinking_content.clear();
    }

    /// Update streaming stage (e.g., tool usage).
    pub fn set_streaming_stage(&mut self, stage: &str) {
        if let Status::Streaming { .. } = self.status {
            self.status = Status::Streaming {
                stage: stage.to_string(),
            };
        }
    }

    /// Append content during streaming.
    pub fn append_streaming_content(&mut self, content: &str) {
        self.streaming_content.push_str(content);
    }

    /// Append thinking content during streaming.
    pub fn append_thinking_content(&mut self, content: &str) {
        self.thinking_content.push_str(content);
    }

    /// Finish streaming and add the message to history.
    pub fn finish_streaming(&mut self) {
        if !self.streaming_content.is_empty() {
            // Preserve thinking content with the assistant message
            let thinking = if self.thinking_content.is_empty() {
                None
            } else {
                Some(std::mem::take(&mut self.thinking_content))
            };
            self.messages.push(DisplayMessage::assistant_with_thinking(
                std::mem::take(&mut self.streaming_content),
                thinking,
            ));
        }
        self.streaming_content.clear();
        self.thinking_content.clear();
        self.status = Status::Connected;
        self.scroll_to_bottom();
    }

    /// Set error status.
    pub fn set_error(&mut self, error: String) {
        self.status = Status::Error(error);
        self.streaming_content.clear();
    }

    /// Add a user message to history.
    pub fn add_user_message(&mut self, content: String) {
        self.messages.push(DisplayMessage::user(content));
        self.scroll_to_bottom();
    }

    /// Handle character input.
    pub fn enter_char(&mut self, c: char) {
        self.input.insert(self.cursor_position, c);
        self.cursor_position += 1;
    }

    /// Handle backspace.
    pub fn delete_char(&mut self) {
        if self.cursor_position > 0 {
            self.cursor_position -= 1;
            self.input.remove(self.cursor_position);
        }
    }

    /// Move cursor left.
    pub fn move_cursor_left(&mut self) {
        if self.cursor_position > 0 {
            self.cursor_position -= 1;
        }
    }

    /// Move cursor right.
    pub fn move_cursor_right(&mut self) {
        if self.cursor_position < self.input.len() {
            self.cursor_position += 1;
        }
    }

    /// Take the current input and clear it.
    pub fn take_input(&mut self) -> String {
        let input = std::mem::take(&mut self.input);
        self.cursor_position = 0;
        input
    }

    /// Scroll chat up (see older messages).
    pub fn scroll_up(&mut self) {
        if self.show_agent_menu {
            // In menu mode, move selection up
            self.agent_select.select_previous();
        } else {
            self.scroll_offset = self.scroll_offset.saturating_add(3).min(self.max_scroll);
        }
    }

    /// Scroll chat down (see newer messages).
    pub fn scroll_down(&mut self) {
        if self.show_agent_menu {
            // In menu mode, move selection down
            self.agent_select.select_next();
        } else {
            self.scroll_offset = self.scroll_offset.saturating_sub(3);
        }
    }

    /// Scroll to bottom of chat.
    pub fn scroll_to_bottom(&mut self) {
        self.scroll_offset = 0;
    }

    /// Set max scroll based on content height.
    pub fn set_max_scroll(&mut self, total_lines: usize, visible_height: usize) {
        self.max_scroll = total_lines.saturating_sub(visible_height);
    }

    /// Check if currently streaming.
    pub fn is_streaming(&self) -> bool {
        self.status.is_streaming()
    }

    /// Show the agent selection menu.
    pub fn show_agents(&mut self, agents: Vec<String>) {
        let items: Vec<SelectItem> = agents
            .into_iter()
            .map(|name| SelectItem::new(name.clone(), name))
            .collect();
        self.agent_select.set_items(items);
        self.agent_select.focused = true;
        self.show_agent_menu = true;
    }

    /// Select the current agent from menu.
    pub fn select_agent(&mut self) {
        if let Some(agent) = self.agent_select.selected() {
            self.agent_name = agent.name.clone();
            self.conversation_id = None; // Start fresh conversation with new agent
            self.messages.clear();
        }
        self.show_agent_menu = false;
    }

    /// Handle character input in agent menu (for filtering).
    pub fn agent_menu_enter_char(&mut self, c: char) {
        self.agent_select.enter_filter_char(c);
    }

    /// Handle backspace in agent menu (for filtering).
    pub fn agent_menu_delete_char(&mut self) {
        self.agent_select.delete_filter_char();
    }

    /// Cancel agent selection.
    pub fn cancel_agent_menu(&mut self) {
        self.show_agent_menu = false;
    }

    /// Check if input is a command.
    #[allow(dead_code)]
    pub fn is_command(input: &str) -> bool {
        input.trim().starts_with('/')
    }
}
