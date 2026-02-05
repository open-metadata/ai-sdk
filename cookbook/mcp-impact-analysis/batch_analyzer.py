"""
Batch Impact Analyzer for CI/CD Integration

Analyzes the impact of all dbt model changes in a PR.

Usage:
    git diff origin/main...HEAD > changes.diff
    python batch_analyzer.py changes.diff

Environment variables required:
    METADATA_HOST - Your OpenMetadata server URL
    METADATA_TOKEN - Your bot's JWT token
    OPENAI_API_KEY - OpenAI API key
"""

import sys
from pathlib import Path
from impact_analyzer import create_impact_analyzer, analyze_change


def get_changed_models(diff_output: str) -> list[str]:
    """Extract changed dbt model names from git diff."""
    models = []
    for line in diff_output.split("\n"):
        if line.startswith("+++ b/") and line.endswith(".sql"):
            # Extract model name from path
            path = Path(line.replace("+++ b/", ""))
            if "models" in path.parts:
                models.append(path.stem)
    return list(set(models))  # Deduplicate


def main():
    if len(sys.argv) < 2:
        print("Usage: python batch_analyzer.py <git-diff-file>")
        print("\nExample:")
        print("  git diff origin/main...HEAD > changes.diff")
        print("  python batch_analyzer.py changes.diff")
        sys.exit(1)

    diff_file = sys.argv[1]

    try:
        with open(diff_file) as f:
            diff_output = f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {diff_file}")
        sys.exit(1)

    changed_models = get_changed_models(diff_output)

    if not changed_models:
        print("No dbt model changes detected.")
        print("\nLooking for files matching pattern: +++ b/*/models/**/*.sql")
        sys.exit(0)

    print(f"# Impact Analysis Report\n")
    print(f"Analyzing {len(changed_models)} changed model(s): {', '.join(changed_models)}\n")

    executor, client = create_impact_analyzer()

    all_reports = []

    try:
        for model in changed_models:
            print(f"\n{'='*60}")
            print(f"## {model}")
            print("="*60 + "\n")

            result = analyze_change(
                executor,
                f"The dbt model '{model}' has been modified. "
                f"What downstream assets are affected and who should be notified?"
            )

            print(result["analysis"])
            all_reports.append({
                "model": model,
                "analysis": result["analysis"],
                "steps": result["steps"]
            })

        # Summary
        print("\n" + "="*60)
        print("## Summary")
        print("="*60 + "\n")
        print(f"| Model | Analysis Steps |")
        print(f"|-------|----------------|")
        for report in all_reports:
            print(f"| {report['model']} | {report['steps']} |")

    finally:
        client.close()


if __name__ == "__main__":
    main()
