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

## Running against Starburst (Iceberg)

The same dbt project can target a remote Starburst instance with an Iceberg catalog.
The raw Jaffle Shop data ships as dbt seeds (CSVs in `dbt/seeds/`) and is loaded
on demand.

### Prerequisites

- A Starburst Galaxy account (or self-hosted Starburst Enterprise) with an Iceberg catalog configured
- An object-storage bucket for the Iceberg data (S3 / GCS / ADLS) — Galaxy is compute-only, you bring storage
- `make install-dbt-starburst` (installs `dbt-trino>=1.7,<2.0`)

### Galaxy quick start

#### 1. Object storage (S3 example)

Galaxy supports a fixed list of AWS regions — `eu-west-3` (Paris) is **not** one of them. Pick a Galaxy-supported region close to you (`eu-west-1` Ireland is closest to Paris):

```bash
BUCKET=<globally-unique-name>
REGION=eu-west-1

aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" \
  --create-bucket-configuration LocationConstraint="$REGION"
```

#### 2. IAM user with long-lived keys

Galaxy needs **permanent access keys**, not STS assume-role / SSO credentials. Create a dedicated IAM user scoped to the bucket:

```bash
cat > /tmp/galaxy-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": ["s3:ListBucket","s3:GetBucketLocation"], "Resource": "arn:aws:s3:::${BUCKET}"},
    {"Effect": "Allow", "Action": ["s3:GetObject","s3:PutObject","s3:DeleteObject"], "Resource": "arn:aws:s3:::${BUCKET}/*"}
  ]
}
EOF

aws iam create-user --user-name galaxy-${BUCKET}
aws iam put-user-policy --user-name galaxy-${BUCKET} \
  --policy-name ${BUCKET}-bucket --policy-document file:///tmp/galaxy-policy.json
aws iam create-access-key --user-name galaxy-${BUCKET}
# capture AccessKeyId + SecretAccessKey — the secret is shown only once
```

#### 3. Galaxy catalog + cluster

In Galaxy UI:

- **Catalogs → Create catalog → Amazon S3 / Iceberg.** Set the catalog name to `iceberg`, bucket to your bucket, region to your bucket's region, and paste the IAM access key/secret. Use the Galaxy-managed metastore (default).
- **Clusters → Create cluster.** Pick the **Free** size, the same region as the bucket, auto-suspend at 1 minute, and attach the `iceberg` catalog.

#### 4. Find the connection details

In Galaxy → **Clusters → \<your-cluster\> → Connect with → Trino CLI**. Note two values exactly as shown:

- **Host** — Galaxy's pattern is `<account>-<cluster>.trino.galaxy.starburst.io`. Example: `collatetest-free-cluster-ireland.trino.galaxy.starburst.io`. **Not** `<cluster>.<account>.galaxy.starburst.io`, and **not** the Galaxy console URL `<account>.galaxy.starburst.io` — that one returns HTTP 405 to Trino traffic.
- **`--user` value** — Galaxy puts the role into the username, e.g. `pmbrull@getcollate.io/accountadmin`. Copy it verbatim.

#### 5. Personal Access Token (the password)

Galaxy's "API tokens" come in two flavors. They are **not JWTs** — they're opaque secrets used as the password over HTTP Basic auth (LDAP method in dbt-trino).

- **Personal user PAT:** Galaxy → click your avatar → *Personal access tokens* → Create. Username will be `<email>/<role>`. This is the simplest path for development.
- **Service-account token:** Galaxy → Admin → Service accounts → Create. Username will be the random ID Galaxy assigns, e.g. `i94xdO6k7bNPWloY`. Better for CI / production but the SA must be granted the role and cluster privileges separately.

The username and password must belong to the **same identity**. A personal-user PAT will not authenticate as a service account, and vice versa — you'll see HTTP 401 (`access_denied`) or 404 (`User not found`).

#### 6. Set env vars and run

```bash
export STARBURST_METHOD=ldap                                # default; explicit for clarity
export STARBURST_HOST=collatetest-free-cluster-ireland.trino.galaxy.starburst.io
export STARBURST_USER='pmbrull@getcollate.io/accountadmin' # quote because of the /
export STARBURST_CATALOG=iceberg

# Keep the PAT out of shell history:
read -rs STARBURST_PASSWORD && export STARBURST_PASSWORD

cd cookbook/resources/demo-database/dbt
DBT_PROFILES_DIR=$(pwd) dbt debug --target starburst
# expect: All checks passed!
```

Then load and build:

```bash
make demo-dbt-starburst-seed   # load CSVs into iceberg.raw_* schemas
make demo-dbt-starburst        # build staging -> intermediate -> marts
```

### Generating the seed CSVs (one-time per data version)

The CSVs are generated from the local PostgreSQL demo (so the same row data
loaded by `init.sql` is what lands in Starburst):

```bash
make demo-database          # start PG
make demo-export-seeds      # PG raw_* tables -> dbt/seeds/raw_*/*.csv
git add cookbook/resources/demo-database/dbt/seeds && git commit
```

CSVs are versioned in git — re-running `demo-export-seeds` is only needed when
`init.sql` changes.

### Authenticating with a real JWT (alternative)

If your Starburst is wired to an external IdP (Okta, Auth0, Azure AD) that issues real JWTs (token starts with `eyJ...` and has three dot-separated segments), use JWT auth instead:

```bash
export STARBURST_METHOD=jwt
export STARBURST_USER=your.user@org           # cosmetic — identity comes from the token's `sub`
export STARBURST_JWT_TOKEN=eyJhbGciOi...
unset STARBURST_PASSWORD
```

Galaxy's built-in API tokens are **not** JWTs — don't use this path with them.

### Troubleshooting

| Symptom | Cause |
|---|---|
| `error 405` from `/v1/statement` | `STARBURST_HOST` points at the Galaxy console (`<account>.galaxy.starburst.io`) instead of the cluster (`<account>-<cluster>.trino.galaxy.starburst.io`). |
| TLS `SSLV3_ALERT_HANDSHAKE_FAILURE` | Same — wrong host. The wildcard cert doesn't cover the made-up name. macOS LibreSSL can also produce this for unrelated reasons; if `dbt debug` succeeds, ignore curl-side failures. |
| `error 401: access_denied` | Username and password belong to different identities (e.g., personal email + SA token), or the role lacks `Use cluster` / `Use catalog` privileges. |
| `error 404: User not found` | Username format wrong. Copy the exact `--user` from Galaxy's *Connect with* tab. |
| `Incorrect S3 access credentials` (Galaxy catalog wizard) | IAM keys with whitespace from the paste, region mismatch between the catalog form and the actual bucket location, or keys still propagating (~30–60s). |
| `Unsupported aws regions: [eu-west-3]` | Galaxy doesn't run in that region. Recreate the bucket in a supported region (`eu-west-1` is the closest to Paris). |

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
