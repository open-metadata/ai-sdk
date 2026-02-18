//! Agent creation TUI wizard.
//!
//! A 4-step wizard for creating new agents:
//! 1. Basic Details - name and description
//! 2. Select Persona - choose from available personas
//! 3. Select Abilities - multi-select from available abilities (optional)
//! 4. Actions - task prompt and bot selection (optional)

use crate::client::{AbilityInfo, BotInfo, MetadataClient, PersonaInfo};
use crate::commands::agents::run_create;
use crate::config::ResolvedConfig;
use crate::error::{CliError, CliResult};
use crate::tui::markdown::render_markdown;
use crate::tui::wizard::{
    render_error, render_loading, render_wizard_footer, render_wizard_header, MultiSelect,
    SelectItem, SingleSelect, TextInput, WizardStatus,
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
    widgets::{Block, Borders, Paragraph},
    Frame, Terminal,
};
use std::io;
use std::time::Duration;
use tokio::sync::mpsc;

/// Wizard step enumeration.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Step {
    BasicDetails,
    SelectPersona,
    SelectAbilities,
    Actions,
}

impl Step {
    fn number(&self) -> usize {
        match self {
            Step::BasicDetails => 1,
            Step::SelectPersona => 2,
            Step::SelectAbilities => 3,
            Step::Actions => 4,
        }
    }

    fn title(&self) -> &'static str {
        match self {
            Step::BasicDetails => "Basic Details",
            Step::SelectPersona => "Select Persona",
            Step::SelectAbilities => "Select Abilities",
            Step::Actions => "Select Bot",
        }
    }
}

/// Focus state for the basic details step.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum BasicDetailsFocus {
    Name,
    Description,
}

/// Agent creation wizard state.
struct CreateAgentWizard {
    /// Current step.
    step: Step,
    /// Name input.
    name_input: TextInput,
    /// Description input.
    description_input: TextInput,
    /// Persona selector.
    persona_select: SingleSelect,
    /// Abilities multi-selector.
    abilities_select: MultiSelect,
    /// Bot selector.
    bot_select: SingleSelect,
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
    /// Loaded personas.
    personas: Vec<PersonaInfo>,
    /// Loaded abilities.
    abilities: Vec<AbilityInfo>,
    /// Loaded bots.
    bots: Vec<BotInfo>,
    /// Whether personas have been loaded.
    personas_loaded: bool,
    /// Whether abilities have been loaded.
    abilities_loaded: bool,
    /// Whether bots have been loaded.
    bots_loaded: bool,
    /// Scroll offset for persona prompt preview.
    prompt_scroll_offset: usize,
}

impl CreateAgentWizard {
    fn new() -> Self {
        let mut name_input = TextInput::new("Name").placeholder("my-agent").required();
        name_input.focused = true;

        let description_input = TextInput::new("Description")
            .placeholder("A helpful agent that...")
            .required();

        let mut persona_select = SingleSelect::new("Select Persona");
        persona_select.focused = false;

        let mut abilities_select = MultiSelect::new("Select Abilities (optional)");
        abilities_select.focused = false;

        let mut bot_select = SingleSelect::new("Select Bot");
        bot_select.focused = false;

        Self {
            step: Step::BasicDetails,
            name_input,
            description_input,
            persona_select,
            abilities_select,
            bot_select,
            basic_focus: BasicDetailsFocus::Name,
            status: WizardStatus::Idle,
            spinner_frame: 0,
            should_exit: false,
            success: false,
            validation_error: None,
            personas: Vec::new(),
            abilities: Vec::new(),
            bots: Vec::new(),
            personas_loaded: false,
            abilities_loaded: false,
            bots_loaded: false,
            prompt_scroll_offset: 0,
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

    /// Validate the persona selection step.
    fn validate_persona(&self) -> Result<(), String> {
        if self.persona_select.selected().is_none() {
            return Err("Please select a persona".to_string());
        }
        Ok(())
    }

    /// Validate the bot selection.
    fn validate_bot(&self) -> Result<(), String> {
        if self.bot_select.selected().is_none() {
            return Err("Please select a bot".to_string());
        }
        Ok(())
    }

    /// Check if can proceed to next step.
    fn can_proceed(&self) -> bool {
        match self.step {
            Step::BasicDetails => self.validate_basic_details().is_ok(),
            Step::SelectPersona => self.validate_persona().is_ok(),
            Step::SelectAbilities => true, // Abilities are optional
            Step::Actions => self.validate_bot().is_ok(),
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
                self.persona_select.focused = true;
                self.step = Step::SelectPersona;
            }
            Step::SelectPersona => {
                if let Err(e) = self.validate_persona() {
                    self.validation_error = Some(e);
                    return;
                }
                self.persona_select.focused = false;
                self.abilities_select.focused = true;
                self.step = Step::SelectAbilities;
            }
            Step::SelectAbilities => {
                self.abilities_select.focused = false;
                self.bot_select.focused = true;
                self.step = Step::Actions;
            }
            Step::Actions => {
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
            Step::SelectPersona => {
                self.persona_select.focused = false;
                self.name_input.focused = true;
                self.basic_focus = BasicDetailsFocus::Name;
                self.step = Step::BasicDetails;
            }
            Step::SelectAbilities => {
                self.abilities_select.focused = false;
                self.persona_select.focused = true;
                self.step = Step::SelectPersona;
            }
            Step::Actions => {
                self.bot_select.focused = false;
                self.abilities_select.focused = true;
                self.step = Step::SelectAbilities;
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
            Step::SelectPersona => {
                self.persona_select.enter_filter_char(c);
            }
            Step::SelectAbilities => {
                self.abilities_select.enter_filter_char(c);
            }
            Step::Actions => {
                self.bot_select.enter_filter_char(c);
            }
        }
    }

    /// Handle backspace.
    fn handle_backspace(&mut self) {
        match self.step {
            Step::BasicDetails => match self.basic_focus {
                BasicDetailsFocus::Name => self.name_input.delete_char(),
                BasicDetailsFocus::Description => self.description_input.delete_char(),
            },
            Step::SelectPersona => {
                if self.persona_select.filter.is_empty() {
                    self.prev_step();
                } else {
                    self.persona_select.delete_filter_char();
                }
            }
            Step::SelectAbilities => {
                if self.abilities_select.filter.is_empty() {
                    self.prev_step();
                } else {
                    self.abilities_select.delete_filter_char();
                }
            }
            Step::Actions => {
                if self.bot_select.filter.is_empty() {
                    self.prev_step();
                } else {
                    self.bot_select.delete_filter_char();
                }
            }
        }
    }

    /// Handle delete (forward).
    fn handle_delete(&mut self) {
        match self.step {
            Step::BasicDetails => match self.basic_focus {
                BasicDetailsFocus::Name => self.name_input.delete_char_forward(),
                BasicDetailsFocus::Description => self.description_input.delete_char_forward(),
            },
            Step::SelectPersona => {}
            Step::SelectAbilities => {}
            Step::Actions => {}
        }
    }

    /// Handle left arrow.
    fn handle_left(&mut self) {
        match self.step {
            Step::BasicDetails => match self.basic_focus {
                BasicDetailsFocus::Name => self.name_input.move_cursor_left(),
                BasicDetailsFocus::Description => self.description_input.move_cursor_left(),
            },
            Step::SelectPersona => {}
            Step::SelectAbilities => {}
            Step::Actions => {}
        }
    }

    /// Handle right arrow.
    fn handle_right(&mut self) {
        match self.step {
            Step::BasicDetails => match self.basic_focus {
                BasicDetailsFocus::Name => self.name_input.move_cursor_right(),
                BasicDetailsFocus::Description => self.description_input.move_cursor_right(),
            },
            Step::SelectPersona => {}
            Step::SelectAbilities => {}
            Step::Actions => {}
        }
    }

    /// Handle up arrow.
    fn handle_up(&mut self) {
        match self.step {
            Step::BasicDetails => {
                if self.basic_focus == BasicDetailsFocus::Description {
                    self.toggle_basic_focus();
                }
            }
            Step::SelectPersona => {
                self.persona_select.select_previous();
                self.reset_prompt_scroll();
            }
            Step::SelectAbilities => {
                self.abilities_select.select_previous();
            }
            Step::Actions => {
                self.bot_select.select_previous();
            }
        }
    }

    /// Handle down arrow.
    fn handle_down(&mut self) {
        match self.step {
            Step::BasicDetails => {
                if self.basic_focus == BasicDetailsFocus::Name {
                    self.toggle_basic_focus();
                }
            }
            Step::SelectPersona => {
                self.persona_select.select_next();
                self.reset_prompt_scroll();
            }
            Step::SelectAbilities => {
                self.abilities_select.select_next();
            }
            Step::Actions => {
                self.bot_select.select_next();
            }
        }
    }

    /// Handle page up for scrolling.
    fn handle_page_up(&mut self) {
        if self.step == Step::SelectPersona {
            // Scroll up by multiple lines
            for _ in 0..5 {
                self.scroll_prompt_up();
            }
        }
    }

    /// Handle page down for scrolling.
    fn handle_page_down(&mut self, visible_lines: usize) {
        if self.step == Step::SelectPersona {
            // Scroll down by multiple lines
            for _ in 0..5 {
                self.scroll_prompt_down(visible_lines);
            }
        }
    }

    /// Get the selected persona name.
    fn selected_persona_name(&self) -> Option<String> {
        self.persona_select.selected().map(|p| p.name.clone())
    }

    /// Get the selected persona's prompt for preview.
    fn selected_persona_prompt(&self) -> Option<String> {
        if let Some(selected) = self.persona_select.selected() {
            // Find the full persona info
            self.personas
                .iter()
                .find(|p| p.name == selected.name)
                .and_then(|p| p.prompt.clone())
        } else {
            None
        }
    }

    /// Get the selected abilities.
    fn selected_abilities(&self) -> Vec<String> {
        self.abilities_select
            .selected_items()
            .iter()
            .map(|item| item.name.clone())
            .collect()
    }

    /// Get the selected bot name.
    fn selected_bot_name(&self) -> Option<String> {
        self.bot_select.selected().map(|b| b.name.clone())
    }

    /// Tick the spinner animation.
    fn tick_spinner(&mut self) {
        self.spinner_frame = (self.spinner_frame + 1) % 8;
    }

    /// Scroll the persona prompt preview up.
    fn scroll_prompt_up(&mut self) {
        if self.prompt_scroll_offset > 0 {
            self.prompt_scroll_offset = self.prompt_scroll_offset.saturating_sub(1);
        }
    }

    /// Scroll the persona prompt preview down.
    fn scroll_prompt_down(&mut self, max_lines: usize) {
        if let Some(prompt) = self.selected_persona_prompt() {
            // Compute rendered line count using same width estimate as render function
            let rendered_lines = render_markdown(&prompt, 80);
            let total_lines = rendered_lines.len();
            if total_lines > max_lines && self.prompt_scroll_offset + max_lines < total_lines {
                self.prompt_scroll_offset += 1;
            }
        }
    }

    /// Reset prompt scroll when persona changes.
    fn reset_prompt_scroll(&mut self) {
        self.prompt_scroll_offset = 0;
    }

    /// Set personas from API response.
    fn set_personas(&mut self, personas: Vec<PersonaInfo>) {
        self.personas = personas.clone();
        let items: Vec<SelectItem> = personas
            .into_iter()
            .map(|p| {
                let display = p.display_name.clone().unwrap_or_else(|| p.name.clone());
                let mut item = SelectItem::new(
                    p.id.clone().unwrap_or_else(|| p.name.clone()),
                    p.name.clone(),
                )
                .display_name(display);
                if let Some(desc) = p.description {
                    item = item.description(desc);
                }
                item
            })
            .collect();
        self.persona_select.set_items(items);
        self.personas_loaded = true;
    }

    /// Set abilities from API response.
    fn set_abilities(&mut self, abilities: Vec<AbilityInfo>) {
        self.abilities = abilities.clone();
        let items: Vec<SelectItem> = abilities
            .into_iter()
            .map(|a| {
                let display = a.display_name.clone().unwrap_or_else(|| a.name.clone());
                let mut item = SelectItem::new(
                    a.id.clone().unwrap_or_else(|| a.name.clone()),
                    a.name.clone(),
                )
                .display_name(display);
                if let Some(desc) = a.description {
                    item = item.description(desc);
                }
                item
            })
            .collect();
        self.abilities_select.set_items(items);
        self.abilities_loaded = true;
    }

    /// Set bots from API response.
    fn set_bots(&mut self, bots: Vec<BotInfo>) {
        self.bots = bots.clone();
        let items: Vec<SelectItem> = bots
            .into_iter()
            .map(|b| {
                let display = b.display_name.clone().unwrap_or_else(|| b.name.clone());
                let mut item = SelectItem::new(
                    b.id.clone().unwrap_or_else(|| b.name.clone()),
                    b.name.clone(),
                )
                .display_name(display);
                if let Some(desc) = b.description {
                    item = item.description(desc);
                }
                item
            })
            .collect();
        self.bot_select.set_items(items);
        self.bots_loaded = true;
    }
}

/// Event from async operations.
enum AsyncEvent {
    PersonasLoaded(Result<Vec<PersonaInfo>, String>),
    AbilitiesLoaded(Result<Vec<AbilityInfo>, String>),
    BotsLoaded(Result<Vec<BotInfo>, String>),
    SubmitSuccess,
    SubmitError(String),
}

/// Run the agent creation TUI wizard.
pub async fn run_create_agent_tui() -> CliResult<()> {
    // Setup terminal
    enable_raw_mode().map_err(|e| CliError::Other(e.to_string()))?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen, EnableMouseCapture)
        .map_err(|e| CliError::Other(e.to_string()))?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend).map_err(|e| CliError::Other(e.to_string()))?;

    // Create wizard state
    let mut wizard = CreateAgentWizard::new();

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
    wizard: &mut CreateAgentWizard,
) -> CliResult<()> {
    let (async_tx, mut async_rx) = mpsc::channel::<AsyncEvent>(4);

    loop {
        // Check if we need to load data for the current step
        if wizard.step == Step::SelectPersona
            && !wizard.personas_loaded
            && !wizard.status.is_loading()
        {
            wizard.status = WizardStatus::Loading("Loading personas...".to_string());
            let tx = async_tx.clone();
            tokio::spawn(async move {
                let result = load_personas().await;
                let _ = tx.send(AsyncEvent::PersonasLoaded(result)).await;
            });
        }

        if wizard.step == Step::SelectAbilities
            && !wizard.abilities_loaded
            && !wizard.status.is_loading()
        {
            wizard.status = WizardStatus::Loading("Loading abilities...".to_string());
            let tx = async_tx.clone();
            tokio::spawn(async move {
                let result = load_abilities().await;
                let _ = tx.send(AsyncEvent::AbilitiesLoaded(result)).await;
            });
        }

        if wizard.step == Step::Actions && !wizard.bots_loaded && !wizard.status.is_loading() {
            wizard.status = WizardStatus::Loading("Loading bots...".to_string());
            let tx = async_tx.clone();
            tokio::spawn(async move {
                let result = load_bots().await;
                let _ = tx.send(AsyncEvent::BotsLoaded(result)).await;
            });
        }

        // Draw UI
        terminal
            .draw(|f| render_wizard(f, wizard))
            .map_err(|e| CliError::Other(e.to_string()))?;

        // Handle events with timeout for spinner animation
        let timeout = Duration::from_millis(80);

        tokio::select! {
            // Check for async events
            Some(event) = async_rx.recv() => {
                match event {
                    AsyncEvent::PersonasLoaded(Ok(personas)) => {
                        wizard.set_personas(personas);
                        wizard.status = WizardStatus::Idle;
                    }
                    AsyncEvent::PersonasLoaded(Err(e)) => {
                        wizard.status = WizardStatus::Error(e);
                    }
                    AsyncEvent::AbilitiesLoaded(Ok(abilities)) => {
                        wizard.set_abilities(abilities);
                        wizard.status = WizardStatus::Idle;
                    }
                    AsyncEvent::AbilitiesLoaded(Err(e)) => {
                        wizard.status = WizardStatus::Error(e);
                    }
                    AsyncEvent::BotsLoaded(Ok(bots)) => {
                        wizard.set_bots(bots);
                        wizard.status = WizardStatus::Idle;
                    }
                    AsyncEvent::BotsLoaded(Err(e)) => {
                        wizard.status = WizardStatus::Error(e);
                    }
                    AsyncEvent::SubmitSuccess => {
                        wizard.status = WizardStatus::Idle;
                        wizard.success = true;
                        wizard.should_exit = true;
                    }
                    AsyncEvent::SubmitError(err) => {
                        wizard.status = WizardStatus::Error(err);
                    }
                }
            }

            // Check for terminal events
            _ = tokio::time::sleep(timeout) => {
                // Tick spinner if submitting or loading
                if wizard.status.is_submitting() || wizard.status.is_loading() {
                    wizard.tick_spinner();
                }

                // Poll for keyboard events
                if event::poll(Duration::ZERO).unwrap_or(false) {
                    if let Ok(Event::Key(key)) = event::read() {
                        // Don't handle input while submitting or loading
                        if wizard.status.is_submitting() || wizard.status.is_loading() {
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
                                    if wizard.step == Step::Actions {
                                        // Validate before submitting
                                        if let Err(e) = wizard.validate_bot() {
                                            wizard.validation_error = Some(e);
                                            continue;
                                        }
                                        // Submit the agent
                                        wizard.status = WizardStatus::Submitting;
                                        let name = wizard.name_input.value.trim().to_string();
                                        let description = wizard.description_input.value.trim().to_string();
                                        let persona = wizard.selected_persona_name().unwrap_or_default();
                                        let abilities = wizard.selected_abilities();
                                        let abilities_opt = if abilities.is_empty() {
                                            None
                                        } else {
                                            Some(abilities)
                                        };
                                        let bot_name = wizard.selected_bot_name();
                                        let tx = async_tx.clone();

                                        tokio::spawn(async move {
                                            match run_create(
                                                &name,
                                                &description,
                                                &persona,
                                                "chat",  // Hardcoded mode
                                                None,    // display_name
                                                None,    // icon
                                                bot_name.as_deref(),
                                                abilities_opt,
                                                Some(true), // api_enabled always true
                                                None,    // provider
                                                false,   // json output
                                            ).await {
                                                Ok(_) => {
                                                    let _ = tx.send(AsyncEvent::SubmitSuccess).await;
                                                }
                                                Err(e) => {
                                                    let _ = tx.send(AsyncEvent::SubmitError(e.to_string())).await;
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
                                    } else {
                                        wizard.next_step();
                                    }
                                }
                                KeyCode::BackTab => {
                                    if wizard.step == Step::BasicDetails {
                                        wizard.toggle_basic_focus();
                                    }
                                }
                                KeyCode::Backspace => {
                                    wizard.handle_backspace();
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
                                    if key.modifiers.contains(KeyModifiers::CONTROL) && wizard.step == Step::SelectPersona {
                                        wizard.scroll_prompt_up();
                                    } else {
                                        wizard.handle_up();
                                    }
                                }
                                KeyCode::Down => {
                                    if key.modifiers.contains(KeyModifiers::CONTROL) && wizard.step == Step::SelectPersona {
                                        // Estimate visible lines based on area (will be approximate)
                                        wizard.scroll_prompt_down(10);
                                    } else {
                                        wizard.handle_down();
                                    }
                                }
                                KeyCode::PageUp => {
                                    wizard.handle_page_up();
                                }
                                KeyCode::PageDown => {
                                    wizard.handle_page_down(10);
                                }
                                KeyCode::Char(' ') => {
                                    if wizard.step == Step::SelectAbilities {
                                        wizard.abilities_select.toggle_current();
                                    } else {
                                        wizard.handle_char(' ');
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

/// Load personas from API.
async fn load_personas() -> Result<Vec<PersonaInfo>, String> {
    let config = ResolvedConfig::load().map_err(|e| e.to_string())?;
    let client = MetadataClient::new(&config).map_err(|e| e.to_string())?;
    // Fetch all personas with automatic pagination
    client.list_personas().await.map_err(|e| e.to_string())
}

/// Load abilities from API.
async fn load_abilities() -> Result<Vec<AbilityInfo>, String> {
    let config = ResolvedConfig::load().map_err(|e| e.to_string())?;
    let client = MetadataClient::new(&config).map_err(|e| e.to_string())?;
    // Fetch all abilities with automatic pagination
    client.list_abilities().await.map_err(|e| e.to_string())
}

/// Load bots from API.
async fn load_bots() -> Result<Vec<BotInfo>, String> {
    let config = ResolvedConfig::load().map_err(|e| e.to_string())?;
    let client = MetadataClient::new(&config).map_err(|e| e.to_string())?;
    // Fetch all bots with automatic pagination
    client.list_bots().await.map_err(|e| e.to_string())
}

/// Render the wizard UI.
fn render_wizard(frame: &mut Frame, wizard: &mut CreateAgentWizard) {
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
        4,
    );

    // Render content based on step
    let content_area = chunks[1];
    match wizard.step {
        Step::BasicDetails => render_basic_details(frame, wizard, content_area),
        Step::SelectPersona => render_select_persona(frame, wizard, content_area),
        Step::SelectAbilities => render_select_abilities(frame, wizard, content_area),
        Step::Actions => render_actions(frame, wizard, content_area),
    }

    // Render footer
    let can_go_back = wizard.step != Step::BasicDetails;
    let is_last = wizard.step == Step::Actions;
    let extra_hints: Vec<(&str, &str)> = match wizard.step {
        Step::BasicDetails => vec![("Tab", "Next field")],
        Step::SelectPersona => vec![("PgUp/PgDn", "Scroll prompt")],
        Step::SelectAbilities => vec![("Space", "Toggle")],
        Step::Actions => vec![],
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

    // Render status overlay if submitting or loading
    if wizard.status.is_submitting() {
        render_loading(
            frame,
            content_area,
            "Creating agent...",
            wizard.spinner_frame,
        );
    } else if let Some(msg) = wizard.status.loading_message() {
        render_loading(frame, content_area, msg, wizard.spinner_frame);
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
fn render_basic_details(frame: &mut Frame, wizard: &CreateAgentWizard, area: Rect) {
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
                format!("  {e}"),
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

/// Render select persona step.
fn render_select_persona(frame: &mut Frame, wizard: &mut CreateAgentWizard, area: Rect) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .margin(1)
        .constraints([
            Constraint::Percentage(50), // Persona list
            Constraint::Percentage(50), // Prompt preview (scrollable)
        ])
        .split(area);

    // Render persona selector
    wizard.persona_select.render(frame, chunks[0]);

    // Render prompt preview if a persona is selected
    if let Some(prompt) = wizard.selected_persona_prompt() {
        let inner_height = chunks[1].height.saturating_sub(2) as usize; // Account for borders
        let inner_width = chunks[1].width.saturating_sub(2) as usize; // Account for borders

        // Render markdown to styled lines
        let rendered_lines = render_markdown(&prompt, inner_width);
        let total_lines = rendered_lines.len();

        let scroll_indicator = if total_lines > inner_height {
            format!(
                " Prompt Preview (↑↓ scroll, {}/{}) ",
                wizard.prompt_scroll_offset + 1,
                total_lines.saturating_sub(inner_height) + 1
            )
        } else {
            " Prompt Preview ".to_string()
        };

        let preview_block = Block::default()
            .title(Span::styled(
                scroll_indicator,
                Style::default()
                    .fg(Color::Yellow)
                    .add_modifier(Modifier::BOLD),
            ))
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::DarkGray));

        // Apply scroll offset to rendered lines
        let visible_lines: Vec<Line> = rendered_lines
            .into_iter()
            .skip(wizard.prompt_scroll_offset)
            .take(inner_height)
            .collect();

        let preview_para = Paragraph::new(visible_lines).block(preview_block);

        frame.render_widget(preview_para, chunks[1]);
    } else {
        let placeholder = Block::default()
            .title(Span::styled(
                " Prompt Preview ",
                Style::default().fg(Color::DarkGray),
            ))
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::DarkGray));

        frame.render_widget(placeholder, chunks[1]);
    }
}

/// Render select abilities step.
fn render_select_abilities(frame: &mut Frame, wizard: &mut CreateAgentWizard, area: Rect) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .margin(1)
        .constraints([
            Constraint::Min(8),    // Abilities list
            Constraint::Length(2), // Hint
        ])
        .split(area);

    // Render abilities multi-selector
    wizard.abilities_select.render(frame, chunks[0]);

    // Render hint
    let hint = Line::from(vec![
        Span::styled("Tip: ", Style::default().fg(Color::Yellow)),
        Span::styled(
            "Press Space to toggle selection. This step is optional - press Enter to skip.",
            Style::default().fg(Color::DarkGray),
        ),
    ]);
    frame.render_widget(Paragraph::new(hint), chunks[1]);
}

/// Render actions step (bot selection).
fn render_actions(frame: &mut Frame, wizard: &mut CreateAgentWizard, area: Rect) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .margin(1)
        .constraints([
            Constraint::Min(10),   // Bot selector
            Constraint::Length(2), // Hint
        ])
        .split(area);

    // Render bot selector
    wizard.bot_select.render(frame, chunks[0]);

    // Render hint
    let hint = Line::from(vec![
        Span::styled("Tip: ", Style::default().fg(Color::Yellow)),
        Span::styled(
            "Select a bot and press Enter to create the agent.",
            Style::default().fg(Color::DarkGray),
        ),
    ]);
    frame.render_widget(Paragraph::new(hint), chunks[1]);
}
