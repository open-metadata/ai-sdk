"""Render GitHub-friendly impact-analysis reports."""

from __future__ import annotations

import html
from typing import Mapping, Sequence

from diff_parser import ChangedAsset
from risk_scoring import ImpactScore, RiskLevel


COMMENT_MARKER = "<!-- openmetadata-impact-analysis -->"


def render_no_change_report() -> str:
    """Render a successful report for PRs with no relevant dbt changes."""

    return "\n".join(
        [
            COMMENT_MARKER,
            "# OpenMetadata Impact Analysis",
            "",
            "No dbt model or schema changes detected.",
            "",
            "The analyzer looked for changed files under dbt `models/` paths with "
            "`.sql`, `.yml`, or `.yaml` extensions.",
            "",
        ]
    )


def render_markdown_report(
    changed_assets: Sequence[ChangedAsset],
    analyses: Mapping[str, str],
    score: ImpactScore,
    warnings: Sequence[str] | None = None,
) -> str:
    """Render the final Markdown report for a PR comment or step summary."""

    lines = [
        COMMENT_MARKER,
        "# OpenMetadata Impact Analysis",
        "",
        "## Impact Summary",
        "",
        f"**Overall risk:** `{score.level.value.upper()}`",
        f"**Affected assets found:** `{score.affected_count}`",
        "",
        "**Risk signals:**",
        *[f"- {reason}" for reason in score.reasons],
        "",
        "## Changed Assets",
        "",
    ]

    if changed_assets:
        lines.extend(
            f"- `{asset.name}` ({asset.kind}, {asset.change_type}) - `{asset.path}`"
            for asset in changed_assets
        )
    else:
        lines.append("- No dbt model or schema changes detected.")

    if warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in warnings)

    for asset_name, analysis in analyses.items():
        lines.extend(["", f"## Analysis: {asset_name}", "", analysis.strip(), ""])

    lines.extend(
        [
            "",
            "## Reviewer Checklist",
            "",
            "- [ ] Review downstream owners before merge.",
            "- [ ] Confirm impacted dashboards and pipelines are expected.",
            "- [ ] Update or add data-quality tests for changed columns.",
            "- [ ] Check governance tags for PII or sensitive data changes.",
            "- [ ] Link follow-up migration or rollback tasks if risk is high.",
            "",
        ]
    )

    return "\n".join(lines)


def render_html_report(markdown_report: str, title: str = "OpenMetadata Impact Analysis") -> str:
    """Render a dependency-free static HTML artifact from the Markdown report."""

    safe_title = html.escape(title)
    safe_report = html.escape(markdown_report)
    risk_class = _risk_class(markdown_report)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <style>
    body {{
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
      margin: 0;
      background: #f6f8fa;
      color: #24292f;
    }}
    main {{
      max-width: 1040px;
      margin: 0 auto;
      padding: 32px 20px;
    }}
    pre {{
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      background: #ffffff;
      border: 1px solid #d0d7de;
      border-top: 6px solid {risk_class};
      border-radius: 8px;
      padding: 24px;
    }}
  </style>
</head>
<body>
  <main>
    <pre>{safe_report}</pre>
  </main>
</body>
</html>
"""


def _risk_class(markdown_report: str) -> str:
    if f"`{RiskLevel.CRITICAL.value.upper()}`" in markdown_report:
        return "#cf222e"
    if f"`{RiskLevel.HIGH.value.upper()}`" in markdown_report:
        return "#bc4c00"
    if f"`{RiskLevel.MEDIUM.value.upper()}`" in markdown_report:
        return "#bf8700"
    return "#1a7f37"
