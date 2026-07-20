"""
Create OpenMetadata Users, Domains, and assign ownership and domain
membership to the banking-redshift demo database tables.

Requires:
    pip install openmetadata-ingestion

Usage:
    export AI_SDK_HOST=http://localhost:8585
    export AI_SDK_TOKEN=<your-jwt-token>
    python create_owners_and_domains.py

    # Or pass arguments directly:
    python create_owners_and_domains.py --host http://localhost:8585 --token <jwt>

    # Custom service / database names:
    python create_owners_and_domains.py --service banking-redshift --database dev
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass, field

from metadata.generated.schema.api.domains.createDataProduct import (
    CreateDataProductRequest,
)
from metadata.generated.schema.api.domains.createDomain import CreateDomainRequest
from metadata.generated.schema.api.teams.createPersona import CreatePersonaRequest
from metadata.generated.schema.api.teams.createTeam import CreateTeamRequest
from metadata.generated.schema.api.teams.createUser import CreateUserRequest
from metadata.generated.schema.entity.data.table import Table
from metadata.generated.schema.entity.domains.dataProduct import DataProduct
from metadata.generated.schema.entity.domains.domain import Domain, DomainType
from metadata.generated.schema.entity.services.connections.metadata.openMetadataConnection import (
    AuthProvider,
    OpenMetadataConnection,
)
from metadata.generated.schema.entity.teams.persona import Persona
from metadata.generated.schema.entity.teams.team import Team, TeamType
from metadata.generated.schema.entity.teams.user import User
from metadata.generated.schema.security.client.openMetadataJWTClientConfig import (
    OpenMetadataJWTClientConfig,
)
from metadata.generated.schema.type.basic import (
    EntityName,
    FullyQualifiedEntityName,
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
        "name": "alice.chen",
        "email": "alice.chen@bank.demo",
        "displayName": "Alice Chen",
        "description": "Lead Data Steward — accountable for customer, account, card, and digital-channel data quality, PII classification, glossary stewardship, and metadata governance across the bank.",
    },
    {
        "name": "marcus.williams",
        "email": "marcus.williams@bank.demo",
        "displayName": "Marcus Williams",
        "description": "Head of Credit Risk — owns loan, delinquency, credit scoring, and loss-provision data.",
    },
    {
        "name": "priya.patel",
        "email": "priya.patel@bank.demo",
        "displayName": "Priya Patel",
        "description": "Head of Wealth — owns investment accounts, holdings, trades, and AUM data.",
    },
    {
        "name": "david.kim",
        "email": "david.kim@bank.demo",
        "displayName": "David Kim",
        "description": "Chief Compliance Officer — owns KYC, AML, sanctions screening, and SAR data.",
    },
    {
        "name": "sara.johnson",
        "email": "sara.johnson@bank.demo",
        "displayName": "Sara Johnson",
        "description": "Data Engineering Lead — owns staging and intermediate transformation layers.",
    },
    {
        "name": "robert.garcia",
        "email": "robert.garcia@bank.demo",
        "displayName": "Robert Garcia",
        "description": "Chief Financial Officer — owns finance mart data including NIM, fee revenue, monthly P&L, branch performance, and loan-loss provisioning reporting.",
    },
]


# ---------------------------------------------------------------------------
# Domain definitions
# ---------------------------------------------------------------------------

DOMAINS: list[dict[str, str | DomainType]] = [
    {
        "name": "RetailBanking",
        "displayName": "Retail Banking",
        "description": "Customer, account, card, branch, transaction, and digital-channel data for the retail bank.",
        "domainType": DomainType.Source_aligned,
    },
    {
        "name": "LendingCredit",
        "displayName": "Lending and Credit",
        "description": "Loan products, applications, payments, collateral, credit scoring, delinquency, and loss provisioning.",
        "domainType": DomainType.Source_aligned,
    },
    {
        "name": "WealthMgmt",
        "displayName": "Wealth Management",
        "description": "Investment accounts, securities, holdings, trades, and assets-under-management data.",
        "domainType": DomainType.Source_aligned,
    },
    {
        "name": "ComplianceAML",
        "displayName": "Compliance and AML",
        "description": "KYC, AML alerts, sanctions screening, and Suspicious Activity Reports.",
        "domainType": DomainType.Consumer_aligned,
    },
    {
        "name": "Finance",
        "displayName": "Finance",
        "description": "P&L, NIM, fee revenue, balance sheet, and regulatory reporting marts.",
        "domainType": DomainType.Source_aligned,
    },
    {
        "name": "Digital",
        "displayName": "Digital",
        "description": "Online and mobile banking telemetry, login attempts, fraud signals, and web sessions.",
        "domainType": DomainType.Source_aligned,
    },
]


# Per-domain expert assignments (domain → user name(s)).
# Experts are referenced by FQN string under CreateDomainRequest.experts.
DOMAIN_EXPERTS: dict[str, list[str]] = {
    "RetailBanking": ["alice.chen"],
    "LendingCredit": ["marcus.williams"],
    "WealthMgmt": ["priya.patel"],
    "ComplianceAML": ["david.kim"],
    "Finance": ["robert.garcia"],
    "Digital": ["alice.chen"],
}


# ---------------------------------------------------------------------------
# Team definitions
# ---------------------------------------------------------------------------
#
# Banks model their organisation as Teams in OpenMetadata. Each team is a
# Group (TeamType.Group), holding the users who steward a slice of the data.

TEAMS: list[dict] = [
    {
        "name": "RiskOrg",
        "displayName": "Risk",
        "description": (
            "Credit risk, delinquency, loss provisioning, and IFRS 9 staging. "
            "Owners of marts_risk and raw_risk (excluding sanctions screening "
            "which sits under Compliance)."
        ),
        "teamType": TeamType.Group,
        "users": ["marcus.williams", "david.kim"],
    },
    {
        "name": "ComplianceOrg",
        "displayName": "Compliance",
        "description": (
            "KYC, AML monitoring, sanctions screening, and Suspicious Activity "
            "Report filings. Owners of raw_risk.sanctions, raw_risk.sars, "
            "raw_risk.kyc_documents."
        ),
        "teamType": TeamType.Group,
        "users": ["david.kim"],
    },
    {
        "name": "WealthOrg",
        "displayName": "Wealth",
        "description": (
            "Investment accounts, securities, holdings, trades, and assets "
            "under management. Owners of raw_wealth and marts_wealth."
        ),
        "teamType": TeamType.Group,
        "users": ["priya.patel"],
    },
    {
        "name": "FinanceOrg",
        "displayName": "Finance",
        "description": (
            "P&L, NIM, fee revenue, balance sheet, branch performance, and "
            "regulatory reporting. Owners of marts_finance."
        ),
        "teamType": TeamType.Group,
        "users": ["robert.garcia"],
    },
    {
        "name": "DataPlatform",
        "displayName": "Data Platform",
        "description": (
            "Data engineering and governance. Owners of staging and "
            "intermediate dbt layers; sets glossary, lineage, and PII "
            "standards across the bank."
        ),
        "teamType": TeamType.Group,
        "users": ["sara.johnson", "alice.chen"],
    },
    {
        "name": "RetailBankingOrg",
        "displayName": "Retail Banking",
        "description": (
            "Customer, account, card, branch, transaction, and digital-channel "
            "operations for the retail bank."
        ),
        "teamType": TeamType.Group,
        "users": ["alice.chen"],
    },
]


# ---------------------------------------------------------------------------
# Persona definitions (UI-customisation entity)
# ---------------------------------------------------------------------------
#
# Personas in OpenMetadata represent the role a user takes on within the
# platform — used to drive UI customisation, default landing pages,
# notification preferences, and curated views.

PERSONAS: list[dict] = [
    {
        "name": "CFO",
        "displayName": "Chief Financial Officer",
        "description": (
            "Persona for finance leadership — focuses on P&L, NIM, fee revenue, "
            "branch performance, regulatory ratios (ROA, ROE, CET1)."
        ),
        "users": ["robert.garcia"],
    },
    {
        "name": "RiskOfficer",
        "displayName": "Risk Officer",
        "description": (
            "Persona for credit-risk leadership — focuses on delinquency, NPL, "
            "ECL provisioning, IFRS 9 staging, and stress-testing inputs."
        ),
        "users": ["marcus.williams"],
    },
    {
        "name": "ComplianceOfficer",
        "displayName": "Compliance Officer",
        "description": (
            "Persona for AML/BSA compliance — focuses on KYC refresh, AML "
            "alerts, SAR filings, sanctions screening, and PEP review."
        ),
        "users": ["david.kim"],
    },
    {
        "name": "DataSteward",
        "displayName": "Data Steward",
        "description": (
            "Persona for governance and metadata — focuses on glossary "
            "maintenance, PII classification, lineage coverage, and data "
            "quality."
        ),
        "users": ["alice.chen"],
    },
    {
        "name": "WealthAdvisor",
        "displayName": "Wealth Advisor",
        "description": (
            "Persona for wealth-management business — focuses on AUM, "
            "holdings, trades, and client investment performance."
        ),
        "users": ["priya.patel"],
    },
    {
        "name": "DataEngineer",
        "displayName": "Data Engineer",
        "description": (
            "Persona for data platform / engineering — focuses on staging, "
            "intermediate, dbt models, and ingestion pipelines."
        ),
        "users": ["sara.johnson"],
    },
]


# ---------------------------------------------------------------------------
# Table → owner mapping  (schema pattern → user name)
# ---------------------------------------------------------------------------

# Each entry: (schema_prefix, user_name)
# Evaluated in order; first match wins.
OWNER_RULES: list[tuple[str, str]] = [
    ("raw_core_banking", "alice.chen"),
    ("raw_transactions", "alice.chen"),
    ("raw_cards", "alice.chen"),
    ("raw_lending", "marcus.williams"),
    # raw_risk is split per-table — see RAW_RISK_OWNER_OVERRIDES below.
    ("raw_risk", "david.kim"),
    ("raw_wealth", "priya.patel"),
    ("raw_digital", "alice.chen"),
    ("raw_marketing", "alice.chen"),
    ("marts_core", "alice.chen"),
    ("marts_finance", "robert.garcia"),
    ("marts_risk", "marcus.williams"),
    ("marts_wealth", "priya.patel"),
    ("marts_marketing", "alice.chen"),
    ("staging", "sara.johnson"),
    ("intermediate", "sara.johnson"),
]


# Per-table owner overrides keyed by "schema.table" (lowercased).
# Used where a single schema spans multiple owners (e.g., raw_risk).
OWNER_OVERRIDES: dict[str, str] = {
    "raw_risk.credit_scores": "marcus.williams",
}


# ---------------------------------------------------------------------------
# Table → domain mapping  (schema pattern → domain name)
# ---------------------------------------------------------------------------

DOMAIN_RULES: list[tuple[str, str]] = [
    ("raw_core_banking", "RetailBanking"),
    ("raw_transactions", "RetailBanking"),
    ("raw_cards", "RetailBanking"),
    ("raw_lending", "LendingCredit"),
    # raw_risk is split per-table — see RAW_RISK_DOMAIN_OVERRIDES below.
    ("raw_risk", "ComplianceAML"),
    ("raw_wealth", "WealthMgmt"),
    ("raw_digital", "Digital"),
    ("raw_marketing", "RetailBanking"),
    ("marts_core", "RetailBanking"),
    ("marts_finance", "Finance"),
    ("marts_risk", "LendingCredit"),
    ("marts_wealth", "WealthMgmt"),
    ("marts_marketing", "RetailBanking"),
    # staging and intermediate have no domain assignment per spec.
]


# Per-table domain overrides keyed by "schema.table" (lowercased).
DOMAIN_OVERRIDES: dict[str, str] = {
    "raw_risk.credit_scores": "LendingCredit",
}


# ---------------------------------------------------------------------------
# Data Product definitions
# ---------------------------------------------------------------------------
#
# Data Products group curated assets within a Domain around a business
# capability. Each entry below declares its owning Domain, owner, optional
# experts, and the table assets that comprise the product. Assets are resolved
# at runtime by listing tables in the configured schemas and applying
# optional table-name regex filters.

@dataclass
class DataProductAssetRule:
    """Asset selector for a Data Product.

    - ``schema``: schema name within the database
    - ``table_patterns``: optional list of regex patterns matched against the
      table name. ``None`` means include every table in the schema.
    """

    schema: str
    table_patterns: list[str] | None = None


DATA_PRODUCTS: list[dict] = [
    # Retail Banking
    {
        "name": "CustomerAccounts360",
        "displayName": "Customer Accounts 360",
        "description": (
            "Unified view of retail customers, deposit accounts, and branch "
            "relationships — feeds onboarding, segmentation, and service "
            "analytics."
        ),
        "domain": "RetailBanking",
        "owner": "alice.chen",
        "experts": ["alice.chen", "sara.johnson"],
        "assets": [
            DataProductAssetRule(schema="raw_core_banking"),
            DataProductAssetRule(schema="marts_core"),
        ],
    },
    {
        "name": "CardOperations",
        "displayName": "Card Operations",
        "description": (
            "Issued cards, card transactions, and disputes used by fraud, "
            "rewards, and chargeback workflows."
        ),
        "domain": "RetailBanking",
        "owner": "alice.chen",
        "experts": ["alice.chen"],
        "assets": [
            DataProductAssetRule(schema="raw_cards"),
        ],
    },
    {
        "name": "TransactionFeed",
        "displayName": "Transaction Feed",
        "description": (
            "Authoritative ledger of retail-banking transactions for "
            "downstream analytics, AML scoring, and customer 360."
        ),
        "domain": "RetailBanking",
        "owner": "alice.chen",
        "experts": ["alice.chen"],
        "assets": [
            DataProductAssetRule(schema="raw_transactions"),
        ],
    },
    # Lending and Credit
    {
        "name": "LoanPortfolio",
        "displayName": "Loan Portfolio",
        "description": (
            "Loan products, applications, payments, and collateral with the "
            "marts powering risk dashboards and IFRS 9 staging."
        ),
        "domain": "LendingCredit",
        "owner": "marcus.williams",
        "experts": ["marcus.williams"],
        "assets": [
            DataProductAssetRule(schema="raw_lending"),
            DataProductAssetRule(schema="marts_risk"),
        ],
    },
    {
        "name": "CreditScoring",
        "displayName": "Credit Scoring",
        "description": (
            "Customer credit-score snapshots feeding underwriting decisions "
            "and risk-based pricing."
        ),
        "domain": "LendingCredit",
        "owner": "marcus.williams",
        "experts": ["marcus.williams"],
        "assets": [
            DataProductAssetRule(
                schema="raw_risk", table_patterns=[r"^credit_scores$"]
            ),
        ],
    },
    # Wealth Management
    {
        "name": "WealthPortfolio",
        "displayName": "Wealth Portfolio",
        "description": (
            "Investment accounts, holdings, trades, and AUM marts used by "
            "wealth advisors and portfolio analytics."
        ),
        "domain": "WealthMgmt",
        "owner": "priya.patel",
        "experts": ["priya.patel"],
        "assets": [
            DataProductAssetRule(schema="raw_wealth"),
            DataProductAssetRule(schema="marts_wealth"),
        ],
    },
    # Compliance and AML
    {
        "name": "AMLMonitoring",
        "displayName": "AML Monitoring",
        "description": (
            "KYC documents, AML alerts, sanctions screening hits, and "
            "Suspicious Activity Reports powering compliance reviews."
        ),
        "domain": "ComplianceAML",
        "owner": "david.kim",
        "experts": ["david.kim"],
        "assets": [
            DataProductAssetRule(
                schema="raw_risk",
                table_patterns=[
                    r"^aml_alerts$",
                    r"^sars$",
                    r"^sanctions.*",
                    r"^kyc_documents$",
                    r"^pep_screening$",
                ],
            ),
        ],
    },
    # Finance
    {
        "name": "FinanceMarts",
        "displayName": "Finance Marts",
        "description": (
            "P&L, NIM, fee revenue, branch performance, and regulatory "
            "reporting marts for CFO and finance teams."
        ),
        "domain": "Finance",
        "owner": "robert.garcia",
        "experts": ["robert.garcia"],
        "assets": [
            DataProductAssetRule(schema="marts_finance"),
        ],
    },
    # Digital
    {
        "name": "DigitalChannels",
        "displayName": "Digital Channels",
        "description": (
            "Web and mobile telemetry — sessions, login attempts, app events "
            "— used by digital product and fraud teams."
        ),
        "domain": "Digital",
        "owner": "alice.chen",
        "experts": ["alice.chen"],
        "assets": [
            DataProductAssetRule(schema="raw_digital"),
        ],
    },
]


# All schemas that should be processed
ALL_SCHEMAS: list[str] = [
    "raw_core_banking",
    "raw_transactions",
    "raw_cards",
    "raw_lending",
    "raw_risk",
    "raw_wealth",
    "raw_digital",
    "raw_marketing",
    "staging",
    "intermediate",
    "marts_core",
    "marts_finance",
    "marts_risk",
    "marts_wealth",
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
    teams_created: list[str] = field(default_factory=list)
    teams_failed: list[str] = field(default_factory=list)
    personas_created: list[str] = field(default_factory=list)
    personas_failed: list[str] = field(default_factory=list)
    owners_assigned: list[str] = field(default_factory=list)
    owners_failed: list[str] = field(default_factory=list)
    domains_assigned: list[str] = field(default_factory=list)
    domains_assign_failed: list[str] = field(default_factory=list)
    data_products_created: list[str] = field(default_factory=list)
    data_products_failed: list[str] = field(default_factory=list)

    @property
    def has_failures(self) -> bool:
        return bool(
            self.users_failed
            or self.domains_failed
            or self.teams_failed
            or self.personas_failed
            or self.owners_failed
            or self.domains_assign_failed
            or self.data_products_failed
        )

    def print_summary(self) -> None:
        total_ok = (
            len(self.users_created)
            + len(self.domains_created)
            + len(self.teams_created)
            + len(self.personas_created)
            + len(self.owners_assigned)
            + len(self.domains_assigned)
            + len(self.data_products_created)
        )
        total_fail = (
            len(self.users_failed)
            + len(self.domains_failed)
            + len(self.teams_failed)
            + len(self.personas_failed)
            + len(self.owners_failed)
            + len(self.domains_assign_failed)
            + len(self.data_products_failed)
        )

        logger.info("")
        logger.info("=" * 60)
        logger.info("SUMMARY")
        logger.info("=" * 60)
        logger.info(
            "Users           : %d created, %d failed (of %d)",
            len(self.users_created),
            len(self.users_failed),
            len(USERS),
        )
        logger.info(
            "Domains         : %d created, %d failed (of %d)",
            len(self.domains_created),
            len(self.domains_failed),
            len(DOMAINS),
        )
        logger.info(
            "Teams           : %d created, %d failed (of %d)",
            len(self.teams_created),
            len(self.teams_failed),
            len(TEAMS),
        )
        logger.info(
            "Personas        : %d created, %d failed (of %d)",
            len(self.personas_created),
            len(self.personas_failed),
            len(PERSONAS),
        )
        logger.info(
            "Owners Assigned : %d assigned, %d failed",
            len(self.owners_assigned),
            len(self.owners_failed),
        )
        logger.info(
            "Domains Assigned: %d assigned, %d failed",
            len(self.domains_assigned),
            len(self.domains_assign_failed),
        )
        logger.info(
            "Data Products   : %d created, %d failed (of %d)",
            len(self.data_products_created),
            len(self.data_products_failed),
            len(DATA_PRODUCTS),
        )
        logger.info("-" * 60)
        logger.info("Total           : %d succeeded, %d failed", total_ok, total_fail)

        if self.users_failed:
            logger.warning("Failed users: %s", ", ".join(self.users_failed))
        if self.domains_failed:
            logger.warning("Failed domains: %s", ", ".join(self.domains_failed))
        if self.teams_failed:
            logger.warning("Failed teams: %s", ", ".join(self.teams_failed))
        if self.personas_failed:
            logger.warning("Failed personas: %s", ", ".join(self.personas_failed))
        if self.owners_failed:
            logger.warning(
                "Failed owner assignments: %s", ", ".join(self.owners_failed)
            )
        if self.domains_assign_failed:
            logger.warning(
                "Failed domain assignments: %s", ", ".join(self.domains_assign_failed)
            )
        if self.data_products_failed:
            logger.warning(
                "Failed data products: %s", ", ".join(self.data_products_failed)
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


def create_domains(
    metadata: OpenMetadata,
    result: CreationResult,
    user_map: dict[str, User],
) -> dict[str, Domain]:
    """Create all domains (with domain experts) and return a name->entity mapping."""
    domain_map: dict[str, Domain] = {}
    for d in DOMAINS:
        name = d["name"]
        # Resolve experts: CreateDomainRequest.experts is List[str] (user FQNs).
        expert_names = DOMAIN_EXPERTS.get(name, [])
        experts: list[str] = []
        for u in expert_names:
            if u in user_map:
                experts.append(u)
            else:
                logger.warning(
                    "Domain expert %s not found for domain %s — skipping.",
                    u, name,
                )

        try:
            entity = metadata.create_or_update(
                data=CreateDomainRequest(
                    name=EntityName(name),
                    displayName=d["displayName"],
                    description=Markdown(d["description"]),
                    domainType=d["domainType"],
                    experts=experts or None,
                )
            )
        except Exception:
            logger.exception("Failed to create domain: %s", name)
            result.domains_failed.append(name)
            continue
        domain_map[name] = entity
        result.domains_created.append(name)
        logger.info(
            "Created domain: %s%s",
            name,
            f" (experts: {', '.join(experts)})" if experts else "",
        )
    return domain_map


def create_teams(
    metadata: OpenMetadata,
    result: CreationResult,
    user_map: dict[str, User],
) -> dict[str, Team]:
    """Create org teams and return a name->entity mapping."""
    team_map: dict[str, Team] = {}
    for t in TEAMS:
        name = t["name"]
        # Resolve user UUIDs for the team
        member_uuids = []
        for member_name in t.get("users", []):
            user = user_map.get(member_name)
            if user is None:
                logger.warning(
                    "User %s not found - skipping membership in team %s",
                    member_name, name,
                )
                continue
            member_uuids.append(user.id)

        try:
            entity = metadata.create_or_update(
                data=CreateTeamRequest(
                    name=EntityName(name),
                    displayName=t["displayName"],
                    description=Markdown(t["description"]),
                    teamType=t["teamType"],
                    users=member_uuids or None,
                )
            )
        except Exception:
            logger.exception("Failed to create team: %s", name)
            result.teams_failed.append(name)
            continue
        team_map[name] = entity
        result.teams_created.append(name)
        logger.info(
            "Created team: %s (%d members)", name, len(member_uuids)
        )
    return team_map


def create_personas(
    metadata: OpenMetadata,
    result: CreationResult,
    user_map: dict[str, User],
) -> dict[str, Persona]:
    """Create UI Personas (CFO, RiskOfficer, etc.) and return name->entity map."""
    persona_map: dict[str, Persona] = {}
    for p in PERSONAS:
        name = p["name"]
        member_uuids = []
        for member_name in p.get("users", []):
            user = user_map.get(member_name)
            if user is None:
                logger.warning(
                    "User %s not found - skipping membership in persona %s",
                    member_name, name,
                )
                continue
            member_uuids.append(user.id)

        try:
            entity = metadata.create_or_update(
                data=CreatePersonaRequest(
                    name=EntityName(name),
                    displayName=p["displayName"],
                    description=Markdown(p["description"]),
                    users=member_uuids or None,
                )
            )
        except Exception:
            logger.exception("Failed to create persona: %s", name)
            result.personas_failed.append(name)
            continue
        persona_map[name] = entity
        result.personas_created.append(name)
        logger.info(
            "Created persona: %s (%d users)", name, len(member_uuids)
        )
    return persona_map


def _resolve_owner(
    schema: str, table_name: str, user_map: dict[str, User]
) -> User | None:
    """Find the owner for a given table, honoring per-table overrides first."""
    override_key = f"{schema}.{table_name}".lower()
    if override_key in OWNER_OVERRIDES:
        return user_map.get(OWNER_OVERRIDES[override_key])
    for prefix, user_name in OWNER_RULES:
        if schema.startswith(prefix):
            return user_map.get(user_name)
    return None


def _resolve_domain(
    schema: str, table_name: str, domain_map: dict[str, Domain]
) -> Domain | None:
    """Find the domain for a given table, honoring per-table overrides first."""
    override_key = f"{schema}.{table_name}".lower()
    if override_key in DOMAIN_OVERRIDES:
        return domain_map.get(DOMAIN_OVERRIDES[override_key])
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
            params={"databaseSchema": schema_fqn},
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
        tables = _list_tables_for_schema(metadata, service, database, schema)
        if not tables:
            logger.warning("No tables found in schema %s", schema)
            continue

        logger.info("Processing %d tables in schema %s", len(tables), schema)

        for table in tables:
            table_name = table.name.root if table.name else ""
            fqn = (
                table.fullyQualifiedName.root
                if table.fullyQualifiedName
                else str(table.id)
            )

            owner = _resolve_owner(schema, table_name, user_map)
            domain = _resolve_domain(schema, table_name, domain_map)

            if owner is None and domain is None:
                logger.info("  No owner or domain for %s — skipping", fqn)
                continue

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
# Data Product creation
# ---------------------------------------------------------------------------


def _resolve_data_product_assets(
    metadata: OpenMetadata,
    service: str,
    database: str,
    rules: list[DataProductAssetRule],
) -> list[EntityReference]:
    """Resolve a Data Product's asset rules into table EntityReferences."""
    import re

    refs: list[EntityReference] = []
    for rule in rules:
        tables = _list_tables_for_schema(metadata, service, database, rule.schema)
        if not tables:
            logger.warning(
                "No tables found in schema %s for data product asset rule", rule.schema
            )
            continue

        patterns = [re.compile(p) for p in (rule.table_patterns or [])]
        for table in tables:
            table_name = table.name.root if table.name else ""
            if patterns and not any(p.search(table_name) for p in patterns):
                continue
            refs.append(EntityReference(id=table.id, type="table"))
    return refs


def create_data_products(
    metadata: OpenMetadata,
    result: CreationResult,
    user_map: dict[str, User],
    domain_map: dict[str, Domain],
    service: str,
    database: str,
) -> None:
    """Create Data Products, attaching them to their owning Domain and assets."""
    for dp in DATA_PRODUCTS:
        name = dp["name"]
        domain_name = dp["domain"]
        domain_entity = domain_map.get(domain_name)
        if domain_entity is None:
            logger.warning(
                "Domain %s missing — skipping data product %s", domain_name, name
            )
            result.data_products_failed.append(name)
            continue

        owner_name = dp.get("owner")
        owners: EntityReferenceList | None = None
        if owner_name:
            owner_user = user_map.get(owner_name)
            if owner_user is None:
                logger.warning(
                    "Owner %s not found for data product %s — leaving unowned",
                    owner_name, name,
                )
            else:
                owners = EntityReferenceList(
                    root=[EntityReference(id=owner_user.id, type="user")]
                )

        experts = [u for u in dp.get("experts", []) if u in user_map] or None
        assets = _resolve_data_product_assets(metadata, service, database, dp["assets"])

        domain_fqn = (
            domain_entity.fullyQualifiedName.root
            if domain_entity.fullyQualifiedName
            else domain_name
        )

        try:
            entity = metadata.create_or_update(
                data=CreateDataProductRequest(
                    name=EntityName(name),
                    displayName=dp["displayName"],
                    description=Markdown(dp["description"]),
                    domains=[FullyQualifiedEntityName(domain_fqn)],
                    owners=owners,
                    experts=experts,
                )
            )
        except Exception:
            logger.exception("Failed to create data product: %s", name)
            result.data_products_failed.append(name)
            continue

        if assets:
            dp_fqn = (
                entity.fullyQualifiedName.root
                if entity.fullyQualifiedName
                else name
            )
            try:
                metadata.add_assets_to_data_product(name=dp_fqn, assets=assets)
            except Exception:
                logger.exception(
                    "Failed to attach %d assets to data product %s",
                    len(assets), name,
                )

        result.data_products_created.append(name)
        logger.info(
            "Created data product: %s (domain=%s, assets=%d)",
            name, domain_name, len(assets),
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed OpenMetadata with users, domains, and table ownership for banking-redshift."
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
        default=os.getenv("AI_SDK_SERVICE", "banking-redshift"),
        help="Database service name in OpenMetadata (default: $AI_SDK_SERVICE or 'banking-redshift')",
    )
    parser.add_argument(
        "--database",
        default=os.getenv("REDSHIFT_DATABASE", "dev"),
        help="Database name (default: $REDSHIFT_DATABASE or 'dev')",
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
    domain_map = create_domains(metadata, result, user_map)

    logger.info("--- Creating Teams ---")
    create_teams(metadata, result, user_map)

    logger.info("--- Creating Personas ---")
    create_personas(metadata, result, user_map)

    logger.info("--- Assigning Owners & Domains to Tables ---")
    assign_owners_and_domains(
        metadata, user_map, domain_map, args.service, args.database, result
    )

    logger.info("--- Creating Data Products ---")
    create_data_products(
        metadata, result, user_map, domain_map, args.service, args.database
    )

    result.print_summary()

    if result.has_failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
