#!/usr/bin/env bash
#
# Provision the local Superset instance for the banking demo:
#   1. Verify the selected warehouse's connection env vars are set.
#   2. Wait for Superset's /health endpoint to be reachable.
#   3. Sanity-check the admin login.
#   4. Hand off to `setup_superset_charts.py`, which creates the warehouse
#      database connection, datasets, charts, and dashboards.
#
# Warehouse selection:
#   WAREHOUSE   redshift (default) | bigquery
#
# Safe to re-run: the Python script is idempotent (existing objects are
# skipped on 409/422).

set -euo pipefail

WAREHOUSE="${WAREHOUSE:-redshift}"
SUPERSET_URL="${SUPERSET_URL:-http://localhost:8088}"
SUPERSET_ADMIN_USER="${SUPERSET_ADMIN_USER:-admin}"
SUPERSET_ADMIN_PASSWORD="${SUPERSET_ADMIN_PASSWORD:-BankAdmin123!}"
SUPERSET_ADMIN_EMAIL="${SUPERSET_ADMIN_EMAIL:-admin@bank.demo}"
SUPERSET_CONTAINER="${SUPERSET_CONTAINER:-banking_superset}"

# ---------------------------------------------------------------------------
# 1. Verify required env vars.
# ---------------------------------------------------------------------------
case "${WAREHOUSE}" in
    redshift)
        required_vars=(
            REDSHIFT_HOST
            REDSHIFT_PORT
            REDSHIFT_DATABASE
            REDSHIFT_USER
            REDSHIFT_PASSWORD
        )
        ;;
    bigquery)
        # Only the host needs the key file: setup_superset_charts.py reads it
        # and posts the contents as the connection's credentials_info, so
        # Superset never touches the path and needs no bind mount.
        required_vars=(
            BANKING_GCP_PROJECT
            GOOGLE_APPLICATION_CREDENTIALS
        )
        ;;
    *)
        echo "ERROR: unknown WAREHOUSE '${WAREHOUSE}'. Use 'redshift' or 'bigquery'." >&2
        exit 1
        ;;
esac

missing=()
for var in "${required_vars[@]}"; do
    if [ -z "${!var:-}" ]; then
        missing+=("$var")
    fi
done

if [ "${#missing[@]}" -gt 0 ]; then
    echo "ERROR: missing required env vars: ${missing[*]}" >&2
    echo "Set them in your shell (or in a .env file) before running this script." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# 2. Wait for Superset to be healthy.
# ---------------------------------------------------------------------------
echo "Waiting for Superset at ${SUPERSET_URL}/health ..."
deadline=$(( $(date +%s) + 300 ))  # 5 minute timeout
until curl -fsS "${SUPERSET_URL}/health" >/dev/null 2>&1; do
    if [ "$(date +%s)" -ge "$deadline" ]; then
        echo "ERROR: Superset did not become healthy within 5 minutes." >&2
        exit 1
    fi
    sleep 3
done
echo "Superset is healthy."

# ---------------------------------------------------------------------------
# 3. Verify admin login. If the user doesn't exist (the compose bootstrap
#    swallows create-admin failures via `|| true`), create them now via
#    `docker exec`. If they exist but the password drifted, reset it.
# ---------------------------------------------------------------------------
check_login() {
    curl -s -o /dev/null -w "%{http_code}" \
        -X POST "${SUPERSET_URL}/api/v1/security/login" \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"${SUPERSET_ADMIN_USER}\",\"password\":\"${SUPERSET_ADMIN_PASSWORD}\",\"provider\":\"db\",\"refresh\":true}"
}

echo "Verifying admin login ..."
login_status=$(check_login)

if [ "$login_status" != "200" ]; then
    echo "Admin login returned HTTP ${login_status}. Provisioning admin user via docker exec ..."

    if ! command -v docker >/dev/null 2>&1; then
        echo "ERROR: docker CLI not found. Cannot auto-provision admin." >&2
        echo "Either install docker, or create the user manually:" >&2
        echo "  docker exec -it ${SUPERSET_CONTAINER} superset fab create-admin \\" >&2
        echo "    --username ${SUPERSET_ADMIN_USER} --firstname Bank --lastname Admin \\" >&2
        echo "    --email ${SUPERSET_ADMIN_EMAIL} --password '${SUPERSET_ADMIN_PASSWORD}'" >&2
        exit 1
    fi

    # Try create. If user already exists, fab returns non-zero — fall through
    # to reset-password.
    docker exec "${SUPERSET_CONTAINER}" superset fab create-admin \
        --username "${SUPERSET_ADMIN_USER}" \
        --firstname Bank --lastname Admin \
        --email "${SUPERSET_ADMIN_EMAIL}" \
        --password "${SUPERSET_ADMIN_PASSWORD}" 2>/dev/null || true

    # Always reset password to ensure it matches the env var
    docker exec "${SUPERSET_CONTAINER}" superset fab reset-password \
        --username "${SUPERSET_ADMIN_USER}" \
        --password "${SUPERSET_ADMIN_PASSWORD}" >/dev/null 2>&1 || true

    # Re-test login
    login_status=$(check_login)
    if [ "$login_status" != "200" ]; then
        echo "ERROR: admin login still failing (HTTP ${login_status}) after provisioning." >&2
        echo "Inspect: docker logs ${SUPERSET_CONTAINER} | tail -50" >&2
        exit 1
    fi
fi
echo "Admin login OK."

# ---------------------------------------------------------------------------
# 4. Run the Python provisioning script.
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="${SCRIPT_DIR}/setup_superset_charts.py"

if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "ERROR: cannot find ${PYTHON_SCRIPT}" >&2
    exit 1
fi

echo "Running ${PYTHON_SCRIPT} (warehouse=${WAREHOUSE}) ..."
WAREHOUSE="$WAREHOUSE" \
SUPERSET_URL="$SUPERSET_URL" \
SUPERSET_ADMIN_USER="$SUPERSET_ADMIN_USER" \
SUPERSET_ADMIN_PASSWORD="$SUPERSET_ADMIN_PASSWORD" \
    python3 "$PYTHON_SCRIPT"

echo ""
echo "Done. Open ${SUPERSET_URL} (admin / ${SUPERSET_ADMIN_PASSWORD})."
