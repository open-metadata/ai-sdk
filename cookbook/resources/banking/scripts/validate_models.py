"""Check the compiled dbt SQL against the target warehouse's dialect.

Run after ``dbt compile``, before ``dbt run``. Catches the class of error that
otherwise only surfaces one model at a time during a long build: Redshift
accepts a good deal of SQL that BigQuery rejects outright, and dbt's own parse
step cannot see it because the difference only appears after macro rendering.

    python scripts/validate_models.py --target bigquery

Two checks, because neither alone is sufficient:

* a dialect parse, which catches bare UNION and macros accidentally rendered
  inside a ``--`` comment (a multi-line render escapes the comment and injects
  raw SQL);
* a reserved-word alias scan, which the parser is too permissive to flag —
  ``left join account_types at`` parses fine and then fails on the warehouse.
"""

from __future__ import annotations

import argparse
import logging
import re
from dataclasses import dataclass
from pathlib import Path

import sqlglot
from sqlglot.errors import ParseError

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMPILED_DIR = PROJECT_ROOT / "dbt" / "target" / "compiled"

# GoogleSQL reserved keywords. A table alias matching one of these is a syntax
# error on BigQuery but perfectly legal on Redshift.
BIGQUERY_RESERVED = frozenset(
    """all and any array as asc assert_rows_modified at between by case cast collate contains create
    cross cube current default define desc distinct else end enum escape except exclude exists extract
    false fetch following for from full group grouping groups hash having if ignore in inner intersect
    interval into is join lateral left like limit lookup merge natural new no not null nulls of on or
    order outer over partition preceding proto range recursive respect right rollup rows select set some
    struct tablesample then to treat true unbounded union unnest using when where window with within""".split()
)

RESERVED_BY_DIALECT = {"bigquery": BIGQUERY_RESERVED, "redshift": frozenset()}

# "from <table> <alias>" / "join <table> <alias>", skipping the words that can
# legitimately follow a table name instead of an alias.
ALIAS_RE = re.compile(
    r"\b(?:from|join)\s+[`\"\w.]+\s+"
    r"(?!on\b|as\b|using\b|where\b|group\b|order\b|left\b|right\b|inner\b|full\b|cross\b"
    r"|union\b|limit\b|having\b|qualify\b|window\b)"
    r"([a-z_]\w*)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Problem:
    model: str
    kind: str
    detail: str


def compiled_models(target_dir: Path) -> list[Path]:
    """Every compiled model SQL file, excluding generated test SQL."""
    return sorted(p for p in target_dir.rglob("*.sql") if "/tests/" not in p.as_posix())


def check_parse(sql: str, dialect: str) -> str | None:
    try:
        sqlglot.parse_one(sql, dialect=dialect)
    except ParseError as error:
        return str(error).split("\n")[0][:160]
    return None


def check_reserved_aliases(sql: str, reserved: frozenset[str]) -> list[str]:
    return sorted({alias for alias in ALIAS_RE.findall(sql) if alias.lower() in reserved})


def validate(target: str) -> list[Problem]:
    if target not in RESERVED_BY_DIALECT:
        raise ValueError(f"Unknown target {target!r}; expected one of {sorted(RESERVED_BY_DIALECT)}")

    if not COMPILED_DIR.exists():
        raise SystemExit(
            f"No compiled SQL at {COMPILED_DIR}.\n"
            f"Run: cd dbt && DBT_PROFILES_DIR=$(pwd) dbt compile --target {target}"
        )

    reserved = RESERVED_BY_DIALECT[target]
    problems: list[Problem] = []
    models = compiled_models(COMPILED_DIR)

    for path in models:
        sql = path.read_text(encoding="utf-8")
        name = path.as_posix().split("/compiled/", 1)[-1]

        error = check_parse(sql, target)
        if error:
            problems.append(Problem(model=name, kind=f"{target} parse error", detail=error))

        for alias in check_reserved_aliases(sql, reserved):
            problems.append(
                Problem(
                    model=name,
                    kind="reserved-word alias",
                    detail=f"'{alias}' is a {target} reserved keyword — rename it",
                )
            )

    logger.info("Checked %d compiled files against the %s dialect.", len(models), target)
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        default="bigquery",
        help="Warehouse dialect to validate against (default: bigquery)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    problems = validate(args.target)
    if not problems:
        logger.info("No dialect problems found.")
        return

    logger.error("%d problem(s):", len(problems))
    for problem in problems:
        logger.error("  %s\n    %s: %s", problem.model, problem.kind, problem.detail)
    raise SystemExit(1)


if __name__ == "__main__":
    main()
