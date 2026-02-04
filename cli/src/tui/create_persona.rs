//! Persona creation TUI wizard.
//!
//! A 3-step wizard for creating new personas:
//! 1. Basic Details - name and description
//! 2. System Prompt - multiline text area
//! 3. Review & Submit - summary and confirmation

use crate::commands::personas::run_create;
use crate::error::{CliError, CliResult};
use crate::tui::wizard::{
    render_error, render_loading, render_wizard_footer, render_wizard_header, TextInput,
    WizardStatus,
};

use crossterm::{
    event::{self, DisableMouseCapture, EnableMouseCapture, Event, KeyCode, KeyModifiers},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
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

/// Wizard step enumeration.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Step {
    BasicDetails,
    SystemPrompt,
    Review,
}

impl Step {
    fn number(&self) -> usize {
        match self {
            Step::BasicDetails => 1,
            Step::SystemPrompt => 2,
            Step::Review => 3,
        }
    }

    fn title(&self) -> &'static str {
        match self {
            Step::BasicDetails => "Basic Details",
            Step::SystemPrompt => "System Prompt",
            Step::Review => "Review & Submit",
        }
    }
}

/// Focus state for the basic details step.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum BasicDetailsFocus {
    Name,
    Description,
}

/// Persona creation wizard state.
struct CreatePersonaWizard {
    /// Current step.
    step: Step,
    /// Name input.
    name_input: TextInput,
    /// Description input.
    description_input: TextInput,
    /// Prompt input (multiline).
    prompt_input: TextInput,
    /// Current focus in basic details step.
    basic_focus: BasicDetailsFocus,
    /// Wizard status.
    status: WizardStatus,
    /// Spinner frame index.
    spinner_frame: usize,
    /// Whether the wizard should exit.
    should_exit: bool,
    /// Whether creation was successful.
    success: bool,
    /// Validation error message.
    validation_error: Option<String>,
}

impl CreatePersonaWizard {
    fn new() -> Self {
        let mut name_input = TextInput::new("Name").placeholder("my-persona").required();
        name_input.focused = true;

        let description_input = TextInput::new("Description")
            .placeholder("A helpful persona for...")
            .required();

        let prompt_input = TextInput::new("System Prompt")
            .placeholder("You are a helpful assistant that...")
            .required()
            .multiline();

        Self {
            step: Step::BasicDetails,
            name_input,
            description_input,
            prompt_input,
            basic_focus: BasicDetailsFocus::Name,
            status: WizardStatus::Idle,
            spinner_frame: 0,
            should_exit: false,
            success: false,
            validation_error: None,
        }
    }

    /// Validate the name field.
    /// Pattern: ^[a-zA-Z][a-zA-Z0-9_-]*$
    fn validate_name(&self) -> Result<(), String> {
        let name = self.name_input.value.trim();
        if name.is_empty() {
            return Err("Name is required".to_string());
        }

        let chars: Vec<char> = name.chars().collect();

        // Must start with a letter
        if !chars[0].is_ascii_alphabetic() {
            return Err(
                "Name must start with a letter and contain only letters, numbers, underscores, and hyphens"
                    .to_string(),
            );
        }

        // Rest must be alphanumeric, underscore, or hyphen
        for c in &chars[1..] {
            if !c.is_ascii_alphanumeric() && *c != '_' && *c != '-' {
                return Err(
                    "Name must start with a letter and contain only letters, numbers, underscores, and hyphens"
                        .to_string(),
                );
            }
        }

        Ok(())
    }

    /// Validate all basic details.
    fn validate_basic_details(&self) -> Result<(), String> {
        self.validate_name()?;
        if self.description_input.value.trim().is_empty() {
            return Err("Description is required".to_string());
        }
        Ok(())
    }

    /// Validate the prompt step.
    fn validate_prompt(&self) -> Result<(), String> {
        if self.prompt_input.value.trim().is_empty() {
            return Err("System prompt is required".to_string());
        }
        Ok(())
    }

    /// Check if can proceed to next step.
    fn can_proceed(&self) -> bool {
        match self.step {
            Step::BasicDetails => self.validate_basic_details().is_ok(),
            Step::SystemPrompt => self.validate_prompt().is_ok(),
            Step::Review => true,
        }
    }

    /// Go to the next step.
    fn next_step(&mut self) {
        self.validation_error = None;
        match self.step {
            Step::BasicDetails => {
                if let Err(e) = self.validate_basic_details() {
                    self.validation_error = Some(e);
                    return;
                }
                self.name_input.focused = false;
                self.description_input.focused = false;
                self.prompt_input.focused = true;
                self.step = Step::SystemPrompt;
            }
            Step::SystemPrompt => {
                if let Err(e) = self.validate_prompt() {
                    self.validation_error = Some(e);
                    return;
                }
                self.prompt_input.focused = false;
                self.step = Step::Review;
            }
            Step::Review => {
                // Submit - handled separately
            }
        }
    }

    /// Go to the previous step.
    fn prev_step(&mut self) {
        self.validation_error = None;
        match self.step {
            Step::BasicDetails => {
                // Can't go back from first step
            }
            Step::SystemPrompt => {
                self.prompt_input.focused = false;
                self.name_input.focused = true;
                self.basic_focus = BasicDetailsFocus::Name;
                self.step = Step::BasicDetails;
            }
            Step::Review => {
                self.prompt_input.focused = true;
                self.step = Step::SystemPrompt;
            }
        }
    }

    /// Toggle focus between name and description in basic details.
    fn toggle_basic_focus(&mut self) {
        match self.basic_focus {
            BasicDetailsFocus::Name => {
                self.name_input.focused = false;
                self.description_input.focused = true;
                self.basic_focus = BasicDetailsFocus::Description;
            }
            BasicDetailsFocus::Description => {
                self.description_input.focused = false;
                self.name_input.focused = true;
                self.basic_focus = BasicDetailsFocus::Name;
            }
        }
    }

    /// Handle character input.
    fn handle_char(&mut self, c: char) {
        match self.step {
            Step::BasicDetails => match self.basic_focus {
                BasicDetailsFocus::Name => self.name_input.enter_char(c),
                BasicDetailsFocus::Description => self.description_input.enter_char(c),
            },
            Step::SystemPrompt => self.prompt_input.enter_char(c),
            Step::Review => {}
        }
    }

    /// Handle backspace.
    fn handle_backspace(&mut self) {
        match self.step {
            Step::BasicDetails => match self.basic_focus {
                BasicDetailsFocus::Name => self.name_input.delete_char(),
                BasicDetailsFocus::Description => self.description_input.delete_char(),
            },
            Step::SystemPrompt => self.prompt_input.delete_char(),
            Step::Review => {}
        }
    }

    /// Handle delete (forward).
    fn handle_delete(&mut self) {
        match self.step {
            Step::BasicDetails => match self.basic_focus {
                BasicDetailsFocus::Name => self.name_input.delete_char_forward(),
                BasicDetailsFocus::Description => self.description_input.delete_char_forward(),
            },
            Step::SystemPrompt => self.prompt_input.delete_char_forward(),
            Step::Review => {}
        }
    }

    /// Handle left arrow.
    fn handle_left(&mut self) {
        match self.step {
            Step::BasicDetails => match self.basic_focus {
                BasicDetailsFocus::Name => self.name_input.move_cursor_left(),
                BasicDetailsFocus::Description => self.description_input.move_cursor_left(),
            },
            Step::SystemPrompt => self.prompt_input.move_cursor_left(),
            Step::Review => {}
        }
    }

    /// Handle right arrow.
    fn handle_right(&mut self) {
        match self.step {
            Step::BasicDetails => match self.basic_focus {
                BasicDetailsFocus::Name => self.name_input.move_cursor_right(),
                BasicDetailsFocus::Description => self.description_input.move_cursor_right(),
            },
            Step::SystemPrompt => self.prompt_input.move_cursor_right(),
            Step::Review => {}
        }
    }

    /// Tick the spinner animation.
    fn tick_spinner(&mut self) {
        self.spinner_frame = (self.spinner_frame + 1) % 8;
    }
}

/// Event from async submission task.
enum SubmitEvent {
    Success,
    Error(String),
}

/// Run the persona creation TUI wizard.
pub async fn run_create_persona_tui() -> CliResult<()> {
    // Setup terminal
    enable_raw_mode().map_err(|e| CliError::Other(e.to_string()))?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen, EnableMouseCapture)
        .map_err(|e| CliError::Other(e.to_string()))?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend).map_err(|e| CliError::Other(e.to_string()))?;

    // Create wizard state
    let mut wizard = CreatePersonaWizard::new();

    // Run the main loop
    let result = run_wizard_loop(&mut terminal, &mut wizard).await;

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

/// Main wizard event loop.
async fn run_wizard_loop(
    terminal: &mut Terminal<CrosstermBackend<io::Stdout>>,
    wizard: &mut CreatePersonaWizard,
) -> CliResult<()> {
    let (submit_tx, mut submit_rx) = mpsc::channel::<SubmitEvent>(1);

    loop {
        // Draw UI
        terminal
            .draw(|f| render_wizard(f, wizard))
            .map_err(|e| CliError::Other(e.to_string()))?;

        // Handle events with timeout for spinner animation
        let timeout = Duration::from_millis(80);

        tokio::select! {
            // Check for submit events
            Some(event) = submit_rx.recv() => {
                match event {
                    SubmitEvent::Success => {
                        wizard.status = WizardStatus::Idle;
                        wizard.success = true;
                        wizard.should_exit = true;
                    }
                    SubmitEvent::Error(err) => {
                        wizard.status = WizardStatus::Error(err);
                    }
                }
            }

            // Check for terminal events
            _ = tokio::time::sleep(timeout) => {
                // Tick spinner if submitting
                if wizard.status.is_submitting() || wizard.status.is_loading() {
                    wizard.tick_spinner();
                }

                // Poll for keyboard events
                if event::poll(Duration::ZERO).unwrap_or(false) {
                    if let Ok(Event::Key(key)) = event::read() {
                        // Don't handle input while submitting
                        if wizard.status.is_submitting() {
                            continue;
                        }

                        // Clear error state on any key press
                        if wizard.status.is_error() {
                            wizard.status = WizardStatus::Idle;
                        }

                        // Ctrl+C always quits
                        if key.modifiers.contains(KeyModifiers::CONTROL) && key.code == KeyCode::Char('c') {
                            wizard.should_exit = true;
                        } else {
                            match key.code {
                                KeyCode::Esc => {
                                    wizard.should_exit = true;
                                }
                                KeyCode::Enter => {
                                    if wizard.step == Step::SystemPrompt && wizard.prompt_input.multiline {
                                        // In multiline mode, Enter adds a newline
                                        wizard.prompt_input.enter_char('\n');
                                    } else if wizard.step == Step::Review {
                                        // Submit the persona
                                        wizard.status = WizardStatus::Submitting;
                                        let name = wizard.name_input.value.trim().to_string();
                                        let description = wizard.description_input.value.trim().to_string();
                                        let prompt = wizard.prompt_input.value.trim().to_string();
                                        let tx = submit_tx.clone();

                                        tokio::spawn(async move {
                                            match run_create(&name, &description, &prompt, None, None, false).await {
                                                Ok(_) => {
                                                    let _ = tx.send(SubmitEvent::Success).await;
                                                }
                                                Err(e) => {
                                                    let _ = tx.send(SubmitEvent::Error(e.to_string())).await;
                                                }
                                            }
                                        });
                                    } else {
                                        wizard.next_step();
                                    }
                                }
                                KeyCode::Tab => {
                                    if wizard.step == Step::BasicDetails {
                                        wizard.toggle_basic_focus();
                                    } else if wizard.step == Step::SystemPrompt {
                                        // Tab advances to next step from prompt
                                        wizard.next_step();
                                    }
                                }
                                KeyCode::BackTab => {
                                    if wizard.step == Step::BasicDetails {
                                        wizard.toggle_basic_focus();
                                    }
                                }
                                KeyCode::Backspace => {
                                    if wizard.step == Step::BasicDetails && wizard.basic_focus == BasicDetailsFocus::Name && wizard.name_input.value.is_empty() {
                                        // Don't go back from empty name field
                                    } else if wizard.step == Step::SystemPrompt && wizard.prompt_input.value.is_empty() {
                                        wizard.prev_step();
                                    } else {
                                        wizard.handle_backspace();
                                    }
                                }
                                KeyCode::Delete => {
                                    wizard.handle_delete();
                                }
                                KeyCode::Left => {
                                    wizard.handle_left();
                                }
                                KeyCode::Right => {
                                    wizard.handle_right();
                                }
                                KeyCode::Up => {
                                    if wizard.step == Step::BasicDetails {
                                        if wizard.basic_focus == BasicDetailsFocus::Description {
                                            wizard.toggle_basic_focus();
                                        }
                                    }
                                }
                                KeyCode::Down => {
                                    if wizard.step == Step::BasicDetails {
                                        if wizard.basic_focus == BasicDetailsFocus::Name {
                                            wizard.toggle_basic_focus();
                                        }
                                    }
                                }
                                KeyCode::Char(c) => {
                                    wizard.handle_char(c);
                                }
                                _ => {}
                            }
                        }
                    }
                }
            }
        }

        if wizard.should_exit {
            break;
        }
    }

    if wizard.success {
        Ok(())
    } else {
        // User cancelled
        Ok(())
    }
}

/// Render the wizard UI.
fn render_wizard(frame: &mut Frame, wizard: &CreatePersonaWizard) {
    let size = frame.size();

    // Main layout: header, content, footer
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(1), // Header
            Constraint::Min(10),   // Content
            Constraint::Length(1), // Footer
        ])
        .split(size);

    // Render header
    render_wizard_header(
        frame,
        chunks[0],
        wizard.step.title(),
        wizard.step.number(),
        3,
    );

    // Render content based on step
    let content_area = chunks[1];
    match wizard.step {
        Step::BasicDetails => render_basic_details(frame, wizard, content_area),
        Step::SystemPrompt => render_system_prompt(frame, wizard, content_area),
        Step::Review => render_review(frame, wizard, content_area),
    }

    // Render footer
    let can_go_back = wizard.step != Step::BasicDetails;
    let is_last = wizard.step == Step::Review;
    let extra_hints: Vec<(&str, &str)> = match wizard.step {
        Step::BasicDetails => vec![("Tab", "Next field")],
        Step::SystemPrompt => vec![],
        Step::Review => vec![],
    };
    render_wizard_footer(
        frame,
        chunks[2],
        can_go_back,
        wizard.can_proceed(),
        is_last,
        &extra_hints,
    );

    // Render error overlay if present
    if let Some(err) = &wizard.validation_error {
        let error_area = Rect::new(
            content_area.x + 2,
            content_area.y + content_area.height.saturating_sub(3),
            content_area.width.saturating_sub(4),
            2,
        );
        render_error(frame, error_area, err);
    }

    // Render status overlay if submitting
    if wizard.status.is_submitting() {
        render_loading(
            frame,
            content_area,
            "Creating persona...",
            wizard.spinner_frame,
        );
    }

    // Render error status if present
    if let WizardStatus::Error(ref err) = wizard.status {
        // Use a larger area to show the full error message
        let error_height = 10;
        let error_area = Rect::new(
            content_area.x + 2,
            content_area.y + content_area.height.saturating_sub(error_height + 1),
            content_area.width.saturating_sub(4),
            error_height,
        );
        render_error(frame, error_area, err);
    }
}

/// Render basic details step (name and description).
fn render_basic_details(frame: &mut Frame, wizard: &CreatePersonaWizard, area: Rect) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .margin(1)
        .constraints([
            Constraint::Length(3), // Name input
            Constraint::Length(1), // Spacing
            Constraint::Length(3), // Description input
            Constraint::Min(1),    // Remaining space
        ])
        .split(area);

    // Render name input
    wizard.name_input.render(frame, chunks[0]);

    // Render description input
    wizard.description_input.render(frame, chunks[2]);

    // Show name validation hint
    if !wizard.name_input.value.is_empty() {
        if let Err(e) = wizard.validate_name() {
            let hint = Line::from(Span::styled(
                format!("  {}", e),
                Style::default().fg(Color::Red),
            ));
            let hint_area = Rect::new(
                chunks[0].x,
                chunks[0].y + chunks[0].height,
                chunks[0].width,
                1,
            );
            frame.render_widget(Paragraph::new(hint), hint_area);
        }
    }
}

/// Render system prompt step.
fn render_system_prompt(frame: &mut Frame, wizard: &CreatePersonaWizard, area: Rect) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .margin(1)
        .constraints([
            Constraint::Min(5),    // Prompt input (takes most space)
            Constraint::Length(2), // Hint
        ])
        .split(area);

    // Render prompt input
    wizard.prompt_input.render(frame, chunks[0]);

    // Render hint
    let hint = Line::from(vec![
        Span::styled("Tip: ", Style::default().fg(Color::Yellow)),
        Span::styled(
            "Press Enter for new lines. Press Tab to proceed.",
            Style::default().fg(Color::DarkGray),
        ),
    ]);
    frame.render_widget(Paragraph::new(hint), chunks[1]);
}

/// Render review step with summary.
fn render_review(frame: &mut Frame, wizard: &CreatePersonaWizard, area: Rect) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .margin(1)
        .constraints([
            Constraint::Length(3), // Name summary
            Constraint::Length(3), // Description summary
            Constraint::Min(5),    // Prompt summary
        ])
        .split(area);

    // Name summary
    let name_block = Block::default()
        .title(Span::styled(
            " Name ",
            Style::default()
                .fg(Color::Cyan)
                .add_modifier(Modifier::BOLD),
        ))
        .borders(Borders::ALL)
        .border_style(Style::default().fg(Color::DarkGray));
    let name_para = Paragraph::new(wizard.name_input.value.trim())
        .block(name_block)
        .style(Style::default().fg(Color::White));
    frame.render_widget(name_para, chunks[0]);

    // Description summary
    let desc_block = Block::default()
        .title(Span::styled(
            " Description ",
            Style::default()
                .fg(Color::Cyan)
                .add_modifier(Modifier::BOLD),
        ))
        .borders(Borders::ALL)
        .border_style(Style::default().fg(Color::DarkGray));
    let desc_para = Paragraph::new(wizard.description_input.value.trim())
        .block(desc_block)
        .style(Style::default().fg(Color::White))
        .wrap(Wrap { trim: true });
    frame.render_widget(desc_para, chunks[1]);

    // Prompt summary
    let prompt_block = Block::default()
        .title(Span::styled(
            " System Prompt ",
            Style::default()
                .fg(Color::Cyan)
                .add_modifier(Modifier::BOLD),
        ))
        .borders(Borders::ALL)
        .border_style(Style::default().fg(Color::DarkGray));
    let prompt_para = Paragraph::new(wizard.prompt_input.value.trim())
        .block(prompt_block)
        .style(Style::default().fg(Color::White))
        .wrap(Wrap { trim: true });
    frame.render_widget(prompt_para, chunks[2]);
}
