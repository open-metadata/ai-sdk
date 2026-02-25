"""
Create OpenMetadata Users, Domains, and assign ownership and domain
membership to the Jaffle Shop demo database tables.

Requires:
    pip install openmetadata-ingestion

Usage:
    export AI_SDK_HOST=http://localhost:8585
    export AI_SDK_TOKEN=<your-jwt-token>
    python create_owners_and_domains.py

    # Or pass arguments directly:
    python create_owners_and_domains.py --host http://localhost:8585 --token <jwt>

    # Custom service / database names:
    python create_owners_and_domains.py --service "jaffle shop" --database jaffle_shop
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass, field

from metadata.generated.schema.api.domains.createDomain import CreateDomainRequest
from metadata.generated.schema.api.teams.createUser import CreateUserRequest
from metadata.generated.schema.entity.data.table import Table
from metadata.generated.schema.entity.domains.domain import Domain, DomainType
from metadata.generated.schema.entity.services.connections.metadata.openMetadataConnection import (
    AuthProvider,
    OpenMetadataConnection,
)
from metadata.generated.schema.entity.teams.user import User
from metadata.generated.schema.security.client.openMetadataJWTClientConfig import (
    OpenMetadataJWTClientConfig,
)
from metadata.generated.schema.type.basic import (
    EntityName,
    Markdown,
)
from metadata.generated.schema.type.entityReference import EntityReference
from metadata.generated.schema.type.entityReferenceList import EntityReferenceList
from metadata.ingestion.models.custom_pydantic import CustomSecretStr
from metadata.ingestion.ometa.ometa_api import OpenMetadata

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Connection (same helper as create_glossaries_and_metrics.py)
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
# User definitions
# ---------------------------------------------------------------------------

USERS: list[dict[str, str]] = [
    {
        "name": "alice.johnson",
        "email": "alice.johnson@jaffleshop.com",
        "displayName": "Alice Johnson",
        "description": "Data Engineering Lead responsible for data pipelines and transformations.",
    },
    {
        "name": "bob.smith",
        "email": "bob.smith@jaffleshop.com",
        "displayName": "Bob Smith",
        "description": "Finance Analyst owning revenue and financial reporting data.",
    },
    {
        "name": "carol.williams",
        "email": "carol.williams@jaffleshop.com",
        "displayName": "Carol Williams",
        "description": "Marketing Analyst responsible for campaign and channel analytics.",
    },
    {
        "name": "dave.brown",
        "email": "dave.brown@jaffleshop.com",
        "displayName": "Dave Brown",
        "description": "Data Platform Engineer managing raw data ingestion and infrastructure.",
    },
    {
        "name": "eve.davis",
        "email": "eve.davis@jaffleshop.com",
        "displayName": "Eve Davis",
        "description": "Product Analyst owning core business dimensions and fact tables.",
    },
]


# ---------------------------------------------------------------------------
# Domain definitions
# ---------------------------------------------------------------------------

DOMAINS: list[dict[str, str | DomainType]] = [
    {
        "name": "Finance",
        "displayName": "Finance",
        "description": "Financial data covering revenue, discounts, shipping costs, and profitability metrics.",
        "domainType": DomainType.Consumer_aligned,
    },
    {
        "name": "Marketing",
        "displayName": "Marketing",
        "description": "Marketing analytics including campaigns, ad spend, channel attribution, and conversion tracking.",
        "domainType": DomainType.Consumer_aligned,
    },
    {
        "name": "Sales",
        "displayName": "Sales",
        "description": "Core commerce data: customers, products, orders, payments, inventory, and support.",
        "domainType": DomainType.Source_aligned,
    },
    {
        "name": "DataEngineering",
        "displayName": "Data Engineering",
        "description": "Staging and intermediate transformation layers managed by the data platform team.",
        "domainType": DomainType.Aggregate,
    },
]


# ---------------------------------------------------------------------------
# Table → owner mapping  (schema pattern → user name)
# ---------------------------------------------------------------------------

# Each entry: (schema_prefix, user_name)
# Evaluated in order; first match wins.
OWNER_RULES: list[tuple[str, str]] = [
    ("marts_finance", "bob.smith"),
    ("marts_marketing", "carol.williams"),
    ("marts_core", "eve.davis"),
    ("staging", "alice.johnson"),
    ("intermediate", "alice.johnson"),
    ("raw_", "dave.brown"),
]


# ---------------------------------------------------------------------------
# Table → domain mapping  (schema pattern → domain name)
# ---------------------------------------------------------------------------

DOMAIN_RULES: list[tuple[str, str]] = [
    ("marts_finance", "Finance"),
    ("raw_stripe", "Finance"),
    ("marts_marketing", "Marketing"),
    ("raw_marketing", "Marketing"),
    ("staging", "DataEngineering"),
    ("intermediate", "DataEngineering"),
    ("marts_core", "Sales"),
    ("raw_jaffle_shop", "Sales"),
    ("raw_inventory", "Sales"),
    ("raw_support", "Sales"),
]

# All schemas that should be processed
ALL_SCHEMAS: list[str] = [
    "raw_jaffle_shop",
    "raw_stripe",
    "raw_inventory",
    "raw_marketing",
    "raw_support",
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
    """Track created and failed entities."""

    users_created: list[str] = field(default_factory=list)
    users_failed: list[str] = field(default_factory=list)
    domains_created: list[str] = field(default_factory=list)
    domains_failed: list[str] = field(default_factory=list)
    owners_assigned: list[str] = field(default_factory=list)
    owners_failed: list[str] = field(default_factory=list)
    domains_assigned: list[str] = field(default_factory=list)
    domains_assign_failed: list[str] = field(default_factory=list)

    @property
    def has_failures(self) -> bool:
        return bool(
            self.users_failed
            or self.domains_failed
            or self.owners_failed
            or self.domains_assign_failed
        )

    def print_summary(self) -> None:
        total_ok = (
            len(self.users_created)
            + len(self.domains_created)
            + len(self.owners_assigned)
            + len(self.domains_assigned)
        )
        total_fail = (
            len(self.users_failed)
            + len(self.domains_failed)
            + len(self.owners_failed)
            + len(self.domains_assign_failed)
        )

        logger.info("")
        logger.info("=" * 60)
        logger.info("SUMMARY")
        logger.info("=" * 60)
        logger.info(
            "Users          : %d created, %d failed (of %d)",
            len(self.users_created),
            len(self.users_failed),
            len(USERS),
        )
        logger.info(
            "Domains        : %d created, %d failed (of %d)",
            len(self.domains_created),
            len(self.domains_failed),
            len(DOMAINS),
        )
        logger.info(
            "Owners Assigned: %d assigned, %d failed",
            len(self.owners_assigned),
            len(self.owners_failed),
        )
        logger.info(
            "Domains Assigned: %d assigned, %d failed",
            len(self.domains_assigned),
            len(self.domains_assign_failed),
        )
        logger.info("-" * 60)
        logger.info("Total          : %d succeeded, %d failed", total_ok, total_fail)

        if self.users_failed:
            logger.warning("Failed users: %s", ", ".join(self.users_failed))
        if self.domains_failed:
            logger.warning("Failed domains: %s", ", ".join(self.domains_failed))
        if self.owners_failed:
            logger.warning(
                "Failed owner assignments: %s", ", ".join(self.owners_failed)
            )
        if self.domains_assign_failed:
            logger.warning(
                "Failed domain assignments: %s", ", ".join(self.domains_assign_failed)
            )

        if not self.has_failures:
            logger.info("All entities created successfully.")
        logger.info("=" * 60)


# ---------------------------------------------------------------------------
# Creation helpers
# ---------------------------------------------------------------------------


def create_users(metadata: OpenMetadata, result: CreationResult) -> dict[str, User]:
    """Create all users and return a mapping of name -> entity."""
    user_map: dict[str, User] = {}
    for u in USERS:
        name = u["name"]
        try:
            entity = metadata.create_or_update(
                data=CreateUserRequest(
                    name=EntityName(name),
                    email=u["email"],
                    displayName=u["displayName"],
                    description=Markdown(u["description"]),
                )
            )
        except Exception:
            logger.exception("Failed to create user: %s", name)
            result.users_failed.append(name)
            continue
        user_map[name] = entity
        result.users_created.append(name)
        logger.info("Created user: %s (%s)", name, u["displayName"])
    return user_map


def create_domains(metadata: OpenMetadata, result: CreationResult) -> dict[str, Domain]:
    """Create all domains and return a mapping of name -> entity."""
    domain_map: dict[str, Domain] = {}
    for d in DOMAINS:
        name = d["name"]
        try:
            entity = metadata.create_or_update(
                data=CreateDomainRequest(
                    name=EntityName(name),
                    displayName=d["displayName"],
                    description=Markdown(d["description"]),
                    domainType=d["domainType"],
                )
            )
        except Exception:
            logger.exception("Failed to create domain: %s", name)
            result.domains_failed.append(name)
            continue
        domain_map[name] = entity
        result.domains_created.append(name)
        logger.info("Created domain: %s", name)
    return domain_map


def _resolve_owner(schema: str, user_map: dict[str, User]) -> User | None:
    """Find the owner for a given schema based on OWNER_RULES."""
    for prefix, user_name in OWNER_RULES:
        if schema.startswith(prefix):
            return user_map.get(user_name)
    return None


def _resolve_domain(schema: str, domain_map: dict[str, Domain]) -> Domain | None:
    """Find the domain for a given schema based on DOMAIN_RULES."""
    for prefix, domain_name in DOMAIN_RULES:
        if schema.startswith(prefix):
            return domain_map.get(domain_name)
    return None


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


def assign_owners_and_domains(
    metadata: OpenMetadata,
    user_map: dict[str, User],
    domain_map: dict[str, Domain],
    service: str,
    database: str,
    result: CreationResult,
) -> None:
    """Walk all schemas and assign owners + domains to every table."""
    for schema in ALL_SCHEMAS:
        owner = _resolve_owner(schema, user_map)
        domain = _resolve_domain(schema, domain_map)

        if owner is None and domain is None:
            logger.info("No owner or domain rule for schema %s — skipping", schema)
            continue

        tables = _list_tables_for_schema(metadata, service, database, schema)
        if not tables:
            logger.warning("No tables found in schema %s", schema)
            continue

        logger.info(
            "Processing %d tables in %s (owner=%s, domain=%s)",
            len(tables),
            schema,
            owner.name.root if owner else "none",
            domain.name.root if domain else "none",
        )

        for table in tables:
            fqn = (
                table.fullyQualifiedName.root
                if table.fullyQualifiedName
                else str(table.id)
            )

            if owner is not None:
                _assign_owner(metadata, table, owner, fqn, result)

            if domain is not None:
                _assign_domain(metadata, table, domain, fqn, result)


def _assign_owner(
    metadata: OpenMetadata,
    table: Table,
    owner: User,
    fqn: str,
    result: CreationResult,
) -> None:
    """Patch a single table's owner."""
    try:
        metadata.patch_owner(
            entity=Table,
            source=table,
            owners=EntityReferenceList(
                root=[EntityReference(id=owner.id, type="user")]
            ),
            force=True,
        )
    except Exception:
        logger.exception("Failed to assign owner to %s", fqn)
        result.owners_failed.append(fqn)
        return
    result.owners_assigned.append(fqn)
    logger.info("  Owner → %s : %s", owner.name.root, fqn)


def _assign_domain(
    metadata: OpenMetadata,
    table: Table,
    domain: Domain,
    fqn: str,
    result: CreationResult,
) -> None:
    """Patch a single table's domain."""
    try:
        metadata.patch_domain(
            entity=Table,
            source=table,
            domains=EntityReferenceList(
                root=[EntityReference(id=domain.id, type="domain")]
            ),
        )
    except Exception:
        logger.exception("Failed to assign domain to %s", fqn)
        result.domains_assign_failed.append(fqn)
        return
    result.domains_assigned.append(fqn)
    logger.info("  Domain → %s : %s", domain.name.root, fqn)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed OpenMetadata with users, domains, and table ownership for Jaffle Shop."
    )
    parser.add_argument(
        "--host",
        default=os.getenv("AI_SDK_HOST", "http://localhost:8585"),
        help="OpenMetadata API host (default: $AI_SDK_HOST or http://localhost:8585)",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("AI_SDK_TOKEN", ""),
        help="JWT token for authentication (default: $AI_SDK_TOKEN)",
    )
    parser.add_argument(
        "--service",
        default=os.getenv("AI_SDK_SERVICE", "jaffle shop"),
        help="Database service name in OpenMetadata (default: $AI_SDK_SERVICE or 'jaffle shop')",
    )
    parser.add_argument(
        "--database",
        default=os.getenv("AI_SDK_DATABASE", "jaffle_shop"),
        help="Database name (default: $AI_SDK_DATABASE or 'jaffle_shop')",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    args = parse_args()

    if not args.token:
        logger.error("No token provided. Set AI_SDK_TOKEN or pass --token.")
        sys.exit(1)

    metadata = get_metadata_client(args.host, args.token)
    result = CreationResult()

    logger.info("--- Creating Users ---")
    user_map = create_users(metadata, result)

    logger.info("--- Creating Domains ---")
    domain_map = create_domains(metadata, result)

    logger.info("--- Assigning Owners & Domains to Tables ---")
    assign_owners_and_domains(
        metadata, user_map, domain_map, args.service, args.database, result
    )

    result.print_summary()

    if result.has_failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
