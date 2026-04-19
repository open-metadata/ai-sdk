"""Batch impact analyzer for CI/CD integration.

Usage:
    python batch_analyzer.py changes.diff --output impact_report.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from diff_parser import ChangedAsset, parse_changed_assets, split_path_filters
from report_renderer import (
    render_html_report,
    render_markdown_report,
    render_no_change_report,
)
from risk_scoring import ImpactScore, RiskLevel, score_impact


def get_changed_models(diff_output: str) -> dict[str, str]:
    """Backward-compatible helper returning changed model/schema diffs by asset name."""

    return {asset.name: asset.diff for asset in parse_changed_assets(diff_output)}


def build_change_prompt(asset: ChangedAsset) -> str:
    """Build the prompt sent to the OpenMetadata MCP-backed agent."""

    return (
        f"The dbt {asset.kind} '{asset.name}' has been {asset.change_type}. "
        f"The changed file is '{asset.path}'. Here is the git diff:\n\n"
        f"```diff\n{asset.diff}\n```\n\n"
        "Start with a brief explanation of what the diff is doing. Then analyze "
        "which downstream assets are affected, who owns them, whether data-quality "
        "tests may fail, and whether PII or governance tags require review."
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    diff_path = Path(args.diff_file)
    if not diff_path.exists():
        print(f"Error: File not found: {diff_path}", file=sys.stderr)
        return 1

    diff_output = diff_path.read_text(encoding="utf-8")
    changed_assets = parse_changed_assets(diff_output, split_path_filters(args.paths))

    if not changed_assets:
        report = render_no_change_report()
        _write_outputs(report, args.output, args.html_output)
        _write_metadata_output(
            args.metadata_output,
            ImpactScore(RiskLevel.LOW, 0, ["no dbt model or schema changes detected"]),
        )
        if args.output is None:
            print(report)
        return 0

    analyses, warnings = _analyze_assets(changed_assets, use_ai=not args.no_ai)
    score = score_impact("\n\n".join(analyses.values()), changed_assets)
    report = render_markdown_report(changed_assets, analyses, score, warnings)

    _write_outputs(report, args.output, args.html_output)
    _write_metadata_output(args.metadata_output, score)

    if args.output is None:
        print(report)
    else:
        print(f"Wrote impact report to {args.output}")

    return 2 if args.fail_on_critical and score.level is RiskLevel.CRITICAL else 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze OpenMetadata impact from a git diff.")
    parser.add_argument("diff_file", help="Path to a unified git diff file.")
    parser.add_argument("--output", help="Write Markdown report to this path.")
    parser.add_argument("--html-output", help="Write a static HTML report artifact to this path.")
    parser.add_argument("--metadata-output", help="Write JSON metadata for GitHub Action outputs.")
    parser.add_argument(
        "--paths",
        help="Comma-separated path globs to analyze. Defaults to dbt models/**/*.sql,yml,yaml.",
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Skip the MCP/LLM analyzer and emit deterministic fallback sections.",
    )
    parser.add_argument(
        "--fail-on-critical",
        action="store_true",
        help="Exit with code 2 when deterministic scoring marks the PR critical.",
    )
    return parser


def _analyze_assets(
    changed_assets: Sequence[ChangedAsset],
    *,
    use_ai: bool,
) -> tuple[dict[str, str], list[str]]:
    warnings: list[str] = []
    analyses: dict[str, str] = {}
    agent = None
    client = None

    if use_ai:
        try:
            from impact_analyzer import analyze_change, create_impact_analyzer

            agent, client = create_impact_analyzer()
        except Exception as exc:  # noqa: BLE001 - degraded CI report is intentional.
            warnings.append(
                "AI analysis unavailable; deterministic fallback used. "
                f"Reason: {exc.__class__.__name__}: {exc}"
            )
            use_ai = False

    try:
        for asset in changed_assets:
            if use_ai and agent is not None:
                try:
                    result = analyze_change(agent, build_change_prompt(asset))
                    analyses[asset.name] = result.get("analysis") or _fallback_analysis(asset)
                    continue
                except Exception as exc:  # noqa: BLE001 - keep other assets reportable.
                    warnings.append(
                        f"AI analysis failed for {asset.name}; fallback used. "
                        f"Reason: {exc.__class__.__name__}: {exc}"
                    )

            analyses[asset.name] = _fallback_analysis(asset)
    finally:
        if client is not None:
            client.close()

    return analyses, warnings


def _fallback_analysis(asset: ChangedAsset) -> str:
    return "\n".join(
        [
            "## What Changed",
            f"`{asset.path}` was {asset.change_type}.",
            "",
            "## Impact Summary",
            "OpenMetadata credentials or AI analysis were not available, so this report "
            "could not query live lineage. Treat this as a review prompt, not a final "
            "blast-radius assessment.",
            "",
            "## Affected Assets",
            "Downstream assets were not resolved in fallback mode.",
            "",
            "## Risk Assessment",
            "- Data Quality: Review tests for changed columns in this model or schema file.",
            "- Compliance: Check whether changed columns contain PII or sensitive tags.",
            "- Business: Review downstream dashboards and pipelines in OpenMetadata before merge.",
            "",
            "## Recommended Actions",
            "1. Run this action with `AI_SDK_HOST`, `AI_SDK_TOKEN`, and `OPENAI_API_KEY`.",
            "2. Review the OpenMetadata lineage graph for this asset.",
            "3. Ask affected owners to approve high-risk model changes.",
        ]
    )


def _write_outputs(
    markdown_report: str,
    output_path: str | None,
    html_output_path: str | None,
) -> None:
    if output_path:
        Path(output_path).write_text(markdown_report, encoding="utf-8")
    if html_output_path:
        Path(html_output_path).write_text(render_html_report(markdown_report), encoding="utf-8")


def _write_metadata_output(output_path: str | None, score: ImpactScore) -> None:
    if output_path is None:
        return
    Path(output_path).write_text(
        json.dumps(
            {
                "risk_level": score.level.value,
                "affected_count": score.affected_count,
                "reasons": score.reasons,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    sys.exit(main())
