#!/usr/bin/env bash
# =====================================================================
# bootstrap_bigquery.sh
# ---------------------------------------------------------------------
# Creates the raw datasets and source tables for the banking demo.
#
# Datasets are created here rather than in SQL because each one needs its
# location pinned at creation time. Tables come from sql/bigquery_init.sql,
# which scripts/generate_ddl.py renders from schema/registry.py.
#
# Safe to re-run: dataset creation tolerates an existing dataset, and the
# table DDL uses CREATE OR REPLACE. Nothing here drops a dataset — see
# `make destroy-bigquery` for that.
#
# Required env:
#   BANKING_GCP_PROJECT   Target GCP project ID
#
# Optional env:
#   BANKING_BQ_LOCATION   Dataset location (default: US). Must match the
#                         `location` in the dbt profile's bigquery output.
#
# Authentication: the bq CLI reads gcloud's credential store, not
# GOOGLE_APPLICATION_CREDENTIALS. Either
#   gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS"
# or
#   gcloud auth login
# before running. dbt, OpenMetadata and Superset read the key file directly.
# =====================================================================
set -euo pipefail

: "${BANKING_GCP_PROJECT:?Set BANKING_GCP_PROJECT to the target GCP project ID}"
BANKING_BQ_LOCATION="${BANKING_BQ_LOCATION:-US}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
INIT_SQL="${PROJECT_ROOT}/sql/bigquery_init.sql"

if [[ ! -f "${INIT_SQL}" ]]; then
    echo "DDL file not found: ${INIT_SQL}" >&2
    echo "Run 'python scripts/generate_ddl.py' first." >&2
    exit 1
fi

echo "Banking demo: bootstrapping BigQuery datasets and tables"
echo "  Project:  ${BANKING_GCP_PROJECT}"
echo "  Location: ${BANKING_BQ_LOCATION}"
echo "  DDL:      ${INIT_SQL}"
echo

# ---------------------------------------------------------------------
# Fail early with an actionable message rather than 38 identical auth errors.
# ---------------------------------------------------------------------
if ! bq --project_id="${BANKING_GCP_PROJECT}" ls >/dev/null 2>&1; then
    echo "Cannot reach BigQuery in project ${BANKING_GCP_PROJECT}." >&2
    echo "Authenticate the bq CLI first:" >&2
    echo "  gcloud auth activate-service-account --key-file=\"\$GOOGLE_APPLICATION_CREDENTIALS\"" >&2
    exit 1
fi

# ---------------------------------------------------------------------
# Datasets. The raw list comes from the registry so it cannot drift from
# the DDL. dbt creates staging / intermediate / marts_* itself.
# ---------------------------------------------------------------------
RAW_SCHEMAS="$(cd "${PROJECT_ROOT}" && python3 -c \
    'from schema.registry import raw_schemas; print(" ".join(raw_schemas()))')"

for schema in ${RAW_SCHEMAS}; do
    if bq --project_id="${BANKING_GCP_PROJECT}" show --dataset "${BANKING_GCP_PROJECT}:${schema}" >/dev/null 2>&1; then
        echo "  dataset ${schema} already exists"
    else
        echo "  creating dataset ${schema}"
        bq --project_id="${BANKING_GCP_PROJECT}" mk \
            --dataset \
            --location="${BANKING_BQ_LOCATION}" \
            --description="Banking demo raw source data (${schema})" \
            "${BANKING_GCP_PROJECT}:${schema}"
    fi
done

# ---------------------------------------------------------------------
# Tables.
# ---------------------------------------------------------------------
echo
echo "Creating tables from ${INIT_SQL}..."
bq --project_id="${BANKING_GCP_PROJECT}" query \
    --location="${BANKING_BQ_LOCATION}" \
    --use_legacy_sql=false \
    --quiet \
    < "${INIT_SQL}"

table_count=$(grep -c 'CREATE OR REPLACE TABLE' "${INIT_SQL}")
schema_count=$(echo "${RAW_SCHEMAS}" | wc -w | tr -d ' ')

echo
echo "Bootstrap complete. ${schema_count} datasets and ${table_count} tables ready."
