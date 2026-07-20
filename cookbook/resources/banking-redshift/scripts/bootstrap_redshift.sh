#!/usr/bin/env bash
# =====================================================================
# bootstrap_redshift.sh
# ---------------------------------------------------------------------
# Runs sql/redshift_init.sql against the target Redshift cluster to
# create the 8 raw schemas and 38 source tables. Safe to re-run: the
# script issues DROP SCHEMA ... CASCADE before recreating.
#
# Required env:
#   REDSHIFT_HOST       Redshift cluster endpoint
#   REDSHIFT_PORT       Cluster port (typically 5439)
#   REDSHIFT_DATABASE   Database name
#   REDSHIFT_USER       Username
#   REDSHIFT_PASSWORD   Password
# =====================================================================
set -euo pipefail

: "${REDSHIFT_HOST:?Set REDSHIFT_HOST to the Redshift cluster endpoint}"
: "${REDSHIFT_PORT:?Set REDSHIFT_PORT to the Redshift port (e.g. 5439)}"
: "${REDSHIFT_DATABASE:?Set REDSHIFT_DATABASE to the target database}"
: "${REDSHIFT_USER:?Set REDSHIFT_USER to the Redshift user}"
: "${REDSHIFT_PASSWORD:?Set REDSHIFT_PASSWORD to the Redshift password}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
INIT_SQL="${PROJECT_ROOT}/sql/redshift_init.sql"

if [[ ! -f "${INIT_SQL}" ]]; then
    echo "DDL file not found: ${INIT_SQL}" >&2
    exit 1
fi

echo "Banking demo: bootstrapping Redshift schemas and tables"
echo "  Host:     ${REDSHIFT_HOST}:${REDSHIFT_PORT}"
echo "  Database: ${REDSHIFT_DATABASE}"
echo "  User:     ${REDSHIFT_USER}"
echo "  DDL:      ${INIT_SQL}"
echo

PGPASSWORD="${REDSHIFT_PASSWORD}" psql \
    --host="${REDSHIFT_HOST}" \
    --port="${REDSHIFT_PORT}" \
    --dbname="${REDSHIFT_DATABASE}" \
    --username="${REDSHIFT_USER}" \
    --set ON_ERROR_STOP=1 \
    --file="${INIT_SQL}"

echo
echo "Bootstrap complete. 8 schemas and 38 tables ready."
