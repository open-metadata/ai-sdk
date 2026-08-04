"""Check every seed CSV against the types declared in schema/registry.py.

A pre-flight guard for the loaders. Redshift's COPY quietly repairs several
mismatches — a bare date in a TIMESTAMP column, an over-scaled decimal — while
BigQuery rejects the whole load job. Without this check the first sign of
trouble is a failed `bq load` partway through a 220 MB upload.

    python scripts/validate_seeds.py

Exits non-zero and prints one line per offending column if anything fails.
"""

from __future__ import annotations

import csv
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# noqa: E402 — the sys.path setup above must precede this import.
from schema.registry import Column, all_tables  # noqa: E402

logger = logging.getLogger(__name__)

SEEDS_DIR = PROJECT_ROOT / "dbt" / "seeds"

# BigQuery accepts 'YYYY-MM-DD HH:MM[:SS[.SSSSSS]]' and the same with 'T'.
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2}(\.\d+)?)?$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
INT_RE = re.compile(r"^-?\d+$")
BOOL_RE = re.compile(r"^(?i:true|false)$")

# Both loaders are configured to read this as NULL; it is never a value.
NULL_MARKER = "\\N"


@dataclass(frozen=True)
class Violation:
    table: str
    column: str
    reason: str
    example: str
    rows: int


def check_value(value: str, column: Column) -> str | None:
    """Return a short reason when ``value`` does not fit its declared type."""
    kind = column.type.kind

    if kind == "timestamp" and not TIMESTAMP_RE.match(value):
        return "not a TIMESTAMP (BigQuery needs the time part, not a bare date)"
    if kind == "date" and not DATE_RE.match(value):
        return "not a DATE"
    if kind == "int" and not INT_RE.match(value):
        return "not an integer"
    if kind == "bool" and not BOOL_RE.match(value):
        return "not a boolean"
    if kind == "string" and column.type.length and len(value) > column.type.length:
        return f"{len(value)} chars exceeds VARCHAR({column.type.length})"

    if kind == "decimal":
        fraction = value.split(".")[1] if "." in value else ""
        if len(fraction) > column.type.scale:
            return f"scale {len(fraction)} exceeds declared scale {column.type.scale}"
        digits = len(value.lstrip("-").replace(".", "").lstrip("0")) or 1
        if digits > column.type.precision:
            return f"{digits} digits exceeds declared precision {column.type.precision}"

    return None


def validate() -> list[Violation]:
    found: dict[tuple[str, str, str], list] = {}
    scanned = 0

    for table in all_tables():
        path = SEEDS_DIR / table.schema / f"{table.name}.csv"
        if not path.exists():
            logger.warning("No CSV for %s.%s — run generate_seed_data.py", table.schema, table.name)
            continue

        indexed = list(enumerate(table.columns))
        with path.open(encoding="utf-8") as handle:
            reader = csv.reader(handle)
            next(reader, None)
            for row in reader:
                scanned += 1
                for position, column in indexed:
                    value = row[position]
                    if value == NULL_MARKER or value == "":
                        continue
                    reason = check_value(value, column)
                    if reason is None:
                        continue
                    key = (f"{table.schema}.{table.name}", column.name, reason)
                    if key not in found:
                        found[key] = [0, value]
                    found[key][0] += 1

    logger.info("Scanned %s rows across %d tables.", f"{scanned:,}", len(all_tables()))
    return [
        Violation(table=key[0], column=key[1], reason=key[2], example=example, rows=rows)
        for key, (rows, example) in sorted(found.items())
    ]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    violations = validate()
    if not violations:
        logger.info("All seed CSVs match schema/registry.py.")
        return

    logger.error("%d column(s) do not match their declared type:", len(violations))
    for violation in violations:
        logger.error(
            "  %s.%s — %s (%d rows, e.g. %r)",
            violation.table,
            violation.column,
            violation.reason,
            violation.rows,
            violation.example[:40],
        )
    raise SystemExit(1)


if __name__ == "__main__":
    main()
