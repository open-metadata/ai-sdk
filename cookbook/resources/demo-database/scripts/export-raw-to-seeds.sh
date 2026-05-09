#!/usr/bin/env bash
#
# Export raw_* tables from the running PostgreSQL demo container into
# dbt seed CSVs. Run once after `make demo-database` and whenever the
# raw data changes.
#
# Output: cookbook/resources/demo-database/dbt/seeds/<schema>/<table>.csv
#
# Requires: psql client (brew install libpq && brew link --force libpq, or psql via pg client install)
set -euo pipefail

PG_CONN="host=localhost port=5433 user=jaffle_user dbname=jaffle_shop"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEEDS_DIR="${SCRIPT_DIR}/../dbt/seeds"

# Schema -> tables mapping. Keep in sync with dbt/models/staging/_sources.yml.
declare -a EXPORTS=(
  "raw_jaffle_shop:customers"
  "raw_jaffle_shop:orders"
  "raw_jaffle_shop:order_items"
  "raw_stripe:payments"
  "raw_stripe:refunds"
  "raw_inventory:products"
  "raw_inventory:suppliers"
  "raw_inventory:stock_levels"
  "raw_marketing:campaigns"
  "raw_marketing:ad_spend"
  "raw_marketing:user_sessions"
  "raw_marketing:events"
  "raw_support:tickets"
  "raw_support:reviews"
)

for entry in "${EXPORTS[@]}"; do
  schema="${entry%:*}"
  table="${entry#*:}"
  out_dir="${SEEDS_DIR}/${schema}"
  out_file="${out_dir}/${table}.csv"
  mkdir -p "${out_dir}"
  echo "Exporting ${schema}.${table} -> ${out_file}"
  psql "${PG_CONN}" -c "\copy (SELECT * FROM ${schema}.${table}) TO '${out_file}' WITH CSV HEADER"
done

echo ""
echo "Done. ${#EXPORTS[@]} tables exported to ${SEEDS_DIR}/"
echo "Review with: ls -la ${SEEDS_DIR}/raw_*/"
