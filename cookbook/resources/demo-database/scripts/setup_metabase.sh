#!/bin/bash
# Setup Metabase with pre-configured questions and dashboards
# Run this after Metabase is up and the database connection is configured
# Safe to re-run: deletes existing collection and recreates everything

set -e

METABASE_URL="${METABASE_URL:-http://localhost:3000}"
METABASE_USER="${METABASE_USER:-admin@jaffle.shop}"
METABASE_PASS="${METABASE_PASS:-JaffleAdmin123!}"
COLLECTION_NAME="Jaffle Shop Analytics"

echo "Waiting for Metabase to be ready..."
until curl -s "${METABASE_URL}/api/health" | grep -q "ok"; do
    sleep 5
done
echo "Metabase is ready!"

# Get session token
echo "Logging in to Metabase..."
SESSION=$(curl -s -X POST "${METABASE_URL}/api/session" \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"${METABASE_USER}\", \"password\": \"${METABASE_PASS}\"}" \
    | jq -r '.id')

if [ "$SESSION" == "null" ] || [ -z "$SESSION" ]; then
    echo "Failed to get session. Please complete Metabase setup manually first."
    echo "1. Go to ${METABASE_URL}"
    echo "2. Complete the initial setup wizard"
    echo "3. Add PostgreSQL database with:"
    echo "   Host: postgres"
    echo "   Port: 5432"
    echo "   Database: jaffle_shop"
    echo "   User: jaffle_user"
    echo "   Password: jaffle_pass"
    exit 1
fi

# Get database ID (assuming it's already configured)
DB_ID=$(curl -s "${METABASE_URL}/api/database" \
    -H "X-Metabase-Session: ${SESSION}" \
    | jq '.data[] | select(.name | contains("jaffle")) | .id')

if [ -z "$DB_ID" ]; then
    echo "Database not found. Please add the jaffle_shop database first."
    exit 1
fi

# Delete existing collections if any exist (handles multiple from previous runs)
curl -s "${METABASE_URL}/api/collection" \
    -H "X-Metabase-Session: ${SESSION}" \
    | jq -r ".[] | select(.name == \"${COLLECTION_NAME}\") | .id" | while read -r EXISTING_ID; do
        echo "Removing existing '${COLLECTION_NAME}' collection (id: ${EXISTING_ID})..."
        curl -s -X PUT "${METABASE_URL}/api/collection/${EXISTING_ID}" \
            -H "Content-Type: application/json" \
            -H "X-Metabase-Session: ${SESSION}" \
            -d '{"archived": true}' > /dev/null
    done

# Create a collection for our dashboards
COLLECTION_ID=$(curl -s -X POST "${METABASE_URL}/api/collection" \
    -H "Content-Type: application/json" \
    -H "X-Metabase-Session: ${SESSION}" \
    -d "{\"name\": \"${COLLECTION_NAME}\", \"color\": \"#509EE3\"}" \
    | jq '.id')

# Helper to create a chart and print a clean status line
create_chart() {
    local name="$1"
    local query="$2"
    local display="$3"
    local viz_settings="${4:-{}}"

    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${METABASE_URL}/api/card" \
        -H "Content-Type: application/json" \
        -H "X-Metabase-Session: ${SESSION}" \
        -d "{
            \"name\": \"${name}\",
            \"dataset_query\": {
                \"type\": \"native\",
                \"native\": { \"query\": \"${query}\" },
                \"database\": ${DB_ID}
            },
            \"display\": \"${display}\",
            \"visualization_settings\": ${viz_settings},
            \"collection_id\": ${COLLECTION_ID}
        }")

    if [ "$RESPONSE" -eq 200 ] || [ "$RESPONSE" -eq 202 ]; then
        echo "  Created: ${name}"
    else
        echo "  FAILED (HTTP ${RESPONSE}): ${name}"
    fi
}

echo "Creating questions..."

create_chart "Monthly Revenue Trend" \
    "SELECT order_month, net_revenue, revenue_growth_pct FROM marts_finance.fct_monthly_revenue ORDER BY order_month" \
    "line" \
    '{"graph.x_axis.title_text": "Month", "graph.y_axis.title_text": "Revenue ($)"}'

create_chart "Customer Value Segments" \
    "SELECT value_segment, COUNT(*) as customer_count, SUM(lifetime_value) as total_ltv FROM marts_core.dim_customers GROUP BY value_segment ORDER BY total_ltv DESC" \
    "pie"

create_chart "Top Products by Revenue" \
    "SELECT product_name, category, total_revenue, units_sold, avg_rating FROM marts_core.dim_products WHERE total_revenue > 0 ORDER BY total_revenue DESC LIMIT 10" \
    "bar"

create_chart "Marketing Campaign ROI" \
    "SELECT campaign_name, channel, total_spend, total_conversions, overall_ctr, estimated_roi_pct FROM marts_marketing.fct_campaign_performance ORDER BY estimated_roi_pct DESC" \
    "table"

create_chart "Daily Order Volume" \
    "SELECT order_date, total_orders, unique_customers, avg_order_value FROM marts_finance.fct_daily_revenue ORDER BY order_date" \
    "line"

echo ""
echo "Setup complete! Access your dashboards at:"
echo "${METABASE_URL}/collection/${COLLECTION_ID}"
