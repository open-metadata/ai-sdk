#!/usr/bin/env bash
# =====================================================================
# load_to_bigquery.sh
# ---------------------------------------------------------------------
# Loads every (schema, table) pair from the local seed CSVs into the
# matching BigQuery table. Run after:
#
#   1. scripts/generate_seed_data.py            (writes the CSVs)
#   2. scripts/bigquery/bootstrap_bigquery.sh   (creates datasets + tables)
#
# There is no staging bucket: BigQuery loads local files directly. The
# per-table loop is required rather than incidental — local loads support
# neither wildcards nor multiple files per invocation.
#
# Required env:
#   BANKING_GCP_PROJECT   Target GCP project ID
#
# Optional env:
#   BANKING_BQ_LOCATION   Dataset location (default: US)
#
# Authentication: see bootstrap_bigquery.sh.
# =====================================================================
set -euo pipefail

: "${BANKING_GCP_PROJECT:?Set BANKING_GCP_PROJECT to the target GCP project ID}"
BANKING_BQ_LOCATION="${BANKING_BQ_LOCATION:-US}"

# BigQuery caps local-file loads at 100 MB. Every seed table fits today, but
# not by much: raw_digital.login_attempts is ~75 MB at N_LOGIN_ATTEMPTS=400000.
# Raising that constant much further needs a GCS staging step instead.
MAX_LOCAL_LOAD_BYTES=$((100 * 1024 * 1024))

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SEEDS_DIR="${PROJECT_ROOT}/dbt/seeds"
SCHEMAS_DIR="${PROJECT_ROOT}/sql/bq_schemas"

if [[ ! -d "${SEEDS_DIR}" ]]; then
    echo "Seeds directory not found: ${SEEDS_DIR}" >&2
    exit 1
fi

if [[ ! -d "${SCHEMAS_DIR}" ]]; then
    echo "Load schemas not found: ${SCHEMAS_DIR}" >&2
    echo "Run 'python scripts/generate_ddl.py' first." >&2
    exit 1
fi

echo "Banking demo: loading seed CSVs into BigQuery"
echo "  Project:  ${BANKING_GCP_PROJECT}"
echo "  Location: ${BANKING_BQ_LOCATION}"
echo "  Source:   ${SEEDS_DIR}"
echo

loaded=0
failed=0
shopt -s nullglob

for schema_dir in "${SEEDS_DIR}"/raw_*/; do
    schema="$(basename "${schema_dir%/}")"
    for csv in "${schema_dir}"*.csv; do
        table="$(basename "${csv}" .csv)"
        schema_json="${SCHEMAS_DIR}/${schema}.${table}.json"

        if [[ ! -f "${schema_json}" ]]; then
            echo "  !! ${schema}.${table}: no load schema at ${schema_json}" >&2
            failed=$((failed + 1))
            continue
        fi

        size=$(wc -c < "${csv}" | tr -d ' ')
        if (( size > MAX_LOCAL_LOAD_BYTES )); then
            echo "  !! ${schema}.${table}: $((size / 1024 / 1024)) MB exceeds the 100 MB" >&2
            echo "     local-load limit. Stage it in GCS and load from gs:// instead." >&2
            failed=$((failed + 1))
            continue
        fi

        echo "  -> ${schema}.${table}  ($((size / 1024)) KB)"

        # --replace makes re-running idempotent, matching the Redshift path's
        # TRUNCATE-then-COPY. --null_marker pairs with the \N that
        # generate_seed_data.py writes for missing values: without it BigQuery
        # would load empty text fields as '' where Redshift yields NULL.
        if bq --project_id="${BANKING_GCP_PROJECT}" load \
            --location="${BANKING_BQ_LOCATION}" \
            --source_format=CSV \
            --skip_leading_rows=1 \
            --replace \
            --max_bad_records=5 \
            --null_marker='\N' \
            --schema="${schema_json}" \
            --quiet \
            "${BANKING_GCP_PROJECT}:${schema}.${table}" \
            "${csv}"
        then
            loaded=$((loaded + 1))
        else
            echo "     FAILED" >&2
            failed=$((failed + 1))
        fi
    done
done

echo
echo "Load complete. Loaded: ${loaded}.  Failed: ${failed}."

if (( failed > 0 )); then
    exit 1
fi
