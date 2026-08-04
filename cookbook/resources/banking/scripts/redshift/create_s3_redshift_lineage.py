"""Create lineage edges S3 container -> Redshift table for the banking demo.

The Redshift query-lineage workflow doesn't parse ``COPY ... FROM 's3://...'``
statements, so the S3 -> Redshift edges that mirror our load_to_redshift.sh
pipeline never appear automatically. This script materialises them.

For every raw_<schema>/<table> manifest entry, it links:

    banking-s3.collate-summit-data.raw.raw_<schema>.<table>   (Container)
        ---->   banking-redshift.<database>.raw_<schema>.<table>   (Table)

Usage:
    export AI_SDK_HOST=...
    export AI_SDK_TOKEN=...
    python scripts/create_s3_redshift_lineage.py \
        --database dev \
        --bucket collate-summit-data \
        --s3-service banking-s3 \
        --db-service banking-redshift \
        --prefix raw

All flags default to the values used by the demo so the typical invocation is
just ``python scripts/create_s3_redshift_lineage.py``.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from metadata.generated.schema.api.lineage.addLineage import AddLineageRequest
from metadata.generated.schema.entity.data.container import Container
from metadata.generated.schema.entity.data.table import Table
from metadata.generated.schema.entity.services.connections.metadata.openMetadataConnection import (
    AuthProvider,
    OpenMetadataConnection,
)
from metadata.generated.schema.security.client.openMetadataJWTClientConfig import (
    OpenMetadataJWTClientConfig,
)
from metadata.generated.schema.type.entityLineage import EntitiesEdge, LineageDetails
from metadata.generated.schema.type.entityReference import EntityReference
from metadata.ingestion.models.custom_pydantic import CustomSecretStr
from metadata.ingestion.ometa.ometa_api import OpenMetadata

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SEEDS_DIR = PROJECT_ROOT / "dbt" / "seeds"


def get_client(host: str, token: str) -> OpenMetadata:
    host_port = (
        f"{host.rstrip('/')}/api" if not host.rstrip("/").endswith("/api") else host
    )
    cfg = OpenMetadataConnection(
        hostPort=host_port,
        authProvider=AuthProvider.openmetadata,
        securityConfig=OpenMetadataJWTClientConfig(jwtToken=CustomSecretStr(token)),
    )
    om = OpenMetadata(cfg)
    if not om.health_check():
        logger.error("OpenMetadata server at %s is not healthy", host)
        sys.exit(1)
    return om


def iter_pairs(prefix: str) -> list[tuple[str, str]]:
    """Walk dbt/seeds/raw_*/*.csv → (schema, table) tuples in stable order."""
    pairs: list[tuple[str, str]] = []
    for schema_dir in sorted(SEEDS_DIR.glob("raw_*/")):
        for csv in sorted(schema_dir.glob("*.csv")):
            pairs.append((schema_dir.name, csv.stem))
    return pairs


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--host", default=os.environ.get("AI_SDK_HOST"))
    p.add_argument("--token", default=os.environ.get("AI_SDK_TOKEN"))
    p.add_argument("--database", default="dev")
    p.add_argument("--bucket", default="collate-summit-data")
    p.add_argument("--s3-service", default="banking-s3")
    p.add_argument("--db-service", default="banking-redshift")
    p.add_argument("--prefix", default="raw")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if not args.host or not args.token:
        logger.error("Set AI_SDK_HOST and AI_SDK_TOKEN (or pass --host/--token).")
        return 2

    om = get_client(args.host, args.token)

    pairs = iter_pairs(args.prefix)
    logger.info("Creating %d lineage edges S3 -> Redshift", len(pairs))

    ok = fail = 0
    for schema, table in pairs:
        # Container FQN: the S3 connector stores the manifest dataPath as a
        # single FQN segment with slashes preserved (no dot-splitting), i.e.
        # <service>.<bucket>.<prefix>/<schema>/<table>
        container_fqn = (
            f"{args.s3_service}.{args.bucket}.{args.prefix}/{schema}/{table}"
        )
        table_fqn = f"{args.db_service}.{args.database}.{schema}.{table}"

        container = om.get_by_name(entity=Container, fqn=container_fqn)
        if container is None:
            logger.warning("Skip: container not found in OM: %s", container_fqn)
            fail += 1
            continue

        rs_table = om.get_by_name(entity=Table, fqn=table_fqn)
        if rs_table is None:
            logger.warning("Skip: table not found in OM: %s", table_fqn)
            fail += 1
            continue

        edge = AddLineageRequest(
            edge=EntitiesEdge(
                fromEntity=EntityReference(id=container.id, type="container"),
                toEntity=EntityReference(id=rs_table.id, type="table"),
                lineageDetails=LineageDetails(
                    description="Loaded via COPY from S3 by scripts/load_to_redshift.sh",
                    source="ExternalTableLineage",
                ),
            )
        )
        try:
            om.add_lineage(edge)
            ok += 1
            logger.info("  + %s -> %s", container_fqn, table_fqn)
        except Exception as exc:
            logger.error("  ! %s -> %s: %s", container_fqn, table_fqn, exc)
            fail += 1

    logger.info("Done. created=%d, failed=%d", ok, fail)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
