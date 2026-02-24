"""
Batch Impact Analyzer for CI/CD Integration

Analyzes the impact of all dbt model changes in a PR.

Usage:
    git diff origin/main...HEAD > changes.diff
    python batch_analyzer.py changes.diff

Environment variables required:
    AI_SDK_HOST - Your OpenMetadata server URL
    AI_SDK_TOKEN - Your bot's JWT token
    OPENAI_API_KEY - OpenAI API key
"""

import sys
from pathlib import Path
from impact_analyzer import create_impact_analyzer, analyze_change


def get_changed_models(diff_output: str) -> dict[str, str]:
    """Extract changed dbt model names and their diff hunks from git diff.

    Returns a mapping of model name to the relevant diff snippet.
    """
    models: dict[str, str] = {}
    current_file: str | None = None
    current_lines: list[str] = []

    for line in diff_output.split("\n"):
        if line.startswith("diff --git"):
            # Flush previous file
            if current_file is not None:
                models[current_file] = "\n".join(current_lines)
            current_file = None
            current_lines = [line]
        elif line.startswith("+++ b/") and line.endswith(".sql"):
            path = Path(line.replace("+++ b/", ""))
            if "models" in path.parts:
                current_file = path.stem
            current_lines.append(line)
        else:
            current_lines.append(line)

    # Flush last file
    if current_file is not None:
        models[current_file] = "\n".join(current_lines)

    return models


def main():
    if len(sys.argv) < 2:
        print("Usage: python batch_analyzer.py <git-diff-file>")
        print("\nExample:")
        print("  git diff origin/main...HEAD > changes.diff")
        print("  python batch_analyzer.py changes.diff")
        sys.exit(1)

    diff_path = Path(sys.argv[1])

    if not diff_path.exists():
        print(f"Error: File not found: {diff_path}")
        sys.exit(1)

    diff_output = diff_path.read_text(encoding="utf-8")

    models_with_diffs = get_changed_models(diff_output)

    if not models_with_diffs:
        print("No dbt model changes detected.")
        print("\nLooking for files matching pattern: +++ b/*/models/**/*.sql")
        sys.exit(0)

    model_names = list(models_with_diffs.keys())
    print(f"# Impact Analysis Report\n")
    print(f"Analyzing {len(model_names)} changed model(s): {', '.join(model_names)}\n")

    executor, client = create_impact_analyzer()

    all_reports = []

    try:
        for model, diff_snippet in models_with_diffs.items():
            print(f"\n{'='*60}")
            print(f"## {model}")
            print("="*60 + "\n")

            result = analyze_change(
                executor,
                f"The dbt model '{model}' has been modified. "
                f"Here is the git diff showing what changed:\n\n"
                f"```diff\n{diff_snippet}\n```\n\n"
                f"Start your Impact Summary with a brief explanation of what "
                f"the diff is doing (e.g. column renamed, filter added, new "
                f"calculation). Then analyze: what downstream assets are "
                f"affected and who should be notified?",
            )

            print(result["analysis"])
            all_reports.append({"model": model, **result})

        # Summary
        print("\n" + "="*60)
        print("## Summary")
        print("="*60 + "\n")
        print("| Model | Status |")
        print("|-------|--------|")
        for report in all_reports:
            status = "Done" if report.get("analysis") else "No output"
            print(f"| {report['model']} | {status} |")

    finally:
        client.close()


if __name__ == "__main__":
    main()
