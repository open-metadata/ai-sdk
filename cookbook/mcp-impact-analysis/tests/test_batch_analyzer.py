from __future__ import annotations

from pathlib import Path

from batch_analyzer import main


def test_main_writes_no_change_report_without_creating_agent(tmp_path: Path) -> None:
    diff_path = tmp_path / "changes.diff"
    output_path = tmp_path / "impact_report.md"
    html_path = tmp_path / "impact_report.html"
    diff_path.write_text(
        "diff --git a/README.md b/README.md\n"
        "--- a/README.md\n"
        "+++ b/README.md\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        "+new\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            str(diff_path),
            "--output",
            str(output_path),
            "--html-output",
            str(html_path),
        ]
    )

    assert exit_code == 0
    assert "No dbt model or schema changes detected." in output_path.read_text(encoding="utf-8")
    assert "No dbt model or schema changes detected." in html_path.read_text(encoding="utf-8")
