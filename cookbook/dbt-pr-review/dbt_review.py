#!/usr/bin/env python3
"""
dbt Model PR Review Script

This script is called by the GitHub Action to review dbt model changes.
Copy this file to .github/scripts/dbt_review.py in your repository.

Usage:
    python dbt_review.py --pr-number 123 --changed-files "models/orders.sql\nmodels/customers.sql"

Environment Variables:
    METADATA_HOST: Collate/OpenMetadata instance URL
    METADATA_TOKEN: JWT token for authentication
    GITHUB_TOKEN: GitHub token for posting comments
    GITHUB_BASE_REF: Base branch for diff comparison
"""

import argparse
import os
import subprocess
import sys
import time

from ai_sdk import MetadataAI
from ai_sdk.exceptions import (
    AgentExecutionError,
    AuthenticationError,
    MetadataError,
    RateLimitError,
)

AGENT_NAME = "DBTReviewer"
COMMENT_MARKER = "<!-- ai-sdk-dbt-review -->"


def get_file_diff(filepath: str, base_ref: str) -> str:
    """Get the git diff for a specific file."""
    result = subprocess.run(
        ["git", "diff", f"origin/{base_ref}...HEAD", "--", filepath],
        capture_output=True,
        text=True,
    )
    return result.stdout


def build_prompt(diffs: dict[str, str]) -> str:
    """Build the agent prompt with all file diffs."""
    files_section = "\n".join(
        f"### {filepath}\n```sql\n{diff}\n```" for filepath, diff in diffs.items()
    )

    return f"""Review these dbt model changes from a pull request.

## Changed Files
{files_section}

## Your Task
For each changed model:
1. Search for it in OpenMetadata by name (extract model name from filename)
2. Analyze downstream lineage - what dashboards, tables, or pipelines depend on it?
3. Check if any metrics are defined on this model - are calculations affected?
4. Review existing data quality tests - will any break due to these changes?
5. Identify breaking changes (renamed/removed columns, changed joins, modified filters)

## Output Format
Provide a structured review with:
- **Summary**: One-line overall assessment
- **Impact Analysis**: For each model, list affected downstream assets with risk level
- **Data Quality Risks**: Tests that may fail or need updating
- **Breaking Changes**: Column renames, removals, or logic changes that affect consumers
- **Recommendations**: Suggested actions before merging

Use tables and emoji indicators (🔴 High, 🟡 Medium, 🟢 Low) for clarity.
"""


def invoke_with_retry(client: MetadataAI, prompt: str, max_retries: int = 3) -> str:
    """Invoke agent with retry logic for transient failures."""
    for attempt in range(max_retries):
        try:
            return client.agent(AGENT_NAME).invoke(prompt)
        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = getattr(e, "retry_after", None) or (2**attempt)
                print(f"Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
        except AgentExecutionError:
            if attempt < max_retries - 1:
                print(f"Server error, retrying in {2**attempt}s...")
                time.sleep(2**attempt)
            else:
                raise
    return ""


def post_or_update_comment(pr_number: int, body: str) -> None:
    """Post or update the review comment on the PR."""
    body_with_marker = f"{COMMENT_MARKER}\n{body}"

    # Find existing comment
    result = subprocess.run(
        [
            "gh",
            "pr",
            "view",
            str(pr_number),
            "--json",
            "comments",
            "--jq",
            ".comments[] | select(.body | startswith(\"<!-- ai-sdk-dbt-review -->\")) | .url",
        ],
        capture_output=True,
        text=True,
    )

    existing_comment_url = result.stdout.strip().split("\n")[0] if result.stdout.strip() else ""

    if existing_comment_url:
        # Extract comment ID from URL and update
        comment_id = existing_comment_url.split("/")[-1].split("#")[-1]
        subprocess.run(
            [
                "gh",
                "api",
                "-X",
                "PATCH",
                f"/repos/{{owner}}/{{repo}}/issues/comments/{comment_id}",
                "-f",
                f"body={body_with_marker}",
            ],
            check=True,
        )
        print(f"Updated existing comment on PR #{pr_number}")
    else:
        # Create new comment
        subprocess.run(
            ["gh", "pr", "comment", str(pr_number), "--body", body_with_marker],
            check=True,
        )
        print(f"Posted new comment on PR #{pr_number}")


def post_error_comment(pr_number: int, error: str) -> None:
    """Post an error comment when review fails."""
    body = f"""## 🔍 dbt Model Review

⚠️ **Review could not be completed**

{error}

Please check the workflow logs for details.

---
*Powered by [Metadata AI](https://github.com/open-metadata/ai-sdk-sdk)*
"""
    post_or_update_comment(pr_number, body)


def main() -> int:
    parser = argparse.ArgumentParser(description="Review dbt model changes")
    parser.add_argument("--pr-number", type=int, required=True, help="PR number")
    parser.add_argument(
        "--changed-files", type=str, required=True, help="Newline-separated list of changed files"
    )
    args = parser.parse_args()

    # Parse changed files
    changed_files = [f.strip() for f in args.changed_files.strip().split("\n") if f.strip()]
    if not changed_files:
        print("No dbt model changes detected")
        return 0

    print(f"Reviewing {len(changed_files)} changed model(s): {', '.join(changed_files)}")

    # Validate environment
    host = os.environ.get("METADATA_HOST")
    token = os.environ.get("METADATA_TOKEN")
    if not host or not token:
        print("Error: METADATA_HOST and METADATA_TOKEN must be set")
        return 1

    # Get diffs
    base_ref = os.environ.get("GITHUB_BASE_REF", "main")
    diffs = {}
    for filepath in changed_files:
        diff = get_file_diff(filepath, base_ref)
        if diff:
            diffs[filepath] = diff

    if not diffs:
        print("No diffs found for changed files")
        return 0

    # Invoke agent
    try:
        client = MetadataAI(host=host, token=token)
        prompt = build_prompt(diffs)
        response = invoke_with_retry(client, prompt)
    except AuthenticationError:
        post_error_comment(args.pr_number, "Authentication failed. Check METADATA_TOKEN secret.")
        return 1
    except MetadataError as e:
        post_error_comment(args.pr_number, f"Metadata AI error: {e}")
        return 1

    # Format and post review
    review_body = f"""## 🔍 dbt Model Review

{response}

---
*Powered by [Metadata AI](https://github.com/open-metadata/ai-sdk-sdk)*
"""

    post_or_update_comment(args.pr_number, review_body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
