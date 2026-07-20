# Banking Redshift Demo

A comprehensive banking-data cookbook resource for OpenMetadata demos that targets a real **S3 → Redshift → Apache Superset → OpenMetadata** lineage chain. It ships everything needed to stand up an end-to-end banking analytics stack and exercise the full breadth of OpenMetadata's catalog, governance, lineage, DQ, PII, and AI features.

Highlights:

- **8 source schemas, 38 raw tables, 5,000 customers, 250k transactions, 400k login attempts** across a 12-month time range (~220 MB of CSV data, deterministic seed=42)
- **dbt project with ~70 models** (staging, intermediate, marts: core / finance / risk / wealth / marketing) with PII tagging, IFRS 9 staging, and ECL calculations
- **Realistic distributions**: hour-of-day + day-of-week + holiday seasonality on transactions, ISO 13616 IBAN with mod-97 checksum, BIN-correct masked PANs, MCC catalog including fraud-typology codes
- **6 OpenMetadata glossaries with multi-paragraph term definitions, 30+ business metrics linked to terms, 6 domains (Retail / Lending / Wealth / Compliance / Finance / Digital), Teams + Personas + domain experts, 9 PII tags applied to columns**
- **4 Superset dashboards** (Executive/CFO, Risk & Compliance, Customer Ops, Digital Engagement) with ~20 charts
- **Engineered demo scenarios**: 8 intentional DQ defects, fraud burst (10 customers × 80 card auths in 24h), chargeback storm (2 merchants × 40 disputes), IFRS9 Stage 1/2/3 loan distribution

## Architecture

```
┌──────────────────┐
│ generate_seed_   │
│ data.py          │  deterministic, seed=42
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ dbt/seeds/raw_*  │  38 CSVs (~220 MB)
└────────┬─────────┘
         │ upload_to_s3.sh
         ▼
┌──────────────────┐
│ S3 bucket        │  s3://<bucket>/raw/<schema>/<table>/<table>.csv
└────────┬─────────┘
         │ load_to_redshift.sh (COPY)
         ▼
┌──────────────────┐
│ Redshift raw_*   │  8 schemas, 38 tables
└────────┬─────────┘
         │ dbt run / test
         ▼
┌──────────────────┐
│ staging → int    │
│ → marts_*        │  ~70 dbt models
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Superset         │  4 dashboards, ~20 charts
└──────────────────┘

OpenMetadata ingests: S3 + Redshift + Redshift query lineage + dbt + Superset
```

## Prerequisites

- **AWS CLI** configured (`aws configure`) with access to the target account
- **Redshift cluster** (RA3 recommended) reachable from your workstation
- **IAM role** attached to the Redshift cluster with `s3:GetObject` / `s3:ListBucket` on the demo bucket (used by `COPY`)
- **Docker** (for the bundled Superset compose stack)
- **Python 3.10+** with `pip`
- **dbt-redshift** (`pip install dbt-redshift`)
- **OpenMetadata** host + JWT (for ingestion + glossary/domain seeding)

Install all Python dependencies in one shot:

```bash
make install-deps
```

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `AWS_REGION` | AWS region for the S3 bucket and Redshift cluster | — |
| `BANKING_S3_BUCKET` | S3 bucket that hosts the raw CSVs | — |
| `BANKING_S3_PREFIX` | Key prefix under the bucket | `raw` |
| `REDSHIFT_HOST` | Redshift cluster endpoint | — |
| `REDSHIFT_PORT` | Redshift port | `5439` |
| `REDSHIFT_DATABASE` | Target database name | — |
| `REDSHIFT_USER` | Redshift user with create/copy privileges | — |
| `REDSHIFT_PASSWORD` | Redshift password | — |
| `REDSHIFT_IAM_ROLE` | ARN of the IAM role used by `COPY` from S3 | — |
| `AI_SDK_HOST` | OpenMetadata host (e.g. `https://your.getcollate.io`) | — |
| `AI_SDK_TOKEN` | OpenMetadata JWT | — |
| `SUPERSET_ADMIN_EMAIL` | Bootstrap admin email for Superset | `admin@bank.demo` |
| `SUPERSET_ADMIN_PASSWORD` | Bootstrap admin password for Superset | `BankAdmin123!` |

Put these in a `.envrc` (direnv) or export them in your shell before running any target.

## Quick Start

> **Data already loaded and just need to (re)ingest into an OpenMetadata instance?**
> See [`RUNBOOK.md`](RUNBOOK.md) — every env var + command in order, plus the
> common ingestion traps and their fixes.

All `make` targets live in this directory's own `Makefile` (not the root project Makefile). `cd` here first, then one command does everything end-to-end:

```bash
cd cookbook/resources/banking-redshift
make all
```

That target walks through the steps below in order:

1. `generate-seeds` — generate the 38 raw CSVs from the deterministic generator
2. `upload-s3` — upload the CSVs to `s3://$BANKING_S3_BUCKET/$BANKING_S3_PREFIX/`
3. `init-redshift` — create `raw_*` schemas and tables via `sql/redshift_init.sql`
4. `load` — `COPY` each CSV into its Redshift table
5. `dbt` — `dbt deps && dbt run && dbt test`
6. `superset-up` — start the Superset docker-compose stack
7. `superset-setup` — provision database connection, datasets, charts, dashboards
8. `ingest-metadata` — run all OpenMetadata ingestion workflows
9. `glossaries` — seed glossaries, terms, metrics, owners, domains
10. `context-center` — seed Context Center folders, files, pages, memories

## Step-by-step Setup

### 1. Generate seed data

```bash
make generate-seeds
```

Runs `scripts/generate_seed_data.py` (seed=42, fully deterministic). Produces 38 CSVs under `dbt/seeds/raw_*/` totaling ~220 MB. Re-running is idempotent.

### 2. Upload to S3

```bash
export BANKING_S3_BUCKET=my-banking-demo-bucket
export AWS_REGION=us-east-1
make upload-s3
```

Uploads to `s3://$BANKING_S3_BUCKET/$BANKING_S3_PREFIX/<schema>/<table>/<table>.csv`.

### 3. Bootstrap Redshift

```bash
make init-redshift
```

Runs `sql/redshift_init.sql` against the cluster. Creates 8 `raw_*` schemas and 38 empty tables with the correct DDL (distkeys, sortkeys, types).

### 4. COPY data to Redshift

```bash
make load
```

Issues a `TRUNCATE` then `COPY` per table from S3 using `REDSHIFT_IAM_ROLE`. Re-running is idempotent — never duplicates rows.

### 5. Run dbt

```bash
make dbt
```

Equivalent to `dbt deps && dbt run && dbt test` in `dbt/`. Builds ~70 staging / intermediate / marts models and runs all data tests (including the ones designed to catch the seeded DQ defects).

For environments where `COPY` is not desired you can use the seed fallback:

```bash
make dbt-seed
```

### 6. Start Superset

```bash
make superset-up
```

Starts the Superset docker-compose stack at <http://localhost:8088>. Login with `$SUPERSET_ADMIN_EMAIL` / `$SUPERSET_ADMIN_PASSWORD`.

### 7. Provision Superset dashboards

```bash
make superset-setup
```

Runs `scripts/setup_superset.sh` which registers the Redshift database, imports datasets, and builds the 4 dashboards with ~20 charts.

### 8. Ingest metadata into OpenMetadata

```bash
make ingest-metadata
```

Runs six workflows in order:

1. **S3 metadata** — container/object metadata for the raw CSVs
2. **Redshift metadata** — schemas, tables, columns (with `markDeletedTables` + `includeOwners`)
3. **Redshift profiler + PII** — column profiles, sample data, auto-PII classification (`processPiiSensitive: true`)
4. **Redshift query lineage** — STL_QUERY-based lineage from raw → marts
5. **dbt metadata** — model descriptions, tags, owner hints, model lineage (catalog + run_results required)
6. **Superset dashboards** — charts, dashboards, dataset lineage to Redshift

### 9. Seed glossaries, metrics, owners, domains

```bash
make glossaries
```

Seeds 6 glossaries (~110 terms incl. IFRS 9 staging, Basel III, GDPR/CCPA), 35+ business metrics with owners and glossary linkage, 6 users, 6 domains (Retail / Lending / Wealth / Compliance / Finance / Digital), 6 Teams, 6 Personas, and PII Classification tags applied to columns.

### 10. Seed the Context Center

```bash
make context-center
```

Populates the **Context Center** (`/context-center/dashboard`) with a realistic
banking-themed knowledge surface:

- **~11 folders** in a hierarchy: Compliance → KYC/AML; Risk Management →
  Credit Risk/Fraud; Customer Operations; Finance & Reporting → IFRS 9/Basel
  III; Data Engineering.
- **~15 files** uploaded as markdown (KYC Policy, AML Procedures, Fraud
  Incident Response, IFRS 9 Staging Methodology, ECL Calculation Guide,
  Basel III Capital Reporting, dbt Model Conventions, PII Classification
  Guide, …). Multipart upload to `/v1/contextCenter/drive/files/upload` with a
  graceful fallback to metadata-only file entries when object storage is not
  configured (pass `--no-upload` to skip uploads outright).
- **~12 pages** — articles (Customer-360 data model, IFRS 9 staging logic,
  fraud burst playbook, PII tag taxonomy, dbt model layers, DQ defects
  catalogue, …) and quick-links to the Superset dashboards and external
  regulator portals (FinCEN, BIS).
- **~22 memories** covering every memory type (`Faq`, `Runbook`, `UseCase`,
  `Note`, `Preference`) — examples: "Where are masked PANs?", "Respond to a
  fraud burst", "Compute customer churn", "Always exclude test customers from
  KPIs". Memories that target a specific Redshift table attach to it via
  `primaryEntity` once the table is ingested; the script logs a warning and
  still creates the memory if the table is not yet in the catalog.

The script is idempotent: any entity that already exists (matched by name /
FQN) is skipped. Pass `--force` to delete and recreate. Pass `--dry-run` to
preview without writes.

Memories carry per-entity owners spread across four users (`alice`,
`bob`, `carol`, `dave`) so the Context Center view shows a mix of
authors. By default each memory is POSTed with the `X-Impersonate-User`
header set to the owner, so the **author** (i.e. `updatedBy` / "Created by"
in the UI) also matches the owner — not just the ownership chip.
Impersonation requires a **bot JWT** on the server side (OpenMetadata's
`JwtFilter` rejects impersonation from non-bot tokens with a 403). On a 401
or 403 the script auto-falls-back to no impersonation and continues. Pass
`--no-impersonate` to skip the header outright; owners that can't be
resolved on the target instance are logged as a warning and the memory is
still created.

To wipe the Context Center before a fresh demo:

```bash
make context-center-clean           # delete folders, files, pages and memories
make context-center-clean-memories  # delete memories only
make context-center-reset           # clean then re-seed
```

Each destructive target prompts for a `yes` confirmation.

### 11. Open dashboards + run AI demos

Open <http://localhost:8088> for the Superset dashboards and <https://your-instance.getcollate.io> for OpenMetadata. See [Cookbook Demo Scenarios](#cookbook-demo-scenarios) below.

## Schema Overview

### `raw_core_banking`

| Table | Rows | Description |
|-------|-----:|-------------|
| `customers` | 5,001 | Retail + business customer master with SSN/tax_id, segment, risk band |
| `branches` | 75 | Physical branch locations with manager assignment |
| `employees` | 400 | Branch and HQ staff with manager hierarchy |
| `accounts` | 8,500 | Deposit + credit accounts (checking, savings, MMA, CD, HELOC, auto, mortgage) |
| `account_holders` | 9,334 | M:N join between accounts and customers (joint accounts) |
| `customer_addresses` | 6,480 | Mailing / residential / work addresses (PII) |
| `customer_contacts` | 11,518 | Phones, emails, secondary contacts |
| `account_types` | 8 | Account type reference lookup |

### `raw_transactions`

| Table | Rows | Description |
|-------|-----:|-------------|
| `transactions` | 250,000 | Core ledger with hour/dow/seasonal time patterns + category + channel |
| `atm_withdrawals` | 25,000 | ATM-specific transactions with terminal, network (STAR/PLUS/...), and `parent_transaction_id` lineage |
| `wire_transfers` | 5,000 | Domestic + international wires with valid ISO 13616 IBAN + BIC, `parent_transaction_id` |
| `ach_transfers` | 35,000 | ACH transfers with SEC codes + NACHA return reason codes, `parent_transaction_id` |
| `transaction_categories` | 12 | Category lookup (POS, fees, payroll, etc.) |

### `raw_cards`

| Table | Rows | Description |
|-------|-----:|-------------|
| `cards` | 6,500 | Debit / credit cards with BIN-correct masked PAN per product |
| `card_authorizations` | 120,800 | Auth attempts with merchant + IP + decline reasons; includes engineered fraud burst |
| `card_disputes` | 920 | Cardholder disputes (~0.7% of auths) plus engineered chargeback storm |
| `card_products` | 6 | Card product catalog (Visa Classic, Platinum, Amex, Discover) |
| `merchants` | 600 | Merchant master with 40+ MCC codes incl. fraud-typology (6011, 6051, 4829, 7995) |

### `raw_lending`

| Table | Rows | Description |
|-------|-----:|-------------|
| `loans` | 3,000 | Mortgages, auto, personal, HELOC, business — **with IFRS 9 stage 1/2/3, PD, LGD, EAD, ECL, days_past_due** |
| `loan_applications` | 6,500 | Application pipeline with FICO ↔ DTI ↔ approval correlation |
| `loan_payments` | 11,344 | Scheduled + actual payments with principal/interest split |
| `collateral` | 2,003 | Collateral records linked to secured loans |
| `loan_products` | 6 | Loan product catalog with rate sheets |

### `raw_risk`

| Table | Rows | Description |
|-------|-----:|-------------|
| `credit_scores` | 12,000 | FICO + VANTAGE bureau pulls with refresh history |
| `kyc_checks` | 6,500 | KYC verification (initial / refresh / EDD) with documents + employee |
| `aml_alerts` | 2,000 | Transaction monitoring alerts with **templated narratives by alert type**, weekend-skewed structuring patterns |
| `sanctions_screening` | 400 | OFAC / EU / UN / UK_HMT match results |
| `suspicious_activity_reports` | 150 | SAR filings with FinCEN references |

### `raw_wealth`

| Table | Rows | Description |
|-------|-----:|-------------|
| `securities` | 150 | Tradable instruments (ISIN, asset class, exchange) |
| `investment_accounts` | 200 | Brokerage / IRA / 401k / 529 accounts |
| `holdings` | 6,000 | Position snapshots by account + security with current market value |
| `trades` | 25,000 | Trade tickets with execution detail and venue |

### `raw_digital`

| Table | Rows | Description |
|-------|-----:|-------------|
| `web_sessions` | 150,000 | Online banking session metadata (device, OS, IP, referrer) |
| `mobile_app_events` | 250,000 | Mobile app events with geo coordinates; `session_id` constrained to same-customer web sessions |
| `login_attempts` | 400,000 | Auth attempts with MFA method, device fingerprint, IP |

### `raw_marketing`

| Table | Rows | Description |
|-------|-----:|-------------|
| `campaigns` | 40 | Marketing campaign master with channel + objective + budget |
| `customer_segments` | 8 | Lifecycle / value segment definitions |
| `customer_interactions` | 40,000 | Cross-channel touchpoints (branch, phone, chat, email, video) |

## dbt Model Overview

```
dbt/models/
├── staging/                                # 38 stg_<schema>__<table> models (one per raw)
│   ├── stg_core_banking__customers.sql
│   ├── stg_core_banking__branches.sql
│   ├── ...                                 # one per raw table
│   └── stg_marketing__customer_interactions.sql
│
├── intermediate/
│   ├── int_customers__360.sql              # Customer 360 join
│   ├── int_accounts__enriched.sql
│   ├── int_branches__performance.sql
│   ├── int_employees__org.sql
│   ├── int_transactions__categorized.sql
│   ├── int_loans__delinquency.sql
│   ├── int_loans__schedule.sql
│   ├── int_aml__alert_context.sql
│   ├── int_kyc__customer_status.sql
│   ├── int_cards__activity.sql
│   ├── int_digital__engagement.sql
│   └── int_holdings__valued.sql
│
└── marts/
    ├── core/
    │   ├── dim_customers.sql
    │   ├── dim_accounts.sql
    │   ├── dim_branches.sql
    │   ├── dim_employees.sql
    │   ├── dim_cards.sql
    │   └── fct_transactions.sql
    ├── finance/
    │   ├── fct_daily_balances.sql
    │   ├── fct_monthly_pnl.sql
    │   ├── fct_nim.sql                     # Net Interest Margin
    │   ├── fct_fee_revenue.sql
    │   └── fct_branch_performance.sql
    ├── risk/
    │   ├── fct_delinquency.sql
    │   ├── fct_loan_loss_provision.sql     # ECL / IFRS9-style
    │   ├── fct_aml_pipeline.sql
    │   └── dim_credit_risk.sql
    ├── wealth/
    │   ├── fct_aum.sql                     # Assets Under Management
    │   ├── fct_trades.sql
    │   └── dim_holdings.sql
    └── marketing/
        ├── fct_campaign_attribution.sql
        └── fct_customer_engagement.sql
```

## Intentional DQ Defects

Seeded by `generate_seed_data.py` (seed=42) so the dbt tests and OpenMetadata profilers have something to flag. Indices are stable across runs.

| Defect | Location | Expected test / signal |
|--------|----------|------------------------|
| NULL `ssn` on a retail customer | `customers` rows 11, 26 (`CUST_000011`, `CUST_000026`) | `not_null` on `customers.ssn` (where customer_type='retail') fails |
| Invalid email format | `customers` row 12 (`CUST_000012`, email = `not-an-email`) | custom regex test `assert_customers_email_valid` fails |
| Future-dated DOB | `customers` row 13 (`CUST_000013`, DOB `2050-01-01`) | custom test `assert_customers_dob_not_future` fails |
| Duplicate name + DOB pair | `CUST_005001` duplicates name + DOB of `CUST_000014` | `dbt_utils.unique_combination_of_columns(first_name, last_name, date_of_birth)` fails |
| Empty city | `customer_addresses` ~row 22 | custom test `assert_addresses_city_not_empty` fails |
| Orphan FK on transactions | 30 `transactions` rows reference `account_id = 'ACC_99999999'` | `relationships` test on `transactions.account_id` to `accounts` fails |
| Closed account, negative balance | `accounts` row 57 (status='closed', balance=-150.00) | custom test `assert_closed_accounts_zero_balance` fails |
| AML alerts on closed accounts | every 50th row in `aml_alerts` references a closed account (~40 rows) | custom test `assert_aml_no_closed_accounts` fails |

## PII Coverage

`scripts/create_glossaries_and_metrics.py` creates a `PII` classification (`Sensitive`, `Restricted`, `NonSensitive` tags) and assigns the relevant `DataPrivacyPII` glossary terms to each PII column. This drives OpenMetadata's PII reports, governance metrics, and DSAR demos without needing auto-classification.

| Column | PII Type | Tag | Glossary term |
|--------|----------|-----|---------------|
| `customers.ssn` | SSN | `PII.Sensitive` | `DataPrivacyPII.SSN` |
| `customers.tax_id` | Tax ID (SSN/EIN) | `PII.Sensitive` | `DataPrivacyPII.TaxID` |
| `customers.date_of_birth` | Date of Birth | `PII.Sensitive` | `DataPrivacyPII.DOB` |
| `customers.email` | Email Address | `PII.Sensitive` | `DataPrivacyPII.EmailAddress` |
| `customers.phone` | Phone Number | `PII.Sensitive` | `DataPrivacyPII.PhoneNumber` |
| `customer_addresses.*` | Physical Address | `PII.Sensitive` | `DataPrivacyPII.PhysicalAddress` |
| `cards.card_number_masked` | Payment Card | `PII.Sensitive` | `DataPrivacyPII.PaymentCardInfo` |
| `card_authorizations.ip_address` | IP Address | `PII.Sensitive` | `DataPrivacyPII.IPAddress` |
| `wire_transfers.from_iban`, `wire_transfers.to_iban` | IBAN | `PII.Sensitive` | `DataPrivacyPII.IBAN` |
| `mobile_app_events.geo_latitude`, `geo_longitude` | Geo Location | `PII.Sensitive` | `DataPrivacyPII.GeoLocation` |
| `web_sessions.ip_address`, `login_attempts.ip_address` | IP Address | `PII.Sensitive` | `DataPrivacyPII.IPAddress` |
| `kyc_checks.documents_provided` | Document type list | `PII.Restricted` | `DataPrivacyPII.IdentityDocument` |
| `sanctions_screening.matched_name` | Full Name | `PII.Sensitive` | `DataPrivacyPII.FullName` |

## IFRS 9 / Risk Coverage

`raw_lending.loans` is enriched with impairment fields so the Risk Officer scenarios are first-class:

| Column | Description | Typical demo use |
|--------|-------------|------------------|
| `days_past_due` | Days since the most recent missed payment | Delinquency / bucketing analysis |
| `ifrs9_stage` | IFRS 9 stage (1 = performing, 2 = under-performing/SICR, 3 = credit-impaired) | "ECL by stage", credit-cost projections |
| `pd_12m` | 12-month probability of default for stage 1, lifetime for stage 2/3 | Risk dashboards |
| `lgd` | Loss given default — product-specific (mortgage 0.25–0.30, HELOC 0.55, business 0.55) | Capital + provisioning |
| `ead` | Exposure at default = current balance | Stress testing |
| `ecl_amount` | `pd_12m × lgd × ead` quantised to USD | ECL coverage demos, IFRS 9 disclosures |

`marts_risk.fct_loan_loss_provision` recomputes ECL from FICO + product (separate path) and `marts_risk.fct_delinquency` rolls up the stage 3 / charge-off buckets per product. Both paths exist intentionally so you can compare model-driven vs source-supplied risk numbers.

## Engineered Fraud + Chargeback Scenarios

| Scenario | Details | Demo use |
|----------|---------|----------|
| Fraud burst | 10 victim customers each see 80 card authorisations within a 24-hour window — high decline rate, mixed-geo IPs, mostly card-not-present, low-amount probing with rare large hits | Fraud detection, velocity rules, IP-geo discrepancy |
| Chargeback storm | 2 merchants take 40 disputes each within a 30-day window with `service_not_received` / `merchant_dispute` reasons | Merchant risk dashboards, dispute funnel analytics |

## Cookbook Demo Scenarios

Each persona below is a real seeded user with the right domain + ownership.

### CFO — *Robert Garcia*

- "What was NIM last month?"
- "How did fee revenue compare to last quarter?"
- "Show me the loan-loss provision trend."

Hits: `fct_nim`, `fct_fee_revenue`, `fct_loan_loss_provision`, finance domain glossary.

### Risk Officer — *Marcus Williams*

- "Which loans are most at risk?"
- "Show me ECL by IFRS 9 stage."
- "How many loans moved from Stage 1 to Stage 2 last quarter?"
- "Top 10 delinquent customers."
- "What is the ECL coverage ratio by product?"

Hits: `loans.ifrs9_stage`/`pd_12m`/`lgd`/`ead`/`ecl_amount`, `fct_delinquency`, `fct_loan_loss_provision`, `dim_credit_risk`.

### Compliance / AML — *David Kim*

- "How many AML alerts this month?"
- "Break down structuring alerts by weekday vs weekend." *(weekend-clustered pattern)*
- "What's the SAR filing rate?"
- "Show me alerts on closed accounts." *(intentional DQ scenario)*
- "Find narratives mentioning 'CTR threshold'." *(templated narrative search)*

Hits: `fct_aml_pipeline`, `aml_alerts`, `suspicious_activity_reports`, custom DQ tests.

### Fraud Analyst — *(uses Marcus's persona)*

- "Find customers with >50 card auths in 24h." *(fraud burst scenario)*
- "List declined auths with mixed-geo IPs."
- "Which merchants have a chargeback spike this quarter?" *(chargeback storm scenario)*

Hits: `card_authorizations`, `card_disputes`, `merchants` (MCC fraud codes).

### Data Engineer — *Sara Johnson*

- "What's the lineage from `raw_transactions.transactions` to `fct_monthly_pnl`?"
- "Which dbt tests are failing?"
- "Find orphan transactions."

Hits: lineage UI, dbt test results, the orphan-FK DQ defect.

### Data Steward — *Alice Chen*

- "Which tables contain SSN?"
- "Show me PII coverage."
- "What's the glossary term for `customers.ssn`?"

Hits: PII classification report, glossary navigation.

### Wealth Advisor — *Priya Patel*

- "What's total AUM?"
- "Top 10 holdings by market value."
- "Trade volume by asset class this quarter."

Hits: `fct_aum`, `dim_holdings`, `fct_trades`.

## Connection Details

| Service | Host | Port | User | Password |
|---------|------|-----:|------|----------|
| Superset | localhost | 8088 | `$SUPERSET_ADMIN_EMAIL` (default `admin@bank.demo`) | `$SUPERSET_ADMIN_PASSWORD` (default `BankAdmin123!`) |
| Redshift | `$REDSHIFT_HOST` | `$REDSHIFT_PORT` (default 5439) | `$REDSHIFT_USER` | `$REDSHIFT_PASSWORD` |
| OpenMetadata | `$AI_SDK_HOST` | — | JWT in `$AI_SDK_TOKEN` | — |

## Cleanup

```bash
# Stop Superset
make superset-down

# Remove the staged CSVs from S3
aws s3 rm s3://$BANKING_S3_BUCKET/$BANKING_S3_PREFIX/ --recursive

# Drop the raw schemas from Redshift
psql -h $REDSHIFT_HOST -p $REDSHIFT_PORT -U $REDSHIFT_USER -d $REDSHIFT_DATABASE <<'SQL'
DROP SCHEMA raw_core_banking      CASCADE;
DROP SCHEMA raw_transactions      CASCADE;
DROP SCHEMA raw_cards             CASCADE;
DROP SCHEMA raw_lending           CASCADE;
DROP SCHEMA raw_risk              CASCADE;
DROP SCHEMA raw_wealth            CASCADE;
DROP SCHEMA raw_digital           CASCADE;
DROP SCHEMA raw_marketing         CASCADE;
SQL
```

The dbt-built schemas (`staging`, `intermediate`, `marts_*`) can be dropped the same way once you no longer need the demo.

## File Structure

```
banking-redshift/
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── seeds/                       # 38 generated CSVs (raw_<schema>/<table>.csv)
│   └── models/
│       ├── staging/
│       ├── intermediate/
│       └── marts/
│           ├── core/
│           ├── finance/
│           ├── risk/
│           ├── wealth/
│           └── marketing/
├── docker/
│   └── superset/
│       └── docker-compose.yml       # Superset + metadata DB + cache
├── sql/
│   └── redshift_init.sql            # raw_* schemas + tables DDL
├── scripts/
│   ├── generate_seed_data.py        # Deterministic data generator (seed=42)
│   ├── upload_to_s3.sh              # Bulk upload of seeds to S3
│   ├── bootstrap_redshift.sh        # Apply redshift_init.sql
│   ├── load_to_redshift.sh          # COPY each table from S3
│   ├── setup_superset.sh            # Datasets, charts, dashboards
│   ├── ingest_metadata.sh           # Run S3/Redshift/dbt/Superset ingestion
│   ├── create_glossaries_and_metrics.py
│   └── create_owners_and_domains.py
├── ingestion/                       # OpenMetadata ingestion YAMLs
│   ├── s3.yaml
│   ├── redshift.yaml
│   ├── redshift_profiler.yaml       # Profiler + auto-PII workflow
│   ├── redshift_lineage.yaml
│   ├── dbt.yaml
│   └── superset.yaml
└── README.md
```
