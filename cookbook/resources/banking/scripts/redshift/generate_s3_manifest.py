"""Generate an OpenMetadata storage manifest (openmetadata.json) for the
banking-redshift demo bucket.

OpenMetadata's S3 connector looks for ``s3://<bucket>/openmetadata.json`` and
uses it to discover structured datasets within the bucket. Without it, the
connector only registers the bucket itself — no per-CSV schemas, no column
profiling, no row counts.

This script walks ``dbt/seeds/raw_*/<table>.csv`` and emits a manifest entry
per table folder so the connector ingests every CSV as a structured dataset.

Usage:
    python scripts/generate_s3_manifest.py
    # writes scripts/../openmetadata.json (project root)

The companion target ``make upload-s3`` will publish this file alongside the
CSVs.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SEEDS_DIR = PROJECT_ROOT / "dbt" / "seeds"
MANIFEST_PATH = PROJECT_ROOT / "openmetadata.json"

# Match the BANKING_S3_PREFIX env var default
DEFAULT_PREFIX = "raw"


def build_manifest(prefix: str) -> dict:
    """Build a manifest covering every raw_<schema>/<table>/ folder."""
    entries: list[dict] = []
    for schema_dir in sorted(SEEDS_DIR.glob("raw_*/")):
        for csv_path in sorted(schema_dir.glob("*.csv")):
            table = csv_path.stem
            schema = schema_dir.name
            # dataPath is the folder one level above the CSV file so the
            # connector treats every file inside as a partition of the same
            # logical dataset.
            data_path = f"{prefix}/{schema}/{table}"
            entries.append(
                {
                    "dataPath": data_path,
                    "structureFormat": "csv",
                    "isPartitioned": False,
                }
            )
    return {"entries": entries}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    prefix = os.environ.get("BANKING_S3_PREFIX", DEFAULT_PREFIX)
    manifest = build_manifest(prefix)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    logger.info(
        "Wrote %d manifest entries (prefix=%s) to %s",
        len(manifest["entries"]),
        prefix,
        MANIFEST_PATH,
    )


if __name__ == "__main__":
    main()
