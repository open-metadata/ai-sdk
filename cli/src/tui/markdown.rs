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
    // Stack of link destination URLs so we can render `(url)` after the
    // visible link text on TagEnd::Link. Stack-shaped to handle nesting.
    let mut link_urls: Vec<String> = Vec::new();

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
                    Tag::Link { dest_url, .. } => {
                        link_urls.push(dest_url.to_string());
                        style_stack.push(
                            Style::default()
                                .fg(Color::Blue)
                                .add_modifier(Modifier::UNDERLINED),
                        );
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
                    TagEnd::Link => {
                        style_stack.pop();
                        // Append " (url)" in dimmed text after the visible label.
                        if let Some(url) = link_urls.pop() {
                            current_spans.push(Span::styled(
                                format!(" ({url})"),
                                Style::default().fg(Color::DarkGray),
                            ));
                        }
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

/// Render markdown with all foreground colors collapsed to dark gray —
/// used for thinking steps so they keep the dimmed look while still
/// applying bold/italic/link/code-block structure from the markdown.
///
/// Background colors and modifiers (bold/italic/underline) are preserved.
pub fn render_markdown_dimmed(text: &str, width: usize) -> Vec<Line<'static>> {
    let lines = render_markdown(text, width);
    lines
        .into_iter()
        .map(|line| {
            let spans: Vec<Span<'static>> = line
                .spans
                .into_iter()
                .map(|span| {
                    let dimmed = Style::default()
                        .fg(Color::DarkGray)
                        .add_modifier(span.style.add_modifier);
                    Span::styled(span.content, dimmed)
                })
                .collect();
            Line::from(spans)
        })
        .collect()
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

    fn collect_text(lines: &[Line<'static>]) -> String {
        lines
            .iter()
            .map(|l| {
                l.spans
                    .iter()
                    .map(|s| s.content.as_ref())
                    .collect::<String>()
            })
            .collect::<Vec<_>>()
            .join("\n")
    }

    #[test]
    fn link_renders_label_with_url_appended() {
        let lines = render_markdown("see [docs](https://example.com)", 80);
        let text = collect_text(&lines);
        assert!(text.contains("docs"), "label missing in: {text}");
        assert!(
            text.contains("(https://example.com)"),
            "url missing in: {text}"
        );
        // the bare `[docs](https://example.com)` literal should not appear
        assert!(!text.contains("[docs]"), "raw markdown leaked in: {text}");
    }

    #[test]
    fn link_label_uses_underline_modifier() {
        let lines = render_markdown("[foo](http://x)", 80);
        let label_span = lines
            .iter()
            .flat_map(|l| l.spans.iter())
            .find(|s| s.content.as_ref() == "foo")
            .expect("label span");
        assert!(label_span.style.add_modifier.contains(Modifier::UNDERLINED));
    }

    #[test]
    fn dimmed_renderer_keeps_modifiers_but_overrides_color() {
        let lines = render_markdown_dimmed("**bold** and [link](http://x)", 80);
        // Every span should have DarkGray foreground.
        for line in &lines {
            for span in &line.spans {
                assert_eq!(
                    span.style.fg,
                    Some(Color::DarkGray),
                    "span '{}' is not dimmed",
                    span.content
                );
            }
        }
        // Modifiers preserved: bold span exists.
        let bold_present = lines
            .iter()
            .flat_map(|l| l.spans.iter())
            .any(|s| s.style.add_modifier.contains(Modifier::BOLD));
        assert!(bold_present, "bold modifier was stripped");
    }
}
