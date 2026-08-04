#!/usr/bin/env bash
# Ingest banking demo metadata into OpenMetadata.
#
# Runs every workflow for the selected warehouse, then the shared dbt and
# Superset workflows. The S3 storage and S3-lineage steps exist only for the
# Redshift target, which stages its raw data in a bucket; the BigQuery target
# loads local files and has no storage service.
#
# Warehouse selection:
#   WAREHOUSE                  redshift (default) | bigquery
#
# Required environment variables (all warehouses):
#   AI_SDK_HOST                OpenMetadata server URL (e.g. https://your-instance.getcollate.io)
#   AI_SDK_TOKEN               JWT token for authentication
#   SUPERSET_ADMIN_PASSWORD    Superset admin password
#
# Required for WAREHOUSE=redshift:
#   REDSHIFT_HOST              Redshift host
#   REDSHIFT_PORT              Redshift port (typically 5439)
#   REDSHIFT_USER              Redshift username
#   REDSHIFT_PASSWORD          Redshift password
#   REDSHIFT_DATABASE          Redshift database name
#   AWS_ACCESS_KEY_ID          AWS access key
#   AWS_SECRET_ACCESS_KEY      AWS secret key
#   AWS_REGION                 AWS region (e.g. us-east-1)
#   BANKING_S3_BUCKET          S3 bucket name for the banking demo
#
# Required for WAREHOUSE=bigquery:
#   BANKING_GCP_PROJECT            GCP project ID
#   GOOGLE_APPLICATION_CREDENTIALS Path to the service account JSON key
#
# Usage:
#   ./scripts/ingest_metadata.sh
#   WAREHOUSE=bigquery ./scripts/ingest_metadata.sh

set -euo pipefail

: "${AI_SDK_HOST:?Set AI_SDK_HOST}"
: "${AI_SDK_TOKEN:?Set AI_SDK_TOKEN}"

WAREHOUSE="${WAREHOUSE:-redshift}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INGESTION_DIR="$SCRIPT_DIR/../ingestion"
RESOURCE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
export PROJECT_ROOT="${RESOURCE_ROOT}"

case "${WAREHOUSE}" in
    redshift)
        : "${REDSHIFT_HOST:?Set REDSHIFT_HOST for WAREHOUSE=redshift}"
        ;;
    bigquery)
        : "${BANKING_GCP_PROJECT:?Set BANKING_GCP_PROJECT for WAREHOUSE=bigquery}"
        : "${GOOGLE_APPLICATION_CREDENTIALS:?Set GOOGLE_APPLICATION_CREDENTIALS for WAREHOUSE=bigquery}"
        ;;
    *)
        echo "Unknown WAREHOUSE '${WAREHOUSE}'. Use 'redshift' or 'bigquery'." >&2
        exit 1
        ;;
esac

# os.path.expandvars in the metadata CLI does not honor ${VAR:-default}, and
# leaves an unset variable as the literal ${NAME}, so defaults must be applied
# here before the YAMLs are loaded.
export BANKING_DBT_TARGET="${BANKING_DBT_TARGET:-${RESOURCE_ROOT}/dbt/target}"
export SUPERSET_URL="${SUPERSET_URL:-http://localhost:8088}"
export SUPERSET_ADMIN_USER="${SUPERSET_ADMIN_USER:-admin}"
export BANKING_BQ_LOCATION="${BANKING_BQ_LOCATION:-US}"

# The shared dbt and Superset YAMLs are warehouse-neutral; these two variables
# point them at the right services. Keeping the BI service per-warehouse lets
# both targets coexist in one OpenMetadata instance.
export BANKING_DB_SERVICE="${BANKING_DB_SERVICE:-banking-${WAREHOUSE}}"
export BANKING_BI_SERVICE="${BANKING_BI_SERVICE:-banking-superset-${WAREHOUSE}}"

RESULTS=()
FAILED=0

run_workflow() {
    local name="$1"
    local yaml_file="$2"
    local subcommand="${3:-ingest}"

    echo ""
    echo "==============================="
    echo "  ${name}"
    echo "==============================="

    if metadata "${subcommand}" -c "${yaml_file}"; then
        RESULTS+=("PASS  ${name}")
    else
        RESULTS+=("FAIL  ${name}")
        FAILED=$((FAILED + 1))
    fi
}

if ! command -v metadata >/dev/null 2>&1; then
    echo "Error: 'metadata' CLI not found."
    if [[ "${WAREHOUSE}" == "bigquery" ]]; then
        echo "  pip install \"openmetadata-ingestion[bigquery,dbt,superset]\""
    else
        echo "  pip install \"openmetadata-ingestion[redshift,dbt,superset,s3]\""
    fi
    exit 1
fi

echo "Ingesting banking demo metadata into ${AI_SDK_HOST}"
echo "  Warehouse:   ${WAREHOUSE}"
echo "  DB service:  ${BANKING_DB_SERVICE}"
echo "  BI service:  ${BANKING_BI_SERVICE}"

# Ordered so that storage and database services exist before lineage / dbt /
# dashboards try to resolve them.
if [[ "${WAREHOUSE}" == "redshift" ]]; then
    run_workflow "S3 Storage Metadata"        "${INGESTION_DIR}/redshift/s3.yaml"
fi

WAREHOUSE_DIR="${INGESTION_DIR}/${WAREHOUSE}"
run_workflow "${WAREHOUSE} Metadata"          "${WAREHOUSE_DIR}/${WAREHOUSE}.yaml"
run_workflow "${WAREHOUSE} Profiler"          "${WAREHOUSE_DIR}/${WAREHOUSE}_profiler.yaml"           "profile"
run_workflow "${WAREHOUSE} PII Auto-Classify" "${WAREHOUSE_DIR}/${WAREHOUSE}_autoclassification.yaml" "classify"
run_workflow "${WAREHOUSE} Lineage"           "${WAREHOUSE_DIR}/${WAREHOUSE}_lineage.yaml"
run_workflow "dbt Metadata"                   "${INGESTION_DIR}/shared/dbt.yaml"
run_workflow "Superset Dashboards"            "${INGESTION_DIR}/shared/superset.yaml"

echo ""
echo "==============================="
echo "  Ingestion Report"
echo "==============================="
for result in "${RESULTS[@]}"; do
    echo "  ${result}"
done
echo "==============================="

if [ "${FAILED}" -gt 0 ]; then
    echo "  ${FAILED} workflow(s) failed."
    exit 1
fi

echo "  All workflows passed."
echo "  Open ${AI_SDK_HOST} to explore the ingested metadata."
