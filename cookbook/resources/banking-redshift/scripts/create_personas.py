"""
Seed AI personas required for the banking-redshift demo.

Creates the ``DataEngineer`` and ``DataSteward`` AI personas on the target
Collate instance via ``POST /v1/agents/personas``. These are the two personas
the banking demo's landing-page widgets are keyed on. Assign one of them as
the ``defaultPersona`` on the demo user so the Action Required and
Recommended Improvements widgets render the demo cards.

These personas may already exist as built-in ``provider: system`` seeds on a
freshly bootstrapped instance. This script is idempotent: it skips any persona
that already exists by name.

Requires:
    pip install requests

Usage:
    export AI_SDK_HOST=https://your-instance.getcollate.io
    export AI_SDK_TOKEN=<your-jwt-token>
    python create_personas.py

    # Or with explicit args:
    python create_personas.py --host https://your-instance.getcollate.io --token ...

    # Dry run:
    python create_personas.py --dry-run
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Any

import requests

logger = logging.getLogger(__name__)


PERSONAS_PATH = "/v1/agents/personas"


def _normalize_host(host: str) -> str:
    host = host.rstrip("/")
    if not host.endswith("/api"):
        host = f"{host}/api"
    return host


DATA_ENGINEER_PROMPT = (
    "You are an expert Data Engineer with deep knowledge of data "
    "infrastructure, pipeline development, and distributed systems. Your "
    "role is to help users:\n\n"
    "**Core Responsibilities:**\n"
    "- Design and implement scalable data pipelines (ETL/ELT)\n"
    "- Optimize data storage and processing systems\n"
    "- Ensure data pipeline reliability, monitoring, and alerting\n"
    "- Integrate diverse data sources and formats\n"
    "- Implement data security and access controls\n"
    "- Performance tune databases and data processing workflows\n"
    "- Troubleshoot data pipeline failures and bottlenecks\n"
    "- Maintain data infrastructure and platform operations\n\n"
    "**Technical Expertise:**\n"
    "- Data pipeline frameworks (Apache Airflow, Prefect, Dagster)\n"
    "- Big data technologies (Spark, Hadoop, Kafka, Flink)\n"
    "- Cloud platforms (AWS, GCP, Azure) and their data services\n"
    "- Database systems (SQL, NoSQL, time-series, graph databases)\n"
    "- Data formats and serialization (Parquet, Avro, JSON, protobuf)\n"
    "- Containerization and orchestration (Docker, Kubernetes)\n"
    "- Infrastructure as Code (Terraform, CloudFormation)\n"
    "- Data quality validation and schema evolution\n\n"
    "Help users build robust, scalable data infrastructure that enables "
    "reliable data delivery and supports organizational data needs "
    "efficiently."
)


DATA_STEWARD_PROMPT = (
    "You are an expert Data Steward with deep knowledge of data governance, "
    "quality management, and regulatory compliance. Your role is to help "
    "users:\n\n"
    "**Core Responsibilities:**\n"
    "- Implement and maintain data governance policies and procedures\n"
    "- Monitor and improve data quality across the organization\n"
    "- Ensure compliance with data regulations (GDPR, CCPA, HIPAA, etc.)\n"
    "- Manage data lineage, ownership, and access controls\n"
    "- Establish data standards, definitions, and documentation\n"
    "- Coordinate data classification and sensitive data identification\n"
    "- Resolve data quality issues and incidents\n\n"
    "**Expertise Areas:**\n"
    "- Data governance frameworks and best practices\n"
    "- Data quality metrics, monitoring, and remediation\n"
    "- Privacy regulations and compliance requirements\n"
    "- Master data management (MDM) principles\n"
    "- Data lifecycle management and retention policies\n"
    "- Data cataloging and metadata management\n"
    "- Data access controls and security protocols\n\n"
    "Help users build a robust data governance foundation that enables "
    "trustworthy, compliant, and valuable data assets."
)


PERSONAS: list[dict[str, str]] = [
    {
        "name": "DataEngineer",
        "displayName": "Data Engineer",
        "description": (
            "Technical expert in data pipeline development, infrastructure "
            "optimization, and data integration. Specializes in building "
            "scalable, reliable data systems and ETL/ELT processes."
        ),
        "prompt": DATA_ENGINEER_PROMPT,
        "provider": "system",
    },
    {
        "name": "DataSteward",
        "displayName": "Data Steward",
        "description": (
            "Data governance expert focused on data quality, compliance, "
            "and metadata management. Ensures data assets are properly "
            "cataloged, documented, and meet organizational standards."
        ),
        "prompt": DATA_STEWARD_PROMPT,
        "provider": "system",
    },
]


@dataclass
class Result:
    created: list[str] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)

    @property
    def has_failures(self) -> bool:
        return bool(self.failed)

    def print_summary(self) -> None:
        logger.info("--- Summary ---")
        logger.info("  Created : %d", len(self.created))
        for name in self.created:
            logger.info("    + %s", name)
        logger.info("  Skipped : %d", len(self.skipped))
        for name, reason in self.skipped:
            logger.info("    = %s (%s)", name, reason)
        logger.info("  Failed  : %d", len(self.failed))
        for name, reason in self.failed:
            logger.info("    ! %s — %s", name, reason)


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def persona_exists(host: str, token: str, name: str) -> bool:
    url = f"{_normalize_host(host)}{PERSONAS_PATH}/name/{name}"
    response = requests.get(url, headers=_headers(token), timeout=30)
    if response.status_code == 200:
        return True
    if response.status_code == 404:
        return False
    response.raise_for_status()
    return False


def create_persona(host: str, token: str, payload: dict[str, Any]) -> None:
    url = f"{_normalize_host(host)}{PERSONAS_PATH}"
    response = requests.post(url, json=payload, headers=_headers(token), timeout=30)
    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"HTTP {response.status_code}: {response.text[:500]}",
        )


def run(host: str, token: str, dry_run: bool = False) -> Result:
    result = Result()
    for persona in PERSONAS:
        name = persona["name"]
        try:
            if persona_exists(host, token, name):
                result.skipped.append((name, "already exists"))
                logger.info("Skipping %s (already exists)", name)
                continue
            if dry_run:
                logger.info("[dry-run] would create persona %s", name)
                result.created.append(name)
                continue
            create_persona(host, token, persona)
            result.created.append(name)
            logger.info("Created persona %s", name)
        except requests.HTTPError as e:
            result.failed.append((name, str(e)))
            logger.exception("Failed to create persona %s", name)
        except RuntimeError as e:
            result.failed.append((name, str(e)))
            logger.error("Failed to create persona %s: %s", name, e)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument(
        "--host",
        default=os.environ.get("AI_SDK_HOST"),
        help="Collate host (or env AI_SDK_HOST).",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("AI_SDK_TOKEN"),
        help="JWT bearer token (or env AI_SDK_TOKEN).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without making changes.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (DEBUG/INFO/WARNING/ERROR).",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if not args.host or not args.token:
        parser.error("--host/--token (or AI_SDK_HOST/AI_SDK_TOKEN env vars) required")

    logger.info("Seeding personas against %s (dry_run=%s)", args.host, args.dry_run)
    result = run(args.host, args.token, dry_run=args.dry_run)
    result.print_summary()
    return 1 if result.has_failures else 0


if __name__ == "__main__":
    sys.exit(main())
