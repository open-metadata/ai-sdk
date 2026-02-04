//! Markdown to styled terminal text renderer.

use pulldown_cmark::{CodeBlockKind, Event, Parser, Tag, TagEnd};
use ratatui::{
    style::{Color, Modifier, Style},
    text::{Line, Span},
};
use std::sync::LazyLock;
use syntect::{
    easy::HighlightLines,
    highlighting::{Style as SyntectStyle, ThemeSet},
    parsing::SyntaxSet,
    util::LinesWithEndings,
};

static SYNTAX_SET: LazyLock<SyntaxSet> = LazyLock::new(SyntaxSet::load_defaults_newlines);
static THEME_SET: LazyLock<ThemeSet> = LazyLock::new(ThemeSet::load_defaults);

/// Convert markdown text to styled lines for terminal display.
pub fn render_markdown(text: &str, width: usize) -> Vec<Line<'static>> {
    let parser = Parser::new(text);
    let mut lines: Vec<Line<'static>> = Vec::new();
    let mut current_spans: Vec<Span<'static>> = Vec::new();
    let mut style_stack: Vec<Style> = vec![Style::default()];

    let mut in_code_block = false;
    let mut code_lang: Option<String> = None;
    let mut code_content = String::new();

    for event in parser {
        match event {
            Event::Start(tag) => {
                match tag {
                    Tag::Paragraph => {}
                    Tag::Heading { .. } => {
                        style_stack.push(
                            Style::default()
                                .fg(Color::Cyan)
                                .add_modifier(Modifier::BOLD),
                        );
                    }
                    Tag::CodeBlock(kind) => {
                        in_code_block = true;
                        code_lang = match kind {
                            CodeBlockKind::Fenced(lang) => {
                                let l = lang.to_string();
                                if l.is_empty() {
                                    None
                                } else {
                                    Some(l)
                                }
                            }
                            CodeBlockKind::Indented => None,
                        };
                        code_content.clear();
                    }
                    Tag::Strong => {
                        style_stack.push(Style::default().add_modifier(Modifier::BOLD));
                    }
                    Tag::Emphasis => {
                        style_stack.push(Style::default().add_modifier(Modifier::ITALIC));
                    }
                    Tag::List(_) => {}
                    Tag::Item => {
                        // Add bullet point
                        if !current_spans.is_empty() {
                            lines.push(Line::from(std::mem::take(&mut current_spans)));
                        }
                        current_spans.push(Span::raw("  • "));
                    }
                    _ => {}
                }
            }
            Event::End(tag_end) => {
                match tag_end {
                    TagEnd::Paragraph => {
                        if !current_spans.is_empty() {
                            lines.push(Line::from(std::mem::take(&mut current_spans)));
                        }
                        lines.push(Line::default()); // Empty line after paragraph
                    }
                    TagEnd::Heading(_) => {
                        style_stack.pop();
                        if !current_spans.is_empty() {
                            lines.push(Line::from(std::mem::take(&mut current_spans)));
                        }
                        lines.push(Line::default());
                    }
                    TagEnd::CodeBlock => {
                        in_code_block = false;
                        let code_lines =
                            render_code_block(&code_content, code_lang.as_deref(), width);
                        lines.extend(code_lines);
                        lines.push(Line::default());
                        code_lang = None;
                    }
                    TagEnd::Strong | TagEnd::Emphasis => {
                        style_stack.pop();
                    }
                    TagEnd::Item => {
                        if !current_spans.is_empty() {
                            lines.push(Line::from(std::mem::take(&mut current_spans)));
                        }
                    }
                    _ => {}
                }
            }
            Event::Text(text) => {
                if in_code_block {
                    code_content.push_str(&text);
                } else {
                    let style = style_stack.last().copied().unwrap_or_default();
                    current_spans.push(Span::styled(text.to_string(), style));
                }
            }
            Event::Code(code) => {
                // Inline code
                current_spans.push(Span::styled(
                    format!(" {code} "),
                    Style::default().bg(Color::DarkGray).fg(Color::White),
                ));
            }
            Event::SoftBreak | Event::HardBreak => {
                if !current_spans.is_empty() {
                    lines.push(Line::from(std::mem::take(&mut current_spans)));
                }
            }
            _ => {}
        }
    }

    // Flush remaining spans
    if !current_spans.is_empty() {
        lines.push(Line::from(current_spans));
    }

    // Remove trailing empty lines
    while lines.last().map(|l| l.spans.is_empty()).unwrap_or(false) {
        lines.pop();
    }

    lines
}

/// Render a code block with syntax highlighting and border.
fn render_code_block(code: &str, lang: Option<&str>, width: usize) -> Vec<Line<'static>> {
    let mut lines = Vec::new();
    let content_width = width.saturating_sub(4); // Account for border

    // Top border with optional language label
    let label = lang.unwrap_or("code");
    let border_width = content_width.saturating_sub(label.len() + 3);
    let top_border = format!("  ┌─ {} {}", label, "─".repeat(border_width));
    lines.push(Line::from(Span::styled(
        top_border,
        Style::default().fg(Color::DarkGray),
    )));

    // Highlighted code lines
    let highlighted = highlight_code(code, lang);
    for line_spans in highlighted {
        let mut spans = vec![Span::styled("  │ ", Style::default().fg(Color::DarkGray))];
        spans.extend(line_spans);
        lines.push(Line::from(spans));
    }

    // Bottom border
    let bottom_border = format!("  └{}", "─".repeat(content_width + 1));
    lines.push(Line::from(Span::styled(
        bottom_border,
        Style::default().fg(Color::DarkGray),
    )));

    lines
}

/// Apply syntax highlighting to code.
fn highlight_code(code: &str, lang: Option<&str>) -> Vec<Vec<Span<'static>>> {
    let syntax = lang
        .and_then(|l| SYNTAX_SET.find_syntax_by_token(l))
        .unwrap_or_else(|| SYNTAX_SET.find_syntax_plain_text());

    let theme = &THEME_SET.themes["base16-ocean.dark"];
    let mut highlighter = HighlightLines::new(syntax, theme);

    let mut result = Vec::new();

    for line in LinesWithEndings::from(code) {
        let ranges = highlighter
            .highlight_line(line, &SYNTAX_SET)
            .unwrap_or_default();
        let spans: Vec<Span<'static>> = ranges
            .into_iter()
            .map(|(style, text)| {
                Span::styled(
                    text.trim_end_matches('\n').to_string(),
                    syntect_to_ratatui_style(style),
                )
            })
            .collect();
        result.push(spans);
    }

    result
}

/// Convert syntect style to ratatui style.
fn syntect_to_ratatui_style(style: SyntectStyle) -> Style {
    let fg = Color::Rgb(style.foreground.r, style.foreground.g, style.foreground.b);
    Style::default().fg(fg)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_render_simple_text() {
        let lines = render_markdown("Hello world", 80);
        assert!(!lines.is_empty());
    }

    #[test]
    fn test_render_bold() {
        let lines = render_markdown("**bold text**", 80);
        assert!(!lines.is_empty());
    }

    #[test]
    fn test_render_code_block() {
        let md = "```sql\nSELECT * FROM users;\n```";
        let lines = render_markdown(md, 80);
        assert!(lines.len() > 1);
    }
}
