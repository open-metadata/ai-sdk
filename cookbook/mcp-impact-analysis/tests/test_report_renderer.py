from __future__ import annotations

from diff_parser import ChangedAsset
from report_renderer import COMMENT_MARKER, render_html_report, render_markdown_report
from risk_scoring import ImpactScore, RiskLevel


def test_render_markdown_report_includes_marker_and_required_sections() -> None:
    report = render_markdown_report(
        changed_assets=[ChangedAsset("stg_orders", "models/staging/stg_orders.sql", "model", "modified", "")],
        analyses={"stg_orders": "## What Changed\nStatus was renamed.\n"},
        score=ImpactScore(RiskLevel.MEDIUM, 1, ["downstream assets detected"]),
        warnings=["AI analysis unavailable; deterministic fallback used."],
    )

    assert report.startswith(COMMENT_MARKER)
    assert "## Impact Summary" in report
    assert "## Changed Assets" in report
    assert "## Analysis: stg_orders" in report
    assert "## Reviewer Checklist" in report
    assert "AI analysis unavailable" in report


def test_render_html_report_escapes_analysis_content() -> None:
    html = render_html_report(
        markdown_report="## Report\n<script>alert('x')</script>",
        title="OpenMetadata Impact Analysis",
    )

    assert "<script>alert" not in html
    assert "&lt;script&gt;alert" in html
    assert "<title>OpenMetadata Impact Analysis</title>" in html
