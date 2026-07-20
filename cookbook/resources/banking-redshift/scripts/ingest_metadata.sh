#!/usr/bin/env bash
# Ingest banking demo metadata (S3 + Redshift + dbt + Superset) into OpenMetadata.
#
# Required environment variables:
#   AI_SDK_HOST                OpenMetadata server URL (e.g. https://your-instance.getcollate.io)
#   AI_SDK_TOKEN               JWT token for authentication
#   REDSHIFT_HOST              Redshift host
#   REDSHIFT_PORT              Redshift port (typically 5439)
#   REDSHIFT_USER              Redshift username
#   REDSHIFT_PASSWORD          Redshift password
#   REDSHIFT_DATABASE          Redshift database name
#   SUPERSET_ADMIN_PASSWORD    Superset admin password
#   AWS_ACCESS_KEY_ID          AWS access key
#   AWS_SECRET_ACCESS_KEY      AWS secret key
#   AWS_REGION                 AWS region (e.g. us-east-1)
#   BANKING_S3_BUCKET          S3 bucket name for the banking demo
#
# Usage:
#   ./scripts/ingest_metadata.sh

set -euo pipefail

: "${AI_SDK_HOST:?Set AI_SDK_HOST}"
: "${AI_SDK_TOKEN:?Set AI_SDK_TOKEN}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INGESTION_DIR="$SCRIPT_DIR/../ingestion"
RESOURCE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
export PROJECT_ROOT="${RESOURCE_ROOT}"

# os.path.expandvars in the metadata CLI does not honor ${VAR:-default}, so
# defaults must be applied here before the YAMLs are loaded.
export BANKING_DBT_TARGET="${BANKING_DBT_TARGET:-${RESOURCE_ROOT}/dbt/target}"
export SUPERSET_URL="${SUPERSET_URL:-http://localhost:8088}"
export SUPERSET_ADMIN_USER="${SUPERSET_ADMIN_USER:-admin}"

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
    echo "  pip install \"openmetadata-ingestion[redshift,dbt,superset,s3]\""
    exit 1
fi

echo "Ingesting banking demo metadata into ${AI_SDK_HOST}"

# Ordered so that storage and database services exist before lineage / dbt / dashboards
# try to resolve them.
run_workflow "S3 Storage Metadata"        "${INGESTION_DIR}/s3.yaml"
run_workflow "Redshift Metadata"          "${INGESTION_DIR}/redshift.yaml"
run_workflow "Redshift Profiler"          "${INGESTION_DIR}/redshift_profiler.yaml"             "profile"
run_workflow "Redshift PII Auto-Classify" "${INGESTION_DIR}/redshift_autoclassification.yaml"   "classify"
run_workflow "Redshift Lineage"           "${INGESTION_DIR}/redshift_lineage.yaml"
run_workflow "dbt Metadata"               "${INGESTION_DIR}/dbt.yaml"
run_workflow "Superset Dashboards"        "${INGESTION_DIR}/superset.yaml"

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
