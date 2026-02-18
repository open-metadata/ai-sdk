"""
Set data retention periods on Jaffle Shop demo tables.

Tables containing PII or sensitive data get shorter retention periods to comply
with data privacy regulations.  Non-sensitive tables get longer or no explicit
retention period.

Requires:
    pip install openmetadata-ingestion

Usage:
    export METADATA_HOST=http://localhost:8585
    export METADATA_TOKEN=<your-jwt-token>
    python set_retention_periods.py

    # Or pass arguments directly:
    python set_retention_periods.py --host http://localhost:8585 --token <jwt>

    # Custom service / database names:
    python set_retention_periods.py --service "jaffle shop" --database jaffle_shop
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass, field

from metadata.generated.schema.entity.data.table import Table
from metadata.generated.schema.entity.services.connections.metadata.openMetadataConnection import (
    AuthProvider,
    OpenMetadataConnection,
)
from metadata.generated.schema.security.client.openMetadataJWTClientConfig import (
    OpenMetadataJWTClientConfig,
)
from metadata.generated.schema.type.basic import Duration
from metadata.ingestion.models.custom_pydantic import CustomSecretStr
from metadata.ingestion.ometa.ometa_api import OpenMetadata

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Connection (same helper as the other seed scripts)
# ---------------------------------------------------------------------------


def get_metadata_client(host: str, token: str) -> OpenMetadata:
    """Create and return an OpenMetadata client."""
    host_port = (
        f"{host.rstrip('/')}/api" if not host.rstrip("/").endswith("/api") else host
    )
    server_config = OpenMetadataConnection(
        hostPort=host_port,
        authProvider=AuthProvider.openmetadata,
        securityConfig=OpenMetadataJWTClientConfig(
            jwtToken=CustomSecretStr(token),
        ),
    )
    metadata = OpenMetadata(server_config)
    if not metadata.health_check():
        logger.error("OpenMetadata server at %s is not healthy", host)
        sys.exit(1)
    logger.info("Connected to OpenMetadata at %s", host)
    return metadata


# ---------------------------------------------------------------------------
# Retention period definitions
# ---------------------------------------------------------------------------
#
# ISO 8601 duration format:  P[n]Y[n]M[n]DT[n]H[n]M[n]S
#   P90D   = 90 days
#   P1Y    = 1 year
#   P2Y    = 2 years
#   P5Y    = 5 years
#   P7Y    = 7 years
#
# Rationale for each tier:
#
#   90 days  – High-sensitivity PII (SSN fragments, full addresses, payment
#              card data, IP addresses).  GDPR/CCPA "minimum necessary" and
#              PCI-DSS best practice.
#
#   180 days – Moderate PII (email, phone, date of birth, billing email).
#              Retained for customer support SLAs and fraud investigation
#              windows, then purged.
#
#   1 year   – Pseudonymous / indirect PII (session IDs, browser
#              fingerprints, support ticket free-text, product reviews with
#              customer references).  Covers seasonal analytics cycles.
#
#   3 years  – Transactional data with no direct PII (orders, order items,
#              refunds, stock levels).  Supports financial audit and
#              year-over-year trending.
#
#   5 years  – Aggregated analytics views (pre-built BI summaries with no
#              row-level PII).  Retained for long-range business planning.
#
#   7 years  – Financial records required for tax and regulatory compliance
#              (payments, campaign budgets).  Aligns with IRS and SOX
#              retention guidelines.
#
# Tables that are reference/master data (products, suppliers, campaigns) are
# not assigned a retention period — they are retained indefinitely.

# Maps  schema.table  →  ISO 8601 duration
RETENTION_PERIODS: dict[str, str] = {
    # ── High-sensitivity PII: 90 days ────────────────────────────────────
    "raw_jaffle_shop.customers": "P90D",
    # Contains: email, phone_number, ssn_last_four, date_of_birth,
    #           address_line_1, city, state, postal_code
    # ── Moderate PII: 180 days ───────────────────────────────────────────
    "raw_stripe.payments": "P180D",
    # Contains: card_last_four, card_brand, billing_email, ip_address
    # ── Pseudonymous / indirect PII: 1 year ──────────────────────────────
    "raw_marketing.user_sessions": "P1Y",
    # Contains: session_id, customer_id (FK), ip_address, device/browser fingerprint
    "raw_marketing.events": "P1Y",
    # Contains: session_id (linkable to user_sessions)
    "raw_support.tickets": "P1Y",
    # Contains: customer_id (FK), free-text description (may mention PII)
    "raw_support.reviews": "P1Y",
    # Contains: customer_id (FK), free-text review_text
    # ── Transactional (no direct PII): 3 years ──────────────────────────
    "raw_jaffle_shop.orders": "P3Y",
    "raw_jaffle_shop.order_items": "P3Y",
    "raw_stripe.refunds": "P3Y",
    "raw_inventory.stock_levels": "P3Y",
    # ── Aggregated analytics views: 5 years ──────────────────────────────
    "analytics.daily_revenue": "P5Y",
    "analytics.customer_ltv": "P5Y",
    "analytics.product_performance": "P5Y",
    "analytics.campaign_roi": "P5Y",
    # ── Financial / regulatory compliance: 7 years ───────────────────────
    "raw_marketing.ad_spend": "P7Y",
    # Budget and spend records for tax / audit purposes
}

# Schemas to walk when looking for tables.
ALL_SCHEMAS: list[str] = [
    "raw_jaffle_shop",
    "raw_stripe",
    "raw_inventory",
    "raw_marketing",
    "raw_support",
    "analytics",
    "staging",
    "intermediate",
    "marts_core",
    "marts_finance",
    "marts_marketing",
]


# ---------------------------------------------------------------------------
# Result tracker
# ---------------------------------------------------------------------------


@dataclass
class CreationResult:
    """Track patched and failed tables."""

    patched: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    @property
    def has_failures(self) -> bool:
        return bool(self.failed)

    def print_summary(self) -> None:
        logger.info("")
        logger.info("=" * 60)
        logger.info("RETENTION PERIOD SUMMARY")
        logger.info("=" * 60)
        logger.info(
            "Patched : %d tables",
            len(self.patched),
        )
        logger.info(
            "Skipped : %d tables (no retention rule)",
            len(self.skipped),
        )
        logger.info(
            "Failed  : %d tables",
            len(self.failed),
        )
        logger.info("-" * 60)

        if self.failed:
            logger.warning("Failed tables: %s", ", ".join(self.failed))

        if not self.has_failures:
            logger.info("All retention periods set successfully.")
        logger.info("=" * 60)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def _list_tables_for_schema(
    metadata: OpenMetadata, service: str, database: str, schema: str
) -> list[Table]:
    """List all tables in a given schema."""
    schema_fqn = f"{service}.{database}.{schema}"
    return list(
        metadata.list_all_entities(
            entity=Table,
            params={"database": schema_fqn},
        )
    )


def _table_schema_and_name(table: Table) -> str | None:
    """Extract 'schema.table_name' from a Table's FQN.

    FQN format: service.database.schema.table
    """
    fqn = table.fullyQualifiedName
    if fqn is None:
        return None
    parts = fqn.root.split(".")
    if len(parts) < 4:
        return None
    return f"{parts[-2]}.{parts[-1]}"


def set_retention_periods(
    metadata: OpenMetadata,
    service: str,
    database: str,
    result: CreationResult,
) -> None:
    """Walk all schemas and set retention periods on matching tables."""
    for schema in ALL_SCHEMAS:
        tables = _list_tables_for_schema(metadata, service, database, schema)
        if not tables:
            logger.info("No tables found in schema %s", schema)
            continue

        logger.info("Processing %d tables in %s", len(tables), schema)

        for table in tables:
            schema_table = _table_schema_and_name(table)
            fqn = (
                table.fullyQualifiedName.root
                if table.fullyQualifiedName
                else str(table.id)
            )

            if schema_table is None or schema_table not in RETENTION_PERIODS:
                result.skipped.append(fqn)
                continue

            duration = RETENTION_PERIODS[schema_table]
            _patch_retention(metadata, table, duration, fqn, result)


def _patch_retention(
    metadata: OpenMetadata,
    table: Table,
    duration: str,
    fqn: str,
    result: CreationResult,
) -> None:
    """Apply a retention period to a single table via JSON Patch."""
    try:
        destination = table.model_copy(deep=True)
        destination.retentionPeriod = Duration(duration)

        metadata.patch(
            entity=Table,
            source=table,
            destination=destination,
        )
    except Exception:
        logger.exception("Failed to set retention period on %s", fqn)
        result.failed.append(fqn)
        return

    result.patched.append(fqn)
    logger.info("  %s → %s : %s", duration, fqn, _human_duration(duration))


def _human_duration(iso: str) -> str:
    """Convert an ISO 8601 duration to a human-readable label."""
    mapping = {
        "P90D": "90 days",
        "P180D": "180 days",
        "P1Y": "1 year",
        "P3Y": "3 years",
        "P5Y": "5 years",
        "P7Y": "7 years",
    }
    return mapping.get(iso, iso)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Set data retention periods on Jaffle Shop demo tables."
    )
    parser.add_argument(
        "--host",
        default=os.getenv("METADATA_HOST", "http://localhost:8585"),
        help="OpenMetadata API host (default: $METADATA_HOST or http://localhost:8585)",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("METADATA_TOKEN", ""),
        help="JWT token for authentication (default: $METADATA_TOKEN)",
    )
    parser.add_argument(
        "--service",
        default=os.getenv("METADATA_SERVICE", "jaffle shop"),
        help="Database service name in OpenMetadata (default: $METADATA_SERVICE or 'jaffle shop')",
    )
    parser.add_argument(
        "--database",
        default=os.getenv("METADATA_DATABASE", "jaffle_shop"),
        help="Database name (default: $METADATA_DATABASE or 'jaffle_shop')",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    args = parse_args()

    if not args.token:
        logger.error("No token provided. Set METADATA_TOKEN or pass --token.")
        sys.exit(1)

    metadata = get_metadata_client(args.host, args.token)
    result = CreationResult()

    logger.info("--- Setting Retention Periods ---")
    set_retention_periods(metadata, args.service, args.database, result)

    result.print_summary()

    if result.has_failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
