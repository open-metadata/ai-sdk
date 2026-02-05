# Jaffle Shop Demo Database

A comprehensive PostgreSQL + dbt + Metabase setup for demonstrating OpenMetadata features. This demo includes realistic e-commerce data with:

- **25+ customers** with PII (emails, phone numbers, addresses)
- **60+ orders** across 4 months with realistic patterns
- **20 products** across multiple categories
- **Marketing campaigns** with ad spend tracking
- **Support tickets** and product reviews
- **Data quality issues** intentionally included for DQ testing

## Quick Start

### 1. Start the Database and Metabase

```bash
cd cookbook/demo-database/docker
docker-compose up -d
```

This starts:
- **PostgreSQL** on `localhost:5432`
- **Metabase** on `localhost:3000`

### 2. Run dbt Models

```bash
cd cookbook/demo-database/dbt

# Install dbt-postgres if needed
pip install dbt-postgres

# Copy profiles to dbt directory (or ~/.dbt/)
export DBT_PROFILES_DIR=$(pwd)

# Test connection
dbt debug

# Run all models
dbt run

# Run tests
dbt test
```

### 3. Setup Metabase (Manual)

1. Open http://localhost:3000
2. Complete the setup wizard:
   - Email: `admin@jaffle.shop`
   - Password: `JaffleAdmin123!`
3. Add PostgreSQL database:
   - **Host**: `postgres` (if using Docker network) or `localhost`
   - **Port**: `5432`
   - **Database**: `jaffle_shop`
   - **Username**: `jaffle_user`
   - **Password**: `jaffle_pass`

## Database Schema

### Raw Schemas (Source Data)

| Schema | Description | Tables |
|--------|-------------|--------|
| `raw_jaffle_shop` | Core transactional data | customers, orders, order_items |
| `raw_stripe` | Payment processing | payments, refunds |
| `raw_inventory` | Product management | products, suppliers, stock_levels |
| `raw_marketing` | Campaign data | campaigns, ad_spend, user_sessions, events |
| `raw_support` | Customer service | tickets, reviews |
| `analytics` | Pre-built views | daily_revenue, customer_ltv, product_performance, campaign_roi |

### dbt Models

```
models/
├── staging/           # Clean and standardize raw data
│   ├── stg_jaffle_shop__customers
│   ├── stg_jaffle_shop__orders
│   ├── stg_jaffle_shop__order_items
│   ├── stg_stripe__payments
│   ├── stg_stripe__refunds
│   ├── stg_inventory__products
│   ├── stg_marketing__campaigns
│   ├── stg_marketing__ad_spend
│   ├── stg_support__tickets
│   └── stg_support__reviews
│
├── intermediate/      # Business logic transformations
│   ├── int_orders__enriched
│   ├── int_products__with_reviews
│   └── int_campaigns__performance
│
└── marts/             # Final analytics tables
    ├── core/
    │   ├── dim_customers      # Customer dimension with LTV
    │   ├── dim_products       # Product dimension with reviews
    │   └── fct_orders         # Order facts
    ├── finance/
    │   ├── fct_daily_revenue  # Daily revenue aggregation
    │   └── fct_monthly_revenue # Monthly with growth metrics
    └── marketing/
        ├── fct_campaign_performance # Campaign-level metrics
        └── fct_channel_performance  # Channel aggregations
```

## Sample Metabase Charts

After running dbt models, create these charts in Metabase:

### 1. Monthly Revenue Trend (Line Chart)

```sql
SELECT
    order_month,
    net_revenue,
    revenue_growth_pct
FROM marts_finance.fct_monthly_revenue
ORDER BY order_month
```

### 2. Customer Value Segments (Pie Chart)

```sql
SELECT
    value_segment,
    COUNT(*) as customer_count,
    SUM(lifetime_value) as total_ltv
FROM marts_core.dim_customers
GROUP BY value_segment
ORDER BY total_ltv DESC
```

### 3. Top Products by Revenue (Bar Chart)

```sql
SELECT
    product_name,
    category,
    total_revenue,
    units_sold,
    avg_rating
FROM marts_core.dim_products
WHERE total_revenue > 0
ORDER BY total_revenue DESC
LIMIT 10
```

### 4. Marketing Channel Performance (Table)

```sql
SELECT
    channel,
    total_campaigns,
    total_spend,
    total_conversions,
    overall_ctr,
    avg_cpa
FROM marts_marketing.fct_channel_performance
ORDER BY total_spend DESC
```

### 5. Daily Order Trends (Area Chart)

```sql
SELECT
    order_date,
    total_orders,
    unique_customers,
    net_revenue
FROM marts_finance.fct_daily_revenue
ORDER BY order_date
```

## Data Quality Scenarios

The dataset includes intentional data quality issues for testing DQ rules:

| Issue | Location | Description |
|-------|----------|-------------|
| Missing emails | `customers` id 11 | NULL email field |
| Empty strings | `customers` id 12 | Empty first_name, city, state |
| Invalid email format | `customers` id 13 | "invalid-email" instead of valid email |
| Future birth date | `customers` id 13 | DOB set to 2050 |
| Duplicate records | `customers` id 14-15 | Exact duplicate customer |
| Missing order total | `orders` id 54 | NULL order_total |
| Orphan order | `orders` id 55 | NULL customer_id |
| Zero total cancelled | `orders` id 56 | Cancelled with $0 total |
| Unverified reviews | `reviews` | Reviews without verified purchase |

## PII Classification Scenarios

Tables contain various PII types for auto-classification testing:

| Column | Table | PII Type |
|--------|-------|----------|
| `email` | customers | Email Address |
| `phone_number` | customers | Phone Number |
| `ssn_last_four` | customers | SSN (partial) |
| `date_of_birth` | customers | Date of Birth |
| `address_line_1` | customers | Street Address |
| `card_last_four` | payments | Credit Card (partial) |
| `ip_address` | payments, user_sessions | IP Address |
| `billing_email` | payments | Email Address |

## OpenMetadata Integration

### Database Users

The database includes two pre-configured users:

| User | Password | Purpose |
|------|----------|---------|
| `jaffle_user` | `jaffle_pass` | Full read/write access for dbt and applications |
| `openmetadata_user` | `openmetadata_pass` | Read-only access for metadata ingestion (recommended) |

Both users have:
- `pg_read_all_stats` role for `pg_stat_statements` access (query lineage)
- SELECT on `pg_catalog` and `information_schema` (metadata extraction)
- Access to all schemas

### Ingesting Metadata

#### Step 1: Create PostgreSQL Service

In OpenMetadata UI, go to **Settings > Services > Databases > Add New Service**:

```yaml
Service Type: Postgres
Service Name: jaffle-shop-postgres

Connection Details:
  Host: localhost          # Use 'host.docker.internal' if OM runs in Docker
  Port: 5432
  Database: jaffle_shop
  Username: openmetadata_user
  Password: openmetadata_pass

  # For query lineage via pg_stat_statements
  SSL Mode: disable        # For local dev; use 'require' in production
```

#### Step 2: Configure Ingestion

Create a metadata ingestion workflow:

```yaml
Source:
  Include Views: true
  Include Tables: true
  Schema Filter Pattern:
    includes:
      - raw_jaffle_shop
      - raw_stripe
      - raw_inventory
      - raw_marketing
      - raw_support
      - analytics
      - staging
      - intermediate
      - marts_core
      - marts_finance
      - marts_marketing

# Enable lineage from pg_stat_statements
Query Log Lineage:
  Enabled: true
```

#### Step 3: Run Ingestion

After running the ingestion, you should see:
- **6 raw schemas** with source tables
- **Analytics views** with computed metrics
- **dbt schemas** (staging, intermediate, marts_*)
- **Automatic lineage** from query logs

#### Step 4: Verify Lineage

Run some queries to populate `pg_stat_statements`:

```sql
-- Connect as jaffle_user and run analytics queries
SELECT * FROM marts_finance.fct_monthly_revenue;
SELECT * FROM marts_core.dim_customers WHERE value_segment = 'High Value';
```

Then re-run lineage ingestion to capture query-based lineage.

### Testing Cookbook Features

| Cookbook | Demo Scenario |
|----------|---------------|
| DQ Failure Notifications | Run DQ tests on `dim_customers`, trigger Slack alerts on failures |
| dbt PR Review | Modify `fct_daily_revenue` model, review downstream impact |
| PII Classification | Run auto-classification on `raw_jaffle_shop.customers` |
| Data Profiling | Profile `fct_orders` to understand data distributions |
| Lineage Analysis | Trace lineage from `raw_stripe.payments` to `fct_monthly_revenue` |
| MCP Integration | Query metadata via Claude/LLM for impact analysis |

## Cleanup

```bash
# Stop and remove containers
cd docker
docker-compose down

# Remove volumes (deletes all data)
docker-compose down -v
```

## Connection Details

| Service | Host | Port | User | Password | Purpose |
|---------|------|------|------|----------|---------|
| PostgreSQL | localhost | 5432 | `jaffle_user` | `jaffle_pass` | dbt, applications |
| PostgreSQL | localhost | 5432 | `openmetadata_user` | `openmetadata_pass` | OpenMetadata ingestion |
| Metabase | localhost | 3000 | `admin@jaffle.shop` | `JaffleAdmin123!` | BI dashboards |

## File Structure

```
demo-database/
├── docker/
│   ├── docker-compose.yml    # PostgreSQL + Metabase services
│   ├── Dockerfile            # PostgreSQL with init script
│   └── init.sql              # Database schema and seed data
├── dbt/
│   ├── dbt_project.yml       # dbt configuration
│   ├── profiles.yml          # Connection profiles
│   └── models/
│       ├── staging/          # Source data cleaning
│       ├── intermediate/     # Business transformations
│       └── marts/            # Analytics tables
├── scripts/
│   └── setup_metabase.sh     # Automated Metabase setup (optional)
└── README.md
```
