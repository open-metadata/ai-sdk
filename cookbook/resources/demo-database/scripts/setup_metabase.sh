#!/bin/bash
# Setup Metabase with pre-configured questions and dashboards
# Run this after Metabase is up and the database connection is configured

set -e

METABASE_URL="${METABASE_URL:-http://localhost:3000}"
METABASE_USER="${METABASE_USER:-admin@jaffle.shop}"
METABASE_PASS="${METABASE_PASS:-JaffleAdmin123!}"

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

echo "Session token: ${SESSION}"

# Get database ID (assuming it's already configured)
DB_ID=$(curl -s "${METABASE_URL}/api/database" \
    -H "X-Metabase-Session: ${SESSION}" \
    | jq '.data[] | select(.name | contains("jaffle")) | .id')

if [ -z "$DB_ID" ]; then
    echo "Database not found. Please add the jaffle_shop database first."
    exit 1
fi

echo "Database ID: ${DB_ID}"

# Create a collection for our dashboards
echo "Creating Jaffle Shop collection..."
COLLECTION_ID=$(curl -s -X POST "${METABASE_URL}/api/collection" \
    -H "Content-Type: application/json" \
    -H "X-Metabase-Session: ${SESSION}" \
    -d '{"name": "Jaffle Shop Analytics", "color": "#509EE3"}' \
    | jq '.id')

echo "Collection ID: ${COLLECTION_ID}"

# Create questions
echo "Creating questions..."

# Question 1: Monthly Revenue Trend
curl -s -X POST "${METABASE_URL}/api/card" \
    -H "Content-Type: application/json" \
    -H "X-Metabase-Session: ${SESSION}" \
    -d "{
        \"name\": \"Monthly Revenue Trend\",
        \"dataset_query\": {
            \"type\": \"native\",
            \"native\": {
                \"query\": \"SELECT order_month, net_revenue, revenue_growth_pct FROM marts_finance.fct_monthly_revenue ORDER BY order_month\"
            },
            \"database\": ${DB_ID}
        },
        \"display\": \"line\",
        \"visualization_settings\": {
            \"graph.x_axis.title_text\": \"Month\",
            \"graph.y_axis.title_text\": \"Revenue ($)\"
        },
        \"collection_id\": ${COLLECTION_ID}
    }"

# Question 2: Customer Segments
curl -s -X POST "${METABASE_URL}/api/card" \
    -H "Content-Type: application/json" \
    -H "X-Metabase-Session: ${SESSION}" \
    -d "{
        \"name\": \"Customer Value Segments\",
        \"dataset_query\": {
            \"type\": \"native\",
            \"native\": {
                \"query\": \"SELECT value_segment, COUNT(*) as customer_count, SUM(lifetime_value) as total_ltv FROM marts_core.dim_customers GROUP BY value_segment ORDER BY total_ltv DESC\"
            },
            \"database\": ${DB_ID}
        },
        \"display\": \"pie\",
        \"collection_id\": ${COLLECTION_ID}
    }"

# Question 3: Top Products
curl -s -X POST "${METABASE_URL}/api/card" \
    -H "Content-Type: application/json" \
    -H "X-Metabase-Session: ${SESSION}" \
    -d "{
        \"name\": \"Top Products by Revenue\",
        \"dataset_query\": {
            \"type\": \"native\",
            \"native\": {
                \"query\": \"SELECT product_name, category, total_revenue, units_sold, avg_rating FROM marts_core.dim_products WHERE total_revenue > 0 ORDER BY total_revenue DESC LIMIT 10\"
            },
            \"database\": ${DB_ID}
        },
        \"display\": \"bar\",
        \"collection_id\": ${COLLECTION_ID}
    }"

# Question 4: Campaign ROI
curl -s -X POST "${METABASE_URL}/api/card" \
    -H "Content-Type: application/json" \
    -H "X-Metabase-Session: ${SESSION}" \
    -d "{
        \"name\": \"Marketing Campaign ROI\",
        \"dataset_query\": {
            \"type\": \"native\",
            \"native\": {
                \"query\": \"SELECT campaign_name, channel, total_spend, total_conversions, overall_ctr, estimated_roi_pct FROM marts_marketing.fct_campaign_performance ORDER BY estimated_roi_pct DESC\"
            },
            \"database\": ${DB_ID}
        },
        \"display\": \"table\",
        \"collection_id\": ${COLLECTION_ID}
    }"

# Question 5: Daily Orders
curl -s -X POST "${METABASE_URL}/api/card" \
    -H "Content-Type: application/json" \
    -H "X-Metabase-Session: ${SESSION}" \
    -d "{
        \"name\": \"Daily Order Volume\",
        \"dataset_query\": {
            \"type\": \"native\",
            \"native\": {
                \"query\": \"SELECT order_date, total_orders, unique_customers, avg_order_value FROM marts_finance.fct_daily_revenue ORDER BY order_date\"
            },
            \"database\": ${DB_ID}
        },
        \"display\": \"line\",
        \"collection_id\": ${COLLECTION_ID}
    }"

echo ""
echo "Setup complete! Access your dashboards at:"
echo "${METABASE_URL}/collection/${COLLECTION_ID}"
