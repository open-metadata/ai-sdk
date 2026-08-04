#!/usr/bin/env bash
# =====================================================================
# upload_to_s3.sh
# ---------------------------------------------------------------------
# Uploads every dbt seed CSV under dbt/seeds/raw_*/*.csv to S3 in the
# layout expected by load_to_redshift.sh:
#
#     s3://${BANKING_S3_BUCKET}/${BANKING_S3_PREFIX}/<schema>/<table>/<table>.csv
#
# Required env:
#   BANKING_S3_BUCKET  Target S3 bucket name (will be created if missing)
#
# Optional env:
#   AWS_REGION         AWS region (default: us-east-1)
#   BANKING_S3_PREFIX  S3 key prefix (default: raw)
# =====================================================================
set -euo pipefail

: "${BANKING_S3_BUCKET:?Set BANKING_S3_BUCKET to the target S3 bucket name}"
AWS_REGION="${AWS_REGION:-us-east-1}"
BANKING_S3_PREFIX="${BANKING_S3_PREFIX:-raw}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SEEDS_DIR="${PROJECT_ROOT}/dbt/seeds"

if [[ ! -d "${SEEDS_DIR}" ]]; then
    echo "Seeds directory not found: ${SEEDS_DIR}" >&2
    exit 1
fi

echo "Banking demo: uploading CSV seeds to S3"
echo "  Bucket:  s3://${BANKING_S3_BUCKET}"
echo "  Prefix:  ${BANKING_S3_PREFIX}"
echo "  Region:  ${AWS_REGION}"
echo "  Source:  ${SEEDS_DIR}"
echo

# ---------------------------------------------------------------------
# Ensure the bucket exists. us-east-1 must NOT pass --create-bucket-configuration.
# ---------------------------------------------------------------------
if aws s3api head-bucket --bucket "${BANKING_S3_BUCKET}" --region "${AWS_REGION}" 2>/dev/null; then
    echo "Bucket already exists: ${BANKING_S3_BUCKET}"
else
    echo "Creating bucket ${BANKING_S3_BUCKET} in ${AWS_REGION}..."
    if [[ "${AWS_REGION}" == "us-east-1" ]]; then
        aws s3api create-bucket \
            --bucket "${BANKING_S3_BUCKET}" \
            --region "${AWS_REGION}"
    else
        aws s3api create-bucket \
            --bucket "${BANKING_S3_BUCKET}" \
            --region "${AWS_REGION}" \
            --create-bucket-configuration "LocationConstraint=${AWS_REGION}"
    fi
fi

# ---------------------------------------------------------------------
# Iterate over every dbt/seeds/raw_*/*.csv and upload.
# ---------------------------------------------------------------------
uploaded=0
failed=0
shopt -s nullglob

for schema_dir in "${SEEDS_DIR}"/raw_*/; do
    schema="$(basename "${schema_dir%/}")"
    for csv in "${schema_dir}"*.csv; do
        table="$(basename "${csv}" .csv)"
        s3_key="${BANKING_S3_PREFIX}/${schema}/${table}/${table}.csv"
        s3_uri="s3://${BANKING_S3_BUCKET}/${s3_key}"

        echo "  -> ${schema}.${table}  ->  ${s3_uri}"
        # Retry once on transient failure; enforce SSE-S3 encryption at rest.
        attempt=0
        while (( attempt < 2 )); do
            if aws s3 cp "${csv}" "${s3_uri}" \
                --region "${AWS_REGION}" \
                --sse AES256 \
                --only-show-errors
            then
                uploaded=$((uploaded + 1))
                break
            fi
            attempt=$((attempt + 1))
            if (( attempt >= 2 )); then
                echo "     FAILED after ${attempt} attempts" >&2
                failed=$((failed + 1))
            else
                echo "     retrying..." >&2
                sleep 2
            fi
        done
    done
done

echo
echo "Done. Uploaded: ${uploaded}.  Failed: ${failed}."

# ---------------------------------------------------------------------
# Publish the OpenMetadata storage manifest at the bucket root.
# Without it, the S3 connector only registers the bucket — it cannot
# discover per-table CSV schemas. Regenerate from current seeds first
# so it always reflects the latest file layout.
# ---------------------------------------------------------------------
echo
echo "Regenerating + publishing OpenMetadata S3 manifest..."
python3 "${SCRIPT_DIR}/generate_s3_manifest.py"

MANIFEST_LOCAL="${PROJECT_ROOT}/openmetadata.json"
MANIFEST_S3="s3://${BANKING_S3_BUCKET}/openmetadata.json"
if aws s3 cp "${MANIFEST_LOCAL}" "${MANIFEST_S3}" \
    --region "${AWS_REGION}" \
    --sse AES256 \
    --only-show-errors
then
    echo "Manifest uploaded -> ${MANIFEST_S3}"
else
    echo "WARNING: manifest upload failed. S3 ingestion will only register the bucket." >&2
fi

if (( failed > 0 )); then
    exit 1
fi
