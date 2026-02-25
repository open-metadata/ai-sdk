#!/bin/bash
# Ingest demo database metadata into OpenMetadata
#
# Prerequisites:
#   - Demo database running (make demo-database)
#   - dbt models built (make demo-dbt)
#   - OpenMetadata ingestion installed (pip install "openmetadata-ingestion[postgres,dbt]")
#
# Required environment variables:
#   AI_SDK_HOST  - OpenMetadata server URL (e.g. https://your-instance.getcollate.io)
#   AI_SDK_TOKEN - JWT token for authentication
#
# Usage:
#   export AI_SDK_HOST=https://your-instance.getcollate.io
#   export AI_SDK_TOKEN=your-jwt-token
#   ./scripts/ingest_metadata.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
INGESTION_DIR="${BASE_DIR}/ingestion"
DBT_DIR="${BASE_DIR}/dbt"
DBT_TARGET_DIR="${DBT_DIR}/target"

# --- Validate environment ---

if [ -z "$AI_SDK_HOST" ]; then
    echo "Error: AI_SDK_HOST is not set."
    echo "  export AI_SDK_HOST=https://your-instance.getcollate.io"
    exit 1
fi

if [ -z "$AI_SDK_TOKEN" ]; then
    echo "Error: AI_SDK_TOKEN is not set."
    echo "  export AI_SDK_TOKEN=your-jwt-token"
    exit 1
fi

if ! command -v metadata &> /dev/null; then
    echo "Error: 'metadata' CLI not found."
    echo "  pip install openmetadata-ingestion[postgres]"
    exit 1
fi

# --- Results tracking ---

RESULTS=()
FAILED=0

# --- Helper to render a YAML template and run ingestion ---

run_ingestion() {
    local name="$1"
    local yaml_template="$2"

    echo ""
    echo "=== ${name} ==="

    # Substitute env vars into a temp config file
    local config_file
    config_file=$(mktemp /tmp/om_ingestion_XXXXXXXXXX) && mv "${config_file}" "${config_file}.yaml" && config_file="${config_file}.yaml"
    export DBT_TARGET_DIR
    envsubst < "${yaml_template}" > "${config_file}"

    metadata ingest -c "${config_file}"
    local status=$?
    rm -f "${config_file}"

    if [ $status -eq 0 ]; then
        RESULTS+=("PASS  ${name}")
    else
        RESULTS+=("FAIL  ${name}")
        FAILED=$((FAILED + 1))
    fi
}

run_classification() {
    local name="$1"
    local yaml_template="$2"

    echo ""
    echo "=== ${name} ==="

    # Substitute env vars into a temp config file
    local config_file
    config_file=$(mktemp /tmp/om_ingestion_XXXXXXXXXX) && mv "${config_file}" "${config_file}.yaml" && config_file="${config_file}.yaml"
    envsubst < "${yaml_template}" > "${config_file}"

    metadata classify -c "${config_file}"
    local status=$?
    rm -f "${config_file}"

    if [ $status -eq 0 ]; then
        RESULTS+=("PASS  ${name}")
    else
        RESULTS+=("FAIL  ${name}")
        FAILED=$((FAILED + 1))
    fi
}

# --- Generate dbt artifacts if missing ---

if [ ! -f "${DBT_TARGET_DIR}/manifest.json" ]; then
    echo "dbt artifacts not found in ${DBT_TARGET_DIR}. Generating..."
    (cd "${DBT_DIR}" && DBT_PROFILES_DIR="${DBT_DIR}" dbt run && dbt docs generate)
fi

# --- Run ingestion workflows ---

echo "Ingesting demo metadata into ${AI_SDK_HOST}"

# 1. PostgreSQL metadata (tables, views, schemas)
run_ingestion "PostgreSQL Metadata" "${INGESTION_DIR}/postgres.yaml"

# 2. dbt metadata (descriptions, tags, lineage from models)
run_ingestion "dbt Metadata" "${INGESTION_DIR}/dbt.yaml"

# 3. PostgreSQL lineage (query-based lineage from pg_stat_statements)
run_ingestion "PostgreSQL Lineage" "${INGESTION_DIR}/postgres_lineage.yaml"

# 4. Metabase dashboards and charts
run_ingestion "Metabase Dashboards" "${INGESTION_DIR}/metabase.yaml"

# 5. Auto-classification (PII detection on raw schemas)
run_classification "Auto Classification" "${INGESTION_DIR}/postgres_auto_classification.yaml"

# --- Summary report ---

echo ""
echo "==============================="
echo "  Ingestion Report"
echo "==============================="
for result in "${RESULTS[@]}"; do
    echo "  ${result}"
done
echo "==============================="

if [ $FAILED -gt 0 ]; then
    echo "  ${FAILED} workflow(s) failed."
    exit 1
else
    echo "  All workflows passed."
    echo "  Open ${AI_SDK_HOST} to explore the ingested metadata."
fi
