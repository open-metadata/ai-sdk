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
cd cookbook/resources/demo-database/docker
docker-compose up -d
```

This starts:
- **PostgreSQL** on `localhost:5433`
- **Metabase** on `localhost:3000`

### 2. Run dbt Models

```bash
cd cookbook/resources/demo-database/dbt

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

### 3. Setup Metabase

1. Open http://localhost:3000
2. Complete the setup wizard:
   - Email: `admin@jaffle.shop`
   - Password: `JaffleAdmin123!`
3. Add PostgreSQL database during the wizard:
   - **Name**: `jaffle_shop`
   - **Host**: `postgres`
   - **Port**: `5432`
   - **Database**: `jaffle_shop`
   - **Username**: `jaffle_user`
   - **Password**: `jaffle_pass`
4. Run the setup script to create pre-built charts and dashboards:

```bash
cd cookbook/resources/demo-database
./scripts/setup_metabase.sh
```

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

## Metabase Charts

The setup script (`scripts/setup_metabase.sh`) creates the following charts in a "Jaffle Shop Analytics" collection:

1. **Monthly Revenue Trend** (Line) — `marts_finance.fct_monthly_revenue`
2. **Customer Value Segments** (Pie) — `marts_core.dim_customers`
3. **Top Products by Revenue** (Bar) — `marts_core.dim_products`
4. **Marketing Campaign ROI** (Table) — `marts_marketing.fct_campaign_performance`
5. **Daily Order Volume** (Line) — `marts_finance.fct_daily_revenue`

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

A single script runs all ingestion workflows (PostgreSQL metadata, dbt, lineage, and Metabase):

```bash
# Install the ingestion package with required plugins
pip install "openmetadata-ingestion[postgres,dbt]"

# Set your OpenMetadata credentials
export AI_SDK_HOST=https://your-instance.getcollate.io
export AI_SDK_TOKEN=your-jwt-token

# Run all ingestion workflows
cd cookbook/resources/demo-database
./scripts/ingest_metadata.sh
```

This runs 4 workflows in order:

1. **PostgreSQL Metadata** — tables, views, and schemas from all raw/staging/marts schemas
2. **dbt Metadata** — model descriptions, tags, and lineage from dbt artifacts
3. **PostgreSQL Lineage** — query-based lineage from `pg_stat_statements`
4. **Metabase Dashboards** — charts and dashboard metadata with lineage to PostgreSQL tables

The YAML configs are in `ingestion/` and can be customized individually:

| File | Workflow |
|------|----------|
| `ingestion/postgres.yaml` | Database metadata ingestion |
| `ingestion/dbt.yaml` | dbt model metadata |
| `ingestion/postgres_lineage.yaml` | Query-based lineage |
| `ingestion/metabase.yaml` | Dashboard metadata |

### Seeding Glossaries, Metrics, Users, Domains & Ownership

After ingestion, seed business metadata:

```bash
cd cookbook/resources/demo-database

# Glossaries and metrics
python scripts/create_glossaries_and_metrics.py

# Users, domains, and table ownership
python scripts/create_owners_and_domains.py
```

The ownership script creates 5 users, 4 domains, and assigns every table to an owner and domain:

| Domain | Schemas | Owner |
|--------|---------|-------|
| Finance | `marts_finance`, `raw_stripe` | Bob Smith (Finance Analyst) |
| Marketing | `marts_marketing`, `raw_marketing` | Carol Williams (Marketing Analyst) |
| Sales | `marts_core`, `raw_jaffle_shop`, `raw_inventory`, `raw_support` | Eve Davis (Product Analyst) / Dave Brown (raw) |
| Data Engineering | `staging`, `intermediate` | Alice Johnson (DE Lead) |

After ingestion, you should see:
- **6 raw schemas** with source tables
- **Analytics views** with computed metrics
- **dbt schemas** (staging, intermediate, marts_*)
- **Automatic lineage** from dbt models and query logs
- **Metabase dashboards** linked to PostgreSQL tables

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
| PostgreSQL | localhost | 5433 | `jaffle_user` | `jaffle_pass` | dbt, applications |
| PostgreSQL | localhost | 5433 | `openmetadata_user` | `openmetadata_pass` | OpenMetadata ingestion |
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
├── ingestion/
│   ├── postgres.yaml           # PostgreSQL metadata ingestion config
│   ├── postgres_lineage.yaml   # PostgreSQL lineage ingestion config
│   ├── dbt.yaml                # dbt metadata ingestion config
│   └── metabase.yaml           # Metabase dashboard ingestion config
├── scripts/
│   ├── setup_metabase.sh                  # Automated Metabase chart setup
│   ├── ingest_metadata.sh                 # Run all OpenMetadata ingestion workflows
│   ├── create_glossaries_and_metrics.py   # Seed glossaries, terms, and metrics
│   └── create_owners_and_domains.py       # Seed users, domains, and table ownership
└── README.md
```
