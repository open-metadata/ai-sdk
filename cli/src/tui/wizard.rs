//! Reusable wizard components for TUI forms.
//!
//! This module provides common UI components for building multi-step wizards:
//! - `TextInput` - Single and multiline text input with cursor management
//! - `SingleSelect` - Filterable single-item selection list
//! - `MultiSelect` - Filterable multi-item selection with checkboxes
//! - Helper functions for consistent wizard header/footer rendering

use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, ListState, Paragraph, Wrap},
    Frame,
};

/// Status of a wizard operation.
#[derive(Debug, Clone)]
pub enum WizardStatus {
    /// Wizard is idle, waiting for user input.
    Idle,
    /// Wizard is loading data (e.g., fetching options).
    Loading(String),
    /// Wizard is submitting the form.
    Submitting,
    /// Wizard encountered an error.
    Error(String),
}

impl Default for WizardStatus {
    fn default() -> Self {
        Self::Idle
    }
}

impl WizardStatus {
    /// Check if the wizard is in a loading state.
    pub fn is_loading(&self) -> bool {
        matches!(self, Self::Loading(_))
    }

    /// Check if the wizard is submitting.
    pub fn is_submitting(&self) -> bool {
        matches!(self, Self::Submitting)
    }

    /// Check if the wizard has an error.
    pub fn is_error(&self) -> bool {
        matches!(self, Self::Error(_))
    }

    /// Get the loading message if in loading state.
    pub fn loading_message(&self) -> Option<&str> {
        match self {
            Self::Loading(msg) => Some(msg),
            _ => None,
        }
    }
}

// =============================================================================
// TextInput
// =============================================================================

/// A text input field with cursor management.
#[derive(Debug, Clone)]
pub struct TextInput {
    /// Current input value.
    pub value: String,
    /// Cursor position within the value.
    pub cursor: usize,
    /// Label displayed above the input.
    pub label: String,
    /// Placeholder text shown when empty.
    pub placeholder: String,
    /// Whether this field is required.
    pub required: bool,
    /// Whether this is a multiline input.
    pub multiline: bool,
    /// Whether this input is currently focused.
    pub focused: bool,
}

impl TextInput {
    /// Create a new text input with the given label.
    pub fn new(label: impl Into<String>) -> Self {
        Self {
            value: String::new(),
            cursor: 0,
            label: label.into(),
            placeholder: String::new(),
            required: false,
            multiline: false,
            focused: false,
        }
    }

    /// Set the placeholder text.
    pub fn placeholder(mut self, placeholder: impl Into<String>) -> Self {
        self.placeholder = placeholder.into();
        self
    }

    /// Mark this field as required.
    pub fn required(mut self) -> Self {
        self.required = true;
        self
    }

    /// Enable multiline input.
    pub fn multiline(mut self) -> Self {
        self.multiline = true;
        self
    }

    /// Insert a character at the cursor position.
    pub fn enter_char(&mut self, c: char) {
        // For multiline, allow newlines; for single line, ignore them
        if c == '\n' && !self.multiline {
            return;
        }
        self.value.insert(self.cursor, c);
        self.cursor += c.len_utf8();
    }

    /// Delete the character before the cursor.
    pub fn delete_char(&mut self) {
        if self.cursor > 0 {
            // Find the previous character boundary
            let mut prev_cursor = self.cursor - 1;
            while prev_cursor > 0 && !self.value.is_char_boundary(prev_cursor) {
                prev_cursor -= 1;
            }
            self.value.remove(prev_cursor);
            self.cursor = prev_cursor;
        }
    }

    /// Delete the character at the cursor (forward delete).
    pub fn delete_char_forward(&mut self) {
        if self.cursor < self.value.len() {
            self.value.remove(self.cursor);
        }
    }

    /// Move the cursor left by one character.
    pub fn move_cursor_left(&mut self) {
        if self.cursor > 0 {
            // Find the previous character boundary
            let mut new_cursor = self.cursor - 1;
            while new_cursor > 0 && !self.value.is_char_boundary(new_cursor) {
                new_cursor -= 1;
            }
            self.cursor = new_cursor;
        }
    }

    /// Move the cursor right by one character.
    pub fn move_cursor_right(&mut self) {
        if self.cursor < self.value.len() {
            // Find the next character boundary
            let mut new_cursor = self.cursor + 1;
            while new_cursor < self.value.len() && !self.value.is_char_boundary(new_cursor) {
                new_cursor += 1;
            }
            self.cursor = new_cursor;
        }
    }

    /// Check if the input is valid (non-empty if required).
    pub fn is_valid(&self) -> bool {
        if self.required {
            !self.value.trim().is_empty()
        } else {
            true
        }
    }

    /// Render the text input widget.
    pub fn render(&self, frame: &mut Frame, area: Rect) {
        let border_style = if self.focused {
            Style::default().fg(Color::Cyan)
        } else if !self.is_valid() {
            Style::default().fg(Color::Red)
        } else {
            Style::default().fg(Color::DarkGray)
        };

        let label_style = if self.focused {
            Style::default()
                .fg(Color::Cyan)
                .add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(Color::White)
        };

        let required_marker = if self.required { " *" } else { "" };
        let title = format!(" {}{} ", self.label, required_marker);

        let block = Block::default()
            .title(Span::styled(title, label_style))
            .borders(Borders::ALL)
            .border_style(border_style);

        let inner_area = block.inner(area);

        // Determine what text to display
        let (display_text, text_style) = if self.value.is_empty() && !self.focused {
            // Show placeholder when empty and not focused
            (
                self.placeholder.clone(),
                Style::default().fg(Color::DarkGray),
            )
        } else if self.value.is_empty() && self.focused {
            // Show placeholder in lighter color when focused but empty
            (
                self.placeholder.clone(),
                Style::default()
                    .fg(Color::DarkGray)
                    .add_modifier(Modifier::ITALIC),
            )
        } else {
            (self.value.clone(), Style::default())
        };

        let paragraph = if self.multiline {
            Paragraph::new(display_text)
                .style(text_style)
                .wrap(Wrap { trim: false })
        } else {
            Paragraph::new(display_text).style(text_style)
        };

        frame.render_widget(block, area);
        frame.render_widget(paragraph, inner_area);

        // Set cursor position if focused
        if self.focused {
            // Calculate cursor position considering the inner area
            let cursor_x = if self.multiline {
                // For multiline, calculate position based on current line
                let lines: Vec<&str> = self.value[..self.cursor].split('\n').collect();
                let current_line = lines.last().unwrap_or(&"");
                inner_area.x + current_line.len() as u16
            } else {
                inner_area.x + self.cursor as u16
            };

            let cursor_y = if self.multiline {
                let lines_before_cursor = self.value[..self.cursor].matches('\n').count();
                inner_area.y + lines_before_cursor as u16
            } else {
                inner_area.y
            };

            // Only set cursor if it's within bounds
            if cursor_x < inner_area.x + inner_area.width
                && cursor_y < inner_area.y + inner_area.height
            {
                frame.set_cursor(cursor_x, cursor_y);
            }
        }
    }
}

// =============================================================================
// SelectItem
// =============================================================================

/// An item that can be selected in a list.
#[derive(Debug, Clone)]
pub struct SelectItem {
    /// Unique identifier for the item.
    pub id: String,
    /// Internal name (used for matching).
    pub name: String,
    /// Display name shown in the list.
    pub display_name: String,
    /// Optional description shown below the name.
    pub description: Option<String>,
}

impl SelectItem {
    /// Create a new select item.
    pub fn new(id: impl Into<String>, name: impl Into<String>) -> Self {
        let name = name.into();
        Self {
            id: id.into(),
            display_name: name.clone(),
            name,
            description: None,
        }
    }

    /// Set a custom display name.
    pub fn display_name(mut self, display_name: impl Into<String>) -> Self {
        self.display_name = display_name.into();
        self
    }

    /// Set a description.
    pub fn description(mut self, description: impl Into<String>) -> Self {
        self.description = Some(description.into());
        self
    }
}

// =============================================================================
// SingleSelect
// =============================================================================

/// A single-selection list with filtering support and virtual scrolling.
#[derive(Debug, Clone)]
pub struct SingleSelect {
    /// All available items.
    items: Vec<SelectItem>,
    /// Current filter text.
    pub filter: String,
    /// Cursor position in the filter.
    pub filter_cursor: usize,
    /// List state for tracking selection.
    state: ListState,
    /// Label displayed above the list.
    pub label: String,
    /// Whether this select is currently focused.
    pub focused: bool,
    /// Scroll offset for virtual scrolling.
    scroll_offset: usize,
}

impl SingleSelect {
    /// Create a new single select with the given label.
    pub fn new(label: impl Into<String>) -> Self {
        let mut state = ListState::default();
        state.select(Some(0));
        Self {
            items: Vec::new(),
            filter: String::new(),
            filter_cursor: 0,
            state,
            label: label.into(),
            focused: false,
            scroll_offset: 0,
        }
    }

    /// Set the available items.
    pub fn set_items(&mut self, items: Vec<SelectItem>) {
        self.items = items;
        self.filter.clear();
        self.filter_cursor = 0;
        self.state.select(Some(0));
        self.scroll_offset = 0;
    }

    /// Get items filtered by the current filter text.
    pub fn filtered_items(&self) -> Vec<&SelectItem> {
        let filter_lower = self.filter.to_lowercase();
        self.items
            .iter()
            .filter(|item| {
                if filter_lower.is_empty() {
                    true
                } else {
                    item.name.to_lowercase().contains(&filter_lower)
                        || item.display_name.to_lowercase().contains(&filter_lower)
                        || item
                            .description
                            .as_ref()
                            .map(|d| d.to_lowercase().contains(&filter_lower))
                            .unwrap_or(false)
                }
            })
            .collect()
    }

    /// Get the currently selected item.
    pub fn selected(&self) -> Option<&SelectItem> {
        let filtered = self.filtered_items();
        self.state.selected().and_then(|i| filtered.get(i).copied())
    }

    /// Move selection to the next item.
    pub fn select_next(&mut self) {
        self.select_next_with_height(10) // Default height, will be adjusted in render
    }

    /// Move selection to the next item with known visible height.
    pub fn select_next_with_height(&mut self, visible_height: usize) {
        let filtered_len = self.filtered_items().len();
        if filtered_len == 0 {
            return;
        }
        let current = self.state.selected().unwrap_or(0);
        let next = if current >= filtered_len - 1 {
            self.scroll_offset = 0; // Wrap to top
            0
        } else {
            current + 1
        };
        self.state.select(Some(next));
        self.ensure_visible(next, visible_height, filtered_len);
    }

    /// Move selection to the previous item.
    pub fn select_previous(&mut self) {
        self.select_previous_with_height(10) // Default height, will be adjusted in render
    }

    /// Move selection to the previous item with known visible height.
    pub fn select_previous_with_height(&mut self, visible_height: usize) {
        let filtered_len = self.filtered_items().len();
        if filtered_len == 0 {
            return;
        }
        let current = self.state.selected().unwrap_or(0);
        let prev = if current == 0 {
            let last = filtered_len - 1;
            // Wrap to bottom - scroll to show the last item
            self.scroll_offset = filtered_len.saturating_sub(visible_height);
            last
        } else {
            current - 1
        };
        self.state.select(Some(prev));
        self.ensure_visible(prev, visible_height, filtered_len);
    }

    /// Ensure the selected index is visible in the viewport.
    fn ensure_visible(&mut self, selected: usize, visible_height: usize, total: usize) {
        if total <= visible_height {
            self.scroll_offset = 0;
            return;
        }
        // If selected is above viewport, scroll up
        if selected < self.scroll_offset {
            self.scroll_offset = selected;
        }
        // If selected is below viewport, scroll down
        else if selected >= self.scroll_offset + visible_height {
            self.scroll_offset = selected.saturating_sub(visible_height) + 1;
        }
    }

    /// Add a character to the filter.
    pub fn enter_filter_char(&mut self, c: char) {
        self.filter.insert(self.filter_cursor, c);
        self.filter_cursor += c.len_utf8();
        // Reset selection and scroll when filter changes
        self.state.select(Some(0));
        self.scroll_offset = 0;
    }

    /// Delete the character before the cursor in the filter.
    pub fn delete_filter_char(&mut self) {
        if self.filter_cursor > 0 {
            let mut prev_cursor = self.filter_cursor - 1;
            while prev_cursor > 0 && !self.filter.is_char_boundary(prev_cursor) {
                prev_cursor -= 1;
            }
            self.filter.remove(prev_cursor);
            self.filter_cursor = prev_cursor;
            // Reset selection and scroll when filter changes
            self.state.select(Some(0));
            self.scroll_offset = 0;
        }
    }

    /// Render the single select widget with virtual scrolling.
    pub fn render(&mut self, frame: &mut Frame, area: Rect) {
        let border_style = if self.focused {
            Style::default().fg(Color::Cyan)
        } else {
            Style::default().fg(Color::DarkGray)
        };

        let label_style = if self.focused {
            Style::default()
                .fg(Color::Cyan)
                .add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(Color::White)
        };

        let title = format!(" {} ", self.label);

        let block = Block::default()
            .title(Span::styled(title, label_style))
            .borders(Borders::ALL)
            .border_style(border_style);

        let inner_area = block.inner(area);
        frame.render_widget(block, area);

        // Split inner area: filter input + list
        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([Constraint::Length(1), Constraint::Min(1)])
            .split(inner_area);

        // Render filter input
        let filter_text = if self.filter.is_empty() && self.focused {
            Span::styled("Type to filter...", Style::default().fg(Color::DarkGray))
        } else if self.filter.is_empty() {
            Span::styled("", Style::default())
        } else {
            Span::styled(&self.filter, Style::default().fg(Color::Yellow))
        };

        let filter_line = Line::from(vec![
            Span::styled("/ ", Style::default().fg(Color::DarkGray)),
            filter_text,
        ]);

        frame.render_widget(Paragraph::new(filter_line), chunks[0]);

        // Calculate visible height for virtual scrolling
        let list_area = chunks[1];

        // Get item count and calculate lines per item (needs a quick scan)
        let total_items = self.filtered_items().len();
        let has_descriptions = self.items.first().map(|i| i.description.is_some()).unwrap_or(false);
        let lines_per_item = if has_descriptions { 2usize } else { 1usize };
        let visible_items = (list_area.height as usize) / lines_per_item.max(1);

        // Ensure selection is visible (modifies scroll_offset)
        let selected = self.state.selected().unwrap_or(0);
        self.ensure_visible(selected, visible_items, total_items);

        // Now get filtered items for rendering (after ensure_visible modified scroll_offset)
        let filtered = self.filtered_items();
        let visible_end = (self.scroll_offset + visible_items).min(total_items);
        let items: Vec<ListItem> = filtered
            .iter()
            .skip(self.scroll_offset)
            .take(visible_items)
            .map(|item| {
                let mut lines = vec![Line::from(Span::raw(&item.display_name))];
                if let Some(desc) = &item.description {
                    lines.push(Line::from(Span::styled(
                        truncate_str(desc, inner_area.width.saturating_sub(4) as usize),
                        Style::default().fg(Color::DarkGray),
                    )));
                }
                ListItem::new(lines)
            })
            .collect();

        let highlight_style = Style::default()
            .fg(Color::Black)
            .bg(Color::Cyan)
            .add_modifier(Modifier::BOLD);

        let list = List::new(items)
            .highlight_symbol("> ")
            .highlight_style(highlight_style);

        // Adjust selection state for the visible window
        let mut state = ListState::default();
        if selected >= self.scroll_offset && selected < visible_end {
            state.select(Some(selected - self.scroll_offset));
        }
        frame.render_stateful_widget(list, list_area, &mut state);

        // Render scroll indicators if needed
        if total_items > visible_items {
            let above = self.scroll_offset;
            let below = total_items.saturating_sub(visible_end);

            if above > 0 {
                let indicator = format!("▲ {} more", above);
                frame.render_widget(
                    Paragraph::new(Span::styled(indicator, Style::default().fg(Color::DarkGray))),
                    Rect::new(list_area.x + list_area.width.saturating_sub(12), list_area.y, 12, 1),
                );
            }
            if below > 0 {
                let indicator = format!("▼ {} more", below);
                let y = list_area.y + list_area.height.saturating_sub(1);
                frame.render_widget(
                    Paragraph::new(Span::styled(indicator, Style::default().fg(Color::DarkGray))),
                    Rect::new(list_area.x + list_area.width.saturating_sub(12), y, 12, 1),
                );
            }
        }

        // Set cursor position in filter if focused
        if self.focused {
            frame.set_cursor(chunks[0].x + 2 + self.filter_cursor as u16, chunks[0].y);
        }
    }
}

// =============================================================================
// MultiSelect
// =============================================================================

/// A multi-selection list with filtering, checkboxes, and virtual scrolling.
#[derive(Debug, Clone)]
pub struct MultiSelect {
    /// All available items.
    items: Vec<SelectItem>,
    /// IDs of selected items.
    selected_ids: Vec<String>,
    /// Current filter text.
    pub filter: String,
    /// Cursor position in the filter.
    pub filter_cursor: usize,
    /// List state for tracking cursor position.
    state: ListState,
    /// Label displayed above the list.
    pub label: String,
    /// Whether this select is currently focused.
    pub focused: bool,
    /// Scroll offset for virtual scrolling.
    scroll_offset: usize,
}

impl MultiSelect {
    /// Create a new multi select with the given label.
    pub fn new(label: impl Into<String>) -> Self {
        let mut state = ListState::default();
        state.select(Some(0));
        Self {
            items: Vec::new(),
            selected_ids: Vec::new(),
            filter: String::new(),
            filter_cursor: 0,
            state,
            label: label.into(),
            focused: false,
            scroll_offset: 0,
        }
    }

    /// Set the available items.
    pub fn set_items(&mut self, items: Vec<SelectItem>) {
        self.items = items;
        self.selected_ids.clear();
        self.filter.clear();
        self.filter_cursor = 0;
        self.state.select(Some(0));
        self.scroll_offset = 0;
    }

    /// Get items filtered by the current filter text.
    pub fn filtered_items(&self) -> Vec<&SelectItem> {
        let filter_lower = self.filter.to_lowercase();
        self.items
            .iter()
            .filter(|item| {
                if filter_lower.is_empty() {
                    true
                } else {
                    item.name.to_lowercase().contains(&filter_lower)
                        || item.display_name.to_lowercase().contains(&filter_lower)
                        || item
                            .description
                            .as_ref()
                            .map(|d| d.to_lowercase().contains(&filter_lower))
                            .unwrap_or(false)
                }
            })
            .collect()
    }

    /// Toggle selection of the currently highlighted item.
    pub fn toggle_current(&mut self) {
        let filtered = self.filtered_items();
        if let Some(index) = self.state.selected() {
            if let Some(item) = filtered.get(index) {
                let id = item.id.clone();
                if self.selected_ids.contains(&id) {
                    self.selected_ids.retain(|x| x != &id);
                } else {
                    self.selected_ids.push(id);
                }
            }
        }
    }

    /// Check if an item is selected by its ID.
    pub fn is_selected(&self, id: &str) -> bool {
        self.selected_ids.contains(&id.to_string())
    }

    /// Move selection to the next item.
    pub fn select_next(&mut self) {
        self.select_next_with_height(10) // Default height, will be adjusted in render
    }

    /// Move selection to the next item with known visible height.
    pub fn select_next_with_height(&mut self, visible_height: usize) {
        let filtered_len = self.filtered_items().len();
        if filtered_len == 0 {
            return;
        }
        let current = self.state.selected().unwrap_or(0);
        let next = if current >= filtered_len - 1 {
            self.scroll_offset = 0; // Wrap to top
            0
        } else {
            current + 1
        };
        self.state.select(Some(next));
        self.ensure_visible(next, visible_height, filtered_len);
    }

    /// Move selection to the previous item.
    pub fn select_previous(&mut self) {
        self.select_previous_with_height(10) // Default height, will be adjusted in render
    }

    /// Move selection to the previous item with known visible height.
    pub fn select_previous_with_height(&mut self, visible_height: usize) {
        let filtered_len = self.filtered_items().len();
        if filtered_len == 0 {
            return;
        }
        let current = self.state.selected().unwrap_or(0);
        let prev = if current == 0 {
            let last = filtered_len - 1;
            // Wrap to bottom - scroll to show the last item
            self.scroll_offset = filtered_len.saturating_sub(visible_height);
            last
        } else {
            current - 1
        };
        self.state.select(Some(prev));
        self.ensure_visible(prev, visible_height, filtered_len);
    }

    /// Ensure the selected index is visible in the viewport.
    fn ensure_visible(&mut self, selected: usize, visible_height: usize, total: usize) {
        if total <= visible_height {
            self.scroll_offset = 0;
            return;
        }
        // If selected is above viewport, scroll up
        if selected < self.scroll_offset {
            self.scroll_offset = selected;
        }
        // If selected is below viewport, scroll down
        else if selected >= self.scroll_offset + visible_height {
            self.scroll_offset = selected.saturating_sub(visible_height) + 1;
        }
    }

    /// Add a character to the filter.
    pub fn enter_filter_char(&mut self, c: char) {
        self.filter.insert(self.filter_cursor, c);
        self.filter_cursor += c.len_utf8();
        // Reset cursor position and scroll when filter changes
        self.state.select(Some(0));
        self.scroll_offset = 0;
    }

    /// Delete the character before the cursor in the filter.
    pub fn delete_filter_char(&mut self) {
        if self.filter_cursor > 0 {
            let mut prev_cursor = self.filter_cursor - 1;
            while prev_cursor > 0 && !self.filter.is_char_boundary(prev_cursor) {
                prev_cursor -= 1;
            }
            self.filter.remove(prev_cursor);
            self.filter_cursor = prev_cursor;
            // Reset cursor position and scroll when filter changes
            self.state.select(Some(0));
            self.scroll_offset = 0;
        }
    }

    /// Get all selected items.
    pub fn selected_items(&self) -> Vec<&SelectItem> {
        self.items
            .iter()
            .filter(|item| self.selected_ids.contains(&item.id))
            .collect()
    }

    /// Render the multi select widget with virtual scrolling.
    pub fn render(&mut self, frame: &mut Frame, area: Rect) {
        let border_style = if self.focused {
            Style::default().fg(Color::Cyan)
        } else {
            Style::default().fg(Color::DarkGray)
        };

        let label_style = if self.focused {
            Style::default()
                .fg(Color::Cyan)
                .add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(Color::White)
        };

        let selected_count = self.selected_ids.len();
        let title = if selected_count > 0 {
            format!(" {} ({} selected) ", self.label, selected_count)
        } else {
            format!(" {} ", self.label)
        };

        let block = Block::default()
            .title(Span::styled(title, label_style))
            .borders(Borders::ALL)
            .border_style(border_style);

        let inner_area = block.inner(area);
        frame.render_widget(block, area);

        // Split inner area: filter input + list
        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([Constraint::Length(1), Constraint::Min(1)])
            .split(inner_area);

        // Render filter input
        let filter_text = if self.filter.is_empty() && self.focused {
            Span::styled("Type to filter...", Style::default().fg(Color::DarkGray))
        } else if self.filter.is_empty() {
            Span::styled("", Style::default())
        } else {
            Span::styled(&self.filter, Style::default().fg(Color::Yellow))
        };

        let filter_line = Line::from(vec![
            Span::styled("/ ", Style::default().fg(Color::DarkGray)),
            filter_text,
        ]);

        frame.render_widget(Paragraph::new(filter_line), chunks[0]);

        // Calculate visible height for virtual scrolling
        // Calculate visible height for virtual scrolling
        let list_area = chunks[1];

        // Get item count and calculate lines per item (needs a quick scan)
        let total_items = self.filtered_items().len();
        let has_descriptions = self.items.first().map(|i| i.description.is_some()).unwrap_or(false);
        let lines_per_item = if has_descriptions { 2usize } else { 1usize };
        let visible_items = (list_area.height as usize) / lines_per_item.max(1);

        // Ensure selection is visible (modifies scroll_offset)
        let selected = self.state.selected().unwrap_or(0);
        self.ensure_visible(selected, visible_items, total_items);

        // Now get filtered items for rendering (after ensure_visible modified scroll_offset)
        let filtered = self.filtered_items();
        let visible_end = (self.scroll_offset + visible_items).min(total_items);
        let items: Vec<ListItem> = filtered
            .iter()
            .skip(self.scroll_offset)
            .take(visible_items)
            .map(|item| {
                let checkbox = if self.is_selected(&item.id) {
                    Span::styled("[x] ", Style::default().fg(Color::Green))
                } else {
                    Span::styled("[ ] ", Style::default().fg(Color::DarkGray))
                };

                let spans = vec![checkbox, Span::raw(&item.display_name)];

                let line = Line::from(spans);

                let mut lines = vec![line];
                if let Some(desc) = &item.description {
                    lines.push(Line::from(Span::styled(
                        format!(
                            "    {}",
                            truncate_str(desc, inner_area.width.saturating_sub(8) as usize)
                        ),
                        Style::default().fg(Color::DarkGray),
                    )));
                }

                ListItem::new(lines)
            })
            .collect();

        let highlight_style = Style::default()
            .bg(Color::DarkGray)
            .add_modifier(Modifier::BOLD);

        let list = List::new(items)
            .highlight_symbol("> ")
            .highlight_style(highlight_style);

        // Adjust selection state for the visible window
        let mut state = ListState::default();
        if selected >= self.scroll_offset && selected < visible_end {
            state.select(Some(selected - self.scroll_offset));
        }
        frame.render_stateful_widget(list, list_area, &mut state);

        // Render scroll indicators if needed
        if total_items > visible_items {
            let above = self.scroll_offset;
            let below = total_items.saturating_sub(visible_end);

            if above > 0 {
                let indicator = format!("▲ {} more", above);
                frame.render_widget(
                    Paragraph::new(Span::styled(indicator, Style::default().fg(Color::DarkGray))),
                    Rect::new(list_area.x + list_area.width.saturating_sub(12), list_area.y, 12, 1),
                );
            }
            if below > 0 {
                let indicator = format!("▼ {} more", below);
                let y = list_area.y + list_area.height.saturating_sub(1);
                frame.render_widget(
                    Paragraph::new(Span::styled(indicator, Style::default().fg(Color::DarkGray))),
                    Rect::new(list_area.x + list_area.width.saturating_sub(12), y, 12, 1),
                );
            }
        }

        // Set cursor position in filter if focused
        if self.focused {
            frame.set_cursor(chunks[0].x + 2 + self.filter_cursor as u16, chunks[0].y);
        }
    }
}

// =============================================================================
// Helper Functions
// =============================================================================

/// Render a wizard header with title and step indicator.
///
/// The header is rendered as:
/// `--- Title ------------------- Step N/M ---`
pub fn render_wizard_header(frame: &mut Frame, area: Rect, title: &str, step: usize, total: usize) {
    let step_text = format!("Step {}/{}", step, total);
    let title_text = format!(" {} ", title);

    // Calculate padding
    let fixed_width = title_text.len() + step_text.len() + 6; // 6 for decorations
    let padding_width = area.width.saturating_sub(fixed_width as u16) as usize;

    let header = Line::from(vec![
        Span::styled("--", Style::default().fg(Color::DarkGray)),
        Span::styled(
            title_text,
            Style::default()
                .fg(Color::Cyan)
                .add_modifier(Modifier::BOLD),
        ),
        Span::styled(
            "-".repeat(padding_width),
            Style::default().fg(Color::DarkGray),
        ),
        Span::styled(" ", Style::default()),
        Span::styled(step_text, Style::default().fg(Color::Yellow)),
        Span::styled(" --", Style::default().fg(Color::DarkGray)),
    ]);

    frame.render_widget(Paragraph::new(header), area);
}

/// Render a wizard footer with navigation hints.
///
/// # Arguments
/// * `frame` - The frame to render into
/// * `area` - The area to render the footer
/// * `can_go_back` - Whether the Back action is available
/// * `can_go_next` - Whether the Next action is available
/// * `is_last` - Whether this is the last step (changes Next to Create/Submit)
/// * `extra_hints` - Additional hints to show (e.g., "Space Toggle")
pub fn render_wizard_footer(
    frame: &mut Frame,
    area: Rect,
    can_go_back: bool,
    can_go_next: bool,
    is_last: bool,
    extra_hints: &[(&str, &str)],
) {
    let mut spans = Vec::new();

    // Escape/Cancel
    spans.push(Span::styled("Esc", Style::default().fg(Color::Yellow)));
    spans.push(Span::styled(
        " Cancel",
        Style::default().fg(Color::DarkGray),
    ));
    spans.push(Span::styled("  ", Style::default()));

    // Back
    if can_go_back {
        spans.push(Span::styled("<-", Style::default().fg(Color::Yellow)));
        spans.push(Span::styled(" Back", Style::default().fg(Color::DarkGray)));
        spans.push(Span::styled("  ", Style::default()));
    }

    // Extra hints (e.g., Space Toggle)
    for (key, action) in extra_hints {
        spans.push(Span::styled(*key, Style::default().fg(Color::Yellow)));
        spans.push(Span::styled(
            format!(" {}", action),
            Style::default().fg(Color::DarkGray),
        ));
        spans.push(Span::styled("  ", Style::default()));
    }

    // Next/Create
    if can_go_next {
        spans.push(Span::styled("Enter", Style::default().fg(Color::Yellow)));
        let action = if is_last { " Create" } else { " Next" };
        spans.push(Span::styled(action, Style::default().fg(Color::DarkGray)));
    }

    let footer = Line::from(spans);
    frame.render_widget(Paragraph::new(footer).style(Style::default()), area);
}

/// Truncate a string to a maximum length, adding ellipsis if needed.
pub fn truncate_str(s: &str, max: usize) -> String {
    if s.len() <= max {
        s.to_string()
    } else if max <= 3 {
        ".".repeat(max)
    } else {
        format!("{}...", &s[..max - 3])
    }
}

/// Render a centered loading indicator.
pub fn render_loading(frame: &mut Frame, area: Rect, message: &str, spinner_frame: usize) {
    const SPINNER_FRAMES: &[char] = &['|', '/', '-', '\\', '|', '/', '-', '\\'];
    let spinner = SPINNER_FRAMES[spinner_frame % SPINNER_FRAMES.len()];

    let text = format!("{} {}", spinner, message);
    let line = Line::from(Span::styled(text, Style::default().fg(Color::Yellow)));

    let paragraph = Paragraph::new(line)
        .style(Style::default())
        .wrap(Wrap { trim: true });

    // Center vertically
    let centered_y = area.y + area.height / 2;
    let centered_area = Rect::new(area.x, centered_y, area.width, 1);

    frame.render_widget(paragraph, centered_area);
}

/// Render an error message.
pub fn render_error(frame: &mut Frame, area: Rect, message: &str) {
    let block = Block::default()
        .title(Span::styled(
            " Error ",
            Style::default().fg(Color::Red).add_modifier(Modifier::BOLD),
        ))
        .borders(Borders::ALL)
        .border_style(Style::default().fg(Color::Red));

    let inner = block.inner(area);

    frame.render_widget(block, area);
    frame.render_widget(
        Paragraph::new(message)
            .style(Style::default().fg(Color::Red))
            .wrap(Wrap { trim: true }),
        inner,
    );
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_text_input_basic() {
        let mut input = TextInput::new("Name").placeholder("Enter name").required();

        assert!(!input.is_valid());
        assert!(input.value.is_empty());

        input.enter_char('H');
        input.enter_char('e');
        input.enter_char('l');
        input.enter_char('l');
        input.enter_char('o');

        assert_eq!(input.value, "Hello");
        assert!(input.is_valid());

        input.delete_char();
        assert_eq!(input.value, "Hell");

        input.move_cursor_left();
        input.move_cursor_left();
        input.enter_char('X');
        assert_eq!(input.value, "HeXll");
    }

    #[test]
    fn test_single_select() {
        let mut select = SingleSelect::new("Agent");
        select.set_items(vec![
            SelectItem::new("1", "Agent One"),
            SelectItem::new("2", "Agent Two"),
            SelectItem::new("3", "Another Agent"),
        ]);

        assert!(select.selected().is_some());
        assert_eq!(select.selected().unwrap().name, "Agent One");

        select.select_next();
        assert_eq!(select.selected().unwrap().name, "Agent Two");

        select.enter_filter_char('A');
        select.enter_filter_char('n');
        select.enter_filter_char('o');
        let filtered = select.filtered_items();
        assert_eq!(filtered.len(), 1);
        assert_eq!(filtered[0].name, "Another Agent");
    }

    #[test]
    fn test_multi_select() {
        let mut select = MultiSelect::new("Roles");
        select.set_items(vec![
            SelectItem::new("admin", "Admin"),
            SelectItem::new("user", "User"),
            SelectItem::new("guest", "Guest"),
        ]);

        assert!(select.selected_items().is_empty());

        select.toggle_current();
        assert_eq!(select.selected_items().len(), 1);
        assert!(select.is_selected("admin"));

        select.select_next();
        select.toggle_current();
        assert_eq!(select.selected_items().len(), 2);
        assert!(select.is_selected("user"));

        select.toggle_current();
        assert_eq!(select.selected_items().len(), 1);
        assert!(!select.is_selected("user"));
    }

    #[test]
    fn test_truncate_str() {
        assert_eq!(truncate_str("Hello", 10), "Hello");
        assert_eq!(truncate_str("Hello World", 8), "Hello...");
        assert_eq!(truncate_str("Hi", 2), "Hi");
        assert_eq!(truncate_str("Hello", 3), "...");
    }
}
