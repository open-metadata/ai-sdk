//! UI layout and rendering for the TUI chat interface.

use super::app::{App, DisplayMessage, Status};
use super::markdown::render_markdown;
use crate::client::MetadataClient;
use crate::config::ResolvedConfig;
use crate::error::{CliError, CliResult};
use crate::streaming::{process_stream, Sender};

use crossterm::{
    event::{DisableMouseCapture, EnableMouseCapture, Event, EventStream, KeyCode, KeyModifiers},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use futures_util::StreamExt;
use ratatui::{
    backend::CrosstermBackend,
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph, Wrap},
    Frame, Terminal,
};
use std::io;
use std::time::Duration;
use tokio::sync::mpsc;

/// Messages from the streaming task to the main loop.
enum StreamEvent {
    Content(String),
    ToolUse(String),
    Thinking(String),
    Done(Option<String>), // conversation_id
    Error(String),
}

/// Messages for async operations.
enum AsyncEvent {
    Stream(StreamEvent),
    AgentsList(Vec<String>),
    AgentsError(String),
}

/// Run the TUI chat interface.
/// If agent_name is None, shows agent selection menu on start.
pub async fn run_tui(agent_name: Option<&str>, conversation_id: Option<String>) -> CliResult<()> {
    // Load config and create client first (needed for agent list)
    let config = ResolvedConfig::load()?;
    let client = MetadataClient::new(&config)?;

    // Setup terminal
    enable_raw_mode().map_err(|e| CliError::Other(e.to_string()))?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen, EnableMouseCapture)
        .map_err(|e| CliError::Other(e.to_string()))?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend).map_err(|e| CliError::Other(e.to_string()))?;

    // Create app state
    let mut app = App::new(
        agent_name.map(String::from).unwrap_or_default(),
        conversation_id,
    );

    // If no agent specified, fetch agents and show selection menu
    if agent_name.is_none() {
        match client.list_agents().await {
            Ok(agents) => {
                let names: Vec<String> = agents
                    .into_iter()
                    .filter(|a| a.api_enabled)
                    .map(|a| a.name)
                    .collect();
                if names.is_empty() {
                    app.set_error("No API-enabled agents available".to_string());
                } else {
                    app.show_agents(names);
                }
            }
            Err(e) => {
                app.set_error(format!("Failed to fetch agents: {}", e));
            }
        }
    }

    // Run the main loop
    let result = run_main_loop(&mut terminal, &mut app, &client).await;

    // Restore terminal
    disable_raw_mode().map_err(|e| CliError::Other(e.to_string()))?;
    execute!(
        terminal.backend_mut(),
        LeaveAlternateScreen,
        DisableMouseCapture
    )
    .map_err(|e| CliError::Other(e.to_string()))?;
    terminal
        .show_cursor()
        .map_err(|e| CliError::Other(e.to_string()))?;

    result
}

/// Main event loop.
async fn run_main_loop(
    terminal: &mut Terminal<CrosstermBackend<io::Stdout>>,
    app: &mut App,
    client: &MetadataClient,
) -> CliResult<()> {
    let (async_tx, mut async_rx) = mpsc::channel::<AsyncEvent>(100);
    let mut event_stream = EventStream::new();
    let mut spinner_interval = tokio::time::interval(Duration::from_millis(80));

    loop {
        // Draw UI
        terminal
            .draw(|f| render_ui(f, app))
            .map_err(|e| CliError::Other(e.to_string()))?;

        tokio::select! {
            // Check for async events (streams, agent list, etc.)
            Some(event) = async_rx.recv() => {
                match event {
                    AsyncEvent::Stream(stream_event) => {
                        match stream_event {
                            StreamEvent::Content(content) => {
                                app.append_streaming_content(&content);
                                app.set_streaming_stage("Responding...");
                            }
                            StreamEvent::ToolUse(tool) => {
                                app.set_streaming_stage(&format!("Using {}...", tool));
                            }
                            StreamEvent::Thinking(thought) => {
                                app.append_thinking_content(&thought);
                                app.set_streaming_stage("Thinking...");
                            }
                            StreamEvent::Done(conv_id) => {
                                if let Some(id) = conv_id {
                                    app.conversation_id = Some(id);
                                }
                                app.finish_streaming();
                            }
                            StreamEvent::Error(err) => {
                                app.set_error(err);
                            }
                        }
                    }
                    AsyncEvent::AgentsList(agents) => {
                        app.show_agents(agents);
                    }
                    AsyncEvent::AgentsError(err) => {
                        app.set_error(err);
                    }
                }
            }

            // Tick spinner at regular intervals
            _ = spinner_interval.tick() => {
                if app.is_streaming() {
                    app.tick_spinner();
                }
            }

            // Handle keyboard events immediately
            Some(Ok(event)) = event_stream.next() => {
                if let Event::Key(key) = event {
                    // Ctrl+C always quits
                    if key.modifiers.contains(KeyModifiers::CONTROL) && key.code == KeyCode::Char('c') {
                        app.should_quit = true;
                    } else if app.show_agent_menu {
                        // Agent selection menu mode with filtering
                        match key.code {
                            KeyCode::Up => app.scroll_up(),
                            KeyCode::Down => app.scroll_down(),
                            KeyCode::Enter => app.select_agent(),
                            KeyCode::Esc => app.cancel_agent_menu(),
                            KeyCode::Backspace => app.agent_menu_delete_char(),
                            KeyCode::Char(c) => app.agent_menu_enter_char(c),
                            _ => {}
                        }
                    } else if !app.is_streaming() {
                        match key.code {
                            KeyCode::Enter => {
                                let message = app.take_input();
                                let trimmed = message.trim();

                                if trimmed.is_empty() {
                                    continue;
                                }

                                // Handle commands
                                if trimmed.starts_with('/') {
                                    match trimmed {
                                        "/agents" | "/a" => {
                                            // Fetch agents list
                                            let tx = async_tx.clone();
                                            let client = client.clone();
                                            tokio::spawn(async move {
                                                match client.list_agents().await {
                                                    Ok(agents) => {
                                                        let names: Vec<String> = agents
                                                            .into_iter()
                                                            .filter(|a| a.api_enabled)
                                                            .map(|a| a.name)
                                                            .collect();
                                                        let _ = tx.send(AsyncEvent::AgentsList(names)).await;
                                                    }
                                                    Err(e) => {
                                                        let _ = tx.send(AsyncEvent::AgentsError(e.to_string())).await;
                                                    }
                                                }
                                            });
                                        }
                                        "/quit" | "/q" => {
                                            app.should_quit = true;
                                        }
                                        "/clear" | "/c" => {
                                            app.messages.clear();
                                            app.conversation_id = None;
                                        }
                                        _ => {
                                            // Unknown command - show as system message
                                            app.messages.push(DisplayMessage::system(
                                                format!("Unknown command: {}. Try /agents, /clear, or /quit", trimmed)
                                            ));
                                        }
                                    }
                                } else {
                                    // Regular message - send to agent
                                    app.add_user_message(message.clone());
                                    app.start_streaming("Connecting...");

                                    let tx = async_tx.clone();
                                    let client = client.clone();
                                    let agent = app.agent_name.clone();
                                    let conv_id = app.conversation_id.clone();

                                    tokio::spawn(async move {
                                        stream_agent_response(tx, client, agent, message, conv_id).await;
                                    });
                                }
                            }
                            KeyCode::Char(c) => app.enter_char(c),
                            KeyCode::Backspace => app.delete_char(),
                            KeyCode::Left => app.move_cursor_left(),
                            KeyCode::Right => app.move_cursor_right(),
                            KeyCode::Up => app.scroll_up(),
                            KeyCode::Down => app.scroll_down(),
                            KeyCode::Esc => app.should_quit = true,
                            _ => {}
                        }
                    } else {
                        // While streaming, only allow scrolling
                        match key.code {
                            KeyCode::Up => app.scroll_up(),
                            KeyCode::Down => app.scroll_down(),
                            _ => {}
                        }
                    }
                }
            }
        }

        if app.should_quit {
            break;
        }
    }

    Ok(())
}

/// Spawn a task to stream agent response.
async fn stream_agent_response(
    tx: mpsc::Sender<AsyncEvent>,
    client: MetadataClient,
    agent: String,
    message: String,
    conversation_id: Option<String>,
) {
    let result = client
        .stream(&agent, Some(message.as_str()), conversation_id.as_deref())
        .await;

    match result {
        Ok(response) => {
            let mut final_conv_id = conversation_id;

            let process_result = process_stream(response, |msg| {
                final_conv_id = Some(msg.conversation_id.clone());

                match msg.sender {
                    Sender::Assistant => {
                        let text = msg.text_content();
                        if !text.is_empty() {
                            let _ = tx.try_send(AsyncEvent::Stream(StreamEvent::Content(text)));
                        }
                        for tool in msg.tools_used() {
                            let _ = tx.try_send(AsyncEvent::Stream(StreamEvent::ToolUse(tool)));
                        }
                    }
                    Sender::System => {
                        // System messages are "thinking" content
                        let text = msg.text_content();
                        if !text.is_empty() {
                            let _ = tx.try_send(AsyncEvent::Stream(StreamEvent::Thinking(text)));
                        }
                    }
                    Sender::Human => {}
                }
            })
            .await;

            match process_result {
                Ok(_) => {
                    let _ = tx
                        .send(AsyncEvent::Stream(StreamEvent::Done(final_conv_id)))
                        .await;
                }
                Err(e) => {
                    let _ = tx
                        .send(AsyncEvent::Stream(StreamEvent::Error(e.to_string())))
                        .await;
                }
            }
        }
        Err(e) => {
            let _ = tx
                .send(AsyncEvent::Stream(StreamEvent::Error(e.to_string())))
                .await;
        }
    }
}

/// Render the entire UI.
fn render_ui(frame: &mut Frame, app: &mut App) {
    let size = frame.size();

    // Main layout: header, chat, input
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(1), // Header
            Constraint::Min(5),    // Chat area
            Constraint::Length(3), // Input area
        ])
        .split(size);

    render_header(frame, app, chunks[0]);
    render_chat(frame, app, chunks[1]);
    render_input(frame, app, chunks[2]);

    // Render agent selection popup if active
    if app.show_agent_menu {
        render_agent_menu(frame, app, size);
    }
}

/// Render the header bar.
fn render_header(frame: &mut Frame, app: &App, area: Rect) {
    let status_indicator = match &app.status {
        Status::Connected => Span::styled(" ● ", Style::default().fg(Color::Green)),
        Status::Streaming { .. } => Span::styled(
            format!(" {} ", app.spinner()),
            Style::default().fg(Color::Yellow),
        ),
        Status::Error(_) => Span::styled(" ● ", Style::default().fg(Color::Red)),
    };

    let status_text = match &app.status {
        Status::Connected => "Connected",
        Status::Streaming { stage } => stage,
        Status::Error(e) => e,
    };

    let title = format!(" {} ", app.agent_name);
    let header = Line::from(vec![
        Span::styled("─".to_string(), Style::default().fg(Color::DarkGray)),
        Span::styled(
            title,
            Style::default()
                .fg(Color::Cyan)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled(
            "─".repeat(
                area.width
                    .saturating_sub(app.agent_name.len() as u16 + status_text.len() as u16 + 10)
                    as usize,
            ),
            Style::default().fg(Color::DarkGray),
        ),
        Span::styled(
            status_text.to_string(),
            Style::default().fg(Color::DarkGray),
        ),
        status_indicator,
        Span::styled("─", Style::default().fg(Color::DarkGray)),
    ]);

    frame.render_widget(Paragraph::new(header), area);
}

/// Render the chat message area.
fn render_chat(frame: &mut Frame, app: &mut App, area: Rect) {
    let inner_width = area.width.saturating_sub(2) as usize;
    let mut all_lines: Vec<Line> = Vec::new();

    // Render each message
    for msg in &app.messages {
        // Show thinking content first if present (for assistant messages)
        if let Some(thinking) = &msg.thinking {
            all_lines.push(Line::from(Span::styled(
                "Thinking: ",
                Style::default()
                    .fg(Color::DarkGray)
                    .add_modifier(Modifier::ITALIC),
            )));
            for line in thinking.lines() {
                all_lines.push(Line::from(Span::styled(
                    format!("  {}", line),
                    Style::default().fg(Color::DarkGray),
                )));
            }
            all_lines.push(Line::default());
        }

        let prefix = match msg.sender {
            Sender::Human => ("You: ", Color::Green),
            Sender::Assistant => ("Assistant: ", Color::Cyan),
            Sender::System => ("System: ", Color::DarkGray),
        };

        // Add sender prefix
        all_lines.push(Line::from(Span::styled(
            prefix.0.to_string(),
            Style::default().fg(prefix.1).add_modifier(Modifier::BOLD),
        )));

        // Render markdown content
        let rendered = render_markdown(&msg.content, inner_width);
        all_lines.extend(rendered);

        // Add spacing between messages
        all_lines.push(Line::default());
    }

    // Render streaming content if any
    if app.is_streaming() || !app.streaming_content.is_empty() || !app.thinking_content.is_empty() {
        // Show thinking content first (in grey)
        if !app.thinking_content.is_empty() {
            all_lines.push(Line::from(Span::styled(
                "Thinking: ",
                Style::default()
                    .fg(Color::DarkGray)
                    .add_modifier(Modifier::ITALIC),
            )));
            // Render thinking in grey
            for line in app.thinking_content.lines() {
                all_lines.push(Line::from(Span::styled(
                    format!("  {}", line),
                    Style::default().fg(Color::DarkGray),
                )));
            }
            all_lines.push(Line::default());
        }

        // Show assistant content
        if !app.streaming_content.is_empty() {
            all_lines.push(Line::from(Span::styled(
                "Assistant: ",
                Style::default()
                    .fg(Color::Cyan)
                    .add_modifier(Modifier::BOLD),
            )));
            let rendered = render_markdown(&app.streaming_content, inner_width);
            all_lines.extend(rendered);
        }

        // Show spinner line (only when actively working, not just "Connecting...")
        if let Status::Streaming { stage } = &app.status {
            if stage != "Connecting..." {
                all_lines.push(Line::default());
                all_lines.push(Line::from(vec![
                    Span::styled(
                        format!("{} ", app.spinner()),
                        Style::default().fg(Color::Yellow),
                    ),
                    Span::styled(stage.clone(), Style::default().fg(Color::DarkGray)),
                ]));
            }
        }
    }

    // Calculate scroll and update max_scroll for proper bounds
    let visible_height = area.height.saturating_sub(2) as usize;
    let total_lines = all_lines.len();
    app.set_max_scroll(total_lines, visible_height);

    let scroll = if total_lines > visible_height {
        (total_lines - visible_height).saturating_sub(app.scroll_offset)
    } else {
        0
    };

    let chat = Paragraph::new(all_lines)
        .block(Block::default().borders(Borders::LEFT | Borders::RIGHT))
        .wrap(Wrap { trim: false })
        .scroll((scroll as u16, 0));

    frame.render_widget(chat, area);
}

/// Render the input area.
fn render_input(frame: &mut Frame, app: &App, area: Rect) {
    let input_style = if app.is_streaming() || app.show_agent_menu {
        Style::default().fg(Color::DarkGray)
    } else {
        Style::default()
    };

    let hint = if app.is_streaming() {
        "Streaming..."
    } else if app.show_agent_menu {
        "↑↓ select │ Enter confirm │ Esc cancel"
    } else {
        "/agents │ /clear │ Ctrl+C quit"
    };

    let input_text = if app.is_streaming() || app.show_agent_menu {
        String::new()
    } else {
        app.input.clone()
    };

    let input = Paragraph::new(Line::from(vec![
        Span::styled("> ", Style::default().fg(Color::Green)),
        Span::styled(input_text, input_style),
    ]))
    .block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::DarkGray))
            .title_bottom(Line::from(hint).right_aligned()),
    );

    frame.render_widget(input, area);

    // Set cursor position
    if !app.is_streaming() && !app.show_agent_menu {
        frame.set_cursor(area.x + 3 + app.cursor_position as u16, area.y + 1);
    }
}

/// Render the agent selection popup menu with filtering and virtual scrolling.
fn render_agent_menu(frame: &mut Frame, app: &mut App, area: Rect) {
    // Calculate popup size - accommodate filter input and reasonable list height
    let popup_width = 50.min(area.width.saturating_sub(4));
    let popup_height = 20.min(area.height.saturating_sub(4));

    // Center the popup
    let popup_x = (area.width.saturating_sub(popup_width)) / 2;
    let popup_y = (area.height.saturating_sub(popup_height)) / 2;

    let popup_area = Rect::new(popup_x, popup_y, popup_width, popup_height);

    // Clear the area first
    let clear = Block::default().style(Style::default().bg(Color::Black));
    frame.render_widget(clear, popup_area);

    // Render the SingleSelect component
    app.agent_select.render(frame, popup_area);
}
