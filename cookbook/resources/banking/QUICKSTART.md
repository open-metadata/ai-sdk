# Banking Demo — Quickstart

A copy-paste walkthrough from empty laptop to a fully demo-ready Banking + OpenMetadata environment.

All commands assume you start in this directory:

```bash
cd cookbook/resources/banking
```

> Already have data loaded and only need to (re)ingest into an OpenMetadata
> instance? Skip this and use [`RUNBOOK.md`](RUNBOOK.md) — the consolidated
> exports + ingest commands + troubleshooting.

## Pick a warehouse first

**Steps 0–13 below are the Redshift walkthrough**, ~45 minutes end to end (mostly
waiting on `dbt run` and `aws s3 cp`).

**On BigQuery the setup is much shorter** — no cluster to provision, no bucket, no
IAM role. Use the section immediately below instead, then rejoin the Redshift
walkthrough at Step 10 (Superset) since everything from there on is shared.

---

## BigQuery track (~20 minutes)

### 1. Tools and credentials

```bash
brew install --cask google-cloud-sdk        # or your platform's installer
brew install docker python@3.11

WAREHOUSE=bigquery make install-deps        # dbt-bigquery + openmetadata-ingestion[bigquery,…]
dbt --version                               # should list dbt-bigquery
```

Create a service account with `roles/bigquery.dataEditor` and
`roles/bigquery.jobUser`, download its JSON key, then authenticate the `bq` CLI.
`bq` reads gcloud's own credential store — it does **not** read
`GOOGLE_APPLICATION_CREDENTIALS`, which is what dbt, OpenMetadata and Superset use:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/keys/banking-sa.json"
gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS"
gcloud services enable bigquery.googleapis.com --project=my-gcp-project
```

### 2. Environment

```bash
cp .env.bigquery.example .env.bigquery
$EDITOR .env.bigquery                       # set BANKING_GCP_PROJECT, key path, AI_SDK_*
set -a && source .env.bigquery && set +a

env | grep -E "BANKING_|GOOGLE_APPLICATION|AI_SDK_" | sort
```

### 3. Generate, create, load

```bash
make generate-seeds                         # ~25s, 38 CSVs, ~220 MB
make generate-ddl                           # bigquery_init.sql + bq_schemas/*.json
WAREHOUSE=bigquery make init                # 8 datasets + 38 tables
WAREHOUSE=bigquery make load                # bq load, one call per CSV
```

Verify the load:

```bash
bq --project_id="$BANKING_GCP_PROJECT" query --use_legacy_sql=false \
  'select
     (select count(*) from raw_core_banking.customers)    as customers,
     (select count(*) from raw_transactions.transactions) as transactions,
     (select count(*) from raw_lending.loans)             as loans'
# expect 5000 / 250000 / 3000
```

Confirm the `\N` NULL marker was honoured — this should return rows with a
genuine `NULL`, not an empty string:

```bash
bq --project_id="$BANKING_GCP_PROJECT" query --use_legacy_sql=false \
  'select count(*) as null_line_2
   from raw_core_banking.customer_addresses
   where address_line_2 is null'
```

### 4. dbt

```bash
WAREHOUSE=bigquery make dbt                 # deps + run + test against --target bigquery
```

### 5. Rejoin the shared walkthrough

Continue at **Step 10 — Start Superset** below, prefixing the remaining `make`
commands with `WAREHOUSE=bigquery`, or just run:

```bash
WAREHOUSE=bigquery make superset-up
WAREHOUSE=bigquery make superset-setup
WAREHOUSE=bigquery make ingest-metadata
WAREHOUSE=bigquery make glossaries
WAREHOUSE=bigquery make context-center
```

---

# Redshift walkthrough

---

## Step 0 — Prerequisites (one-time)

Install the system tools you'll need.

```bash
# macOS (Homebrew)
brew install awscli postgresql@16 docker python@3.11

# Verify
aws --version            # >= aws-cli/2.x
psql --version           # >= 16
docker --version         # Docker Engine 24+
python3 --version        # >= 3.10
```

Start Docker Desktop (or `colima start`) so the Superset stack can run later.

Configure your AWS credentials and pick a region:

```bash
aws configure
# AWS Access Key ID:     <paste>
# AWS Secret Access Key: <paste>
# Default region name:   us-east-1
# Default output format: json
```

---

## Step 1 — Python dependencies

```bash
make install-deps
```

This installs `dbt-redshift`, `faker`, and `openmetadata-ingestion` with the
`redshift,dbt,superset,s3` extras. Verify:

```bash
dbt --version            # should list dbt-redshift
metadata --version       # the OpenMetadata CLI
```

---

## Step 2 — Provision a Redshift cluster

You need a Redshift cluster (RA3.xlplus is enough) reachable from your
workstation with:

1. **An attached IAM role** that has `s3:GetObject` and `s3:ListBucket` on the
   bucket you'll use in Step 3. Note the role's ARN — you'll paste it below.
2. **A security group** that permits inbound TCP from your IP on port 5439.
3. **Network access** — if your cluster is in a VPC, ensure it's publicly
   accessible OR you have a bastion / VPN.

If you don't already have one, the AWS Console wizard ("Create cluster" →
"Free trial" or "Production") finishes in ~5 minutes.

Record these values:

| What | Example |
|------|---------|
| Endpoint | `my-cluster.abc123.us-east-1.redshift.amazonaws.com` |
| Port | `5439` |
| Database | `dev` |
| Admin user | `admin` |
| Password | `**********` |
| IAM role ARN | `arn:aws:iam::123456789012:role/RedshiftS3Read` |

---

## Step 3 — Pick an S3 bucket

Choose a unique bucket name. The script will create it for you if it doesn't
exist. Example: `bank-demo-yourname-20240101`.

---

## Step 4 — Set environment variables

Create `.envrc` (or just export them in your shell). Replace each `***` with
the real value from Steps 2 and 3.

```bash
# === AWS / S3 ===
export AWS_REGION=us-east-1
export BANKING_S3_BUCKET=bank-demo-yourname-20240101
export BANKING_S3_PREFIX=raw

# === Redshift ===
export REDSHIFT_HOST=***.redshift.amazonaws.com
export REDSHIFT_PORT=5439
export REDSHIFT_DATABASE=dev
export REDSHIFT_USER=admin
export REDSHIFT_PASSWORD=***
export REDSHIFT_IAM_ROLE=arn:aws:iam::***:role/RedshiftS3Read

# === OpenMetadata ===
export AI_SDK_HOST=https://your-instance.getcollate.io
export AI_SDK_TOKEN=eyJraWQiOi***...

# === Superset (optional — defaults shown) ===
export SUPERSET_ADMIN_EMAIL=admin@bank.demo
export SUPERSET_ADMIN_PASSWORD=BankAdmin123!
```

Then load them:

```bash
source .envrc           # or: direnv allow
```

Sanity check:

```bash
env | grep -E "REDSHIFT_|BANKING_S3_|AI_SDK_" | sort
```

---

## Step 5 — Generate the seed CSVs

```bash
make generate-seeds
```

Takes ~25 seconds. Produces 38 CSVs under `dbt/seeds/raw_*/` totalling ~210 MB.
Deterministic (seed=42), so every run gives byte-identical output.

Verify:

```bash
ls dbt/seeds/raw_*/ | wc -l        # expect 38
du -sh dbt/seeds/                  # expect ~210M
```

---

## Step 6 — Upload to S3

```bash
make upload-s3
```

Creates the bucket if missing, then uploads every `dbt/seeds/raw_*/*.csv` to:

```
s3://${BANKING_S3_BUCKET}/${BANKING_S3_PREFIX}/<schema>/<table>/<table>.csv
```

Takes ~2 minutes depending on bandwidth. Auto-retries each file once on
transient failure. Encrypts each object with SSE-S3.

Verify:

```bash
aws s3 ls s3://${BANKING_S3_BUCKET}/${BANKING_S3_PREFIX}/raw_core_banking/customers/
# expect: customers.csv ... 1.1 MB
```

---

## Step 7 — Bootstrap Redshift schemas + tables

```bash
make init
```

`sql/redshift_init.sql` is committed, so this works as-is. If you changed
`schema/registry.py`, regenerate first with `make generate-ddl`.

Runs `sql/redshift_init.sql`. Creates 8 `raw_*` schemas and 38 tables with
correct types, distkeys, and sortkeys. **Drops + recreates** schemas — safe
to re-run.

Verify:

```bash
psql "host=${REDSHIFT_HOST} port=${REDSHIFT_PORT} dbname=${REDSHIFT_DATABASE} user=${REDSHIFT_USER} password=${REDSHIFT_PASSWORD}" \
    -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'raw_%' ORDER BY 1;"
# expect 8 rows
```

---

## Step 8 — COPY data from S3 into Redshift

```bash
make load
```

Generates one `TRUNCATE` + `COPY` per table inside a single transaction. Takes
~3-8 minutes depending on cluster size; the big tables are `transactions`
(250k), `mobile_app_events` (250k), and `login_attempts` (400k). Idempotent —
re-runs replace data, never duplicate.

Verify row counts:

```bash
psql "host=${REDSHIFT_HOST} port=${REDSHIFT_PORT} dbname=${REDSHIFT_DATABASE} user=${REDSHIFT_USER} password=${REDSHIFT_PASSWORD}" \
    -c "SELECT 'customers', COUNT(*) FROM raw_core_banking.customers
        UNION ALL SELECT 'transactions', COUNT(*) FROM raw_transactions.transactions
        UNION ALL SELECT 'loans', COUNT(*) FROM raw_lending.loans;"
# expect 5001 / 250000 / 3000
```

---

## Step 9 — Run dbt

```bash
make dbt
```

Runs `dbt deps && dbt run && dbt test` in `dbt/`. Builds:

- 38 staging views (`staging.stg_*`)
- 12 intermediate views (`intermediate.int_*`)
- 20 mart tables (`marts_core / marts_finance / marts_risk / marts_wealth / marts_marketing`)
- Runs 290+ data tests

Takes ~6–10 minutes against an `ra3.xlplus`.

The 8 intentional DQ defect tests **will fail by design** — that's the point;
they fuel the OpenMetadata DQ dashboard. Expected failures:

```
FAIL  not_null_stg_core_banking__customers_ssn
FAIL  assert_customers_email_valid
FAIL  assert_customers_dob_not_future
FAIL  dbt_utils_unique_combination_of_columns_stg_core_banking__customers
FAIL  not_null_stg_core_banking__customer_addresses_city
FAIL  assert_addresses_city_not_empty
FAIL  relationships_stg_transactions__transactions_account_id
FAIL  assert_closed_accounts_zero_balance
FAIL  assert_aml_no_closed_accounts
```

Any **other** failure is a real problem — investigate.

Generate the dbt catalog so OpenMetadata can ingest descriptions:

```bash
make dbt-docs
```

This populates `dbt/target/catalog.json` (required by `make ingest-metadata`).

---

## Step 10 — Start Superset

```bash
make superset-up
```

Starts a docker-compose stack on `http://localhost:8088`. First build takes
~3-5 minutes; subsequent starts are fast.

Verify in a browser. Login with `$SUPERSET_ADMIN_EMAIL` / `$SUPERSET_ADMIN_PASSWORD`.

---

## Step 11 — Provision Superset datasets, charts, dashboards

```bash
make superset-setup
```

Registers the Redshift database, creates 18 datasets, 20 charts, and 4
dashboards. Idempotent — re-runs reconcile by name.

Verify in the browser: navigate to Dashboards. You should see:

- Executive / CFO
- Risk & Compliance
- Customer Operations
- Digital Engagement

---

## Step 12 — Ingest into OpenMetadata

```bash
make ingest-metadata
```

Runs six workflows in order: S3 → Redshift metadata → Redshift profiler+PII →
Redshift query lineage → dbt metadata → Superset dashboards. Takes ~10-15
minutes (the profiler is the slowest).

Verify in OpenMetadata UI:

- `Services → Databases → banking-redshift` — should list 8 raw schemas + 4
  marts schemas
- `Services → Dashboards → banking-superset-redshift` — should list 4 dashboards
- Open any table — should show columns, sample data, profile, and PII tags
  on `customers.ssn`, `wire_transfers.from_iban`, etc.
- `Insights → Lineage` from `raw_transactions.transactions` should trace
  through staging → intermediate → marts.

---

## Step 13 — Seed glossaries, metrics, users, domains, teams, personas

```bash
make glossaries
```

Runs two Python scripts:

- `create_glossaries_and_metrics.py` — 6 glossaries, 112 terms, 35 metrics,
  2 classifications (PII, Banking), 7 tags, 19 PII column tags applied
- `create_owners_and_domains.py` — 6 users, 6 domains, 6 teams, 6 personas,
  domain experts, plus table-level owner+domain assignment for all 12 schemas

Re-runs are idempotent.

Verify in OpenMetadata UI:

- `Govern → Glossaries` → 6 glossaries listed
- `Govern → Classifications` → "PII" and "Banking" present
- `Settings → Members → Users` → 6 users (alice.chen, marcus.williams, etc.)
- `Settings → Members → Teams` → 6 teams
- `Settings → Members → Personas` → 6 personas
- `Domains` → 6 domains, each with an "Expert" set
- Open `customers.ssn` — should be tagged `PII.Sensitive` + `DataPrivacyPII.SSN`

---

## Step 14 — Run the demos

You now have:

- 4 Superset dashboards at `http://localhost:8088`
- A fully-catalogued OpenMetadata instance at `$AI_SDK_HOST`

Try the persona prompts from the [Cookbook Demo Scenarios](README.md#cookbook-demo-scenarios)
section of the README. The questions match real tables and metrics, e.g.:

- **CFO Robert Garcia** → "What was NIM last month?" → hits `marts_finance.fct_nim`
- **Risk Officer Marcus Williams** → "Show me ECL by IFRS 9 stage" → hits `raw_lending.loans.ifrs9_stage` + `marts_risk.fct_loan_loss_provision`
- **Compliance Officer David Kim** → "Show alerts on closed accounts" → fires the intentional DQ test
- **Data Steward Alice Chen** → "Which tables contain SSN?" → returns all `PII.Sensitive` columns

---

## End-to-end shortcut

If you've completed Steps 0–4 (prereqs + env vars) you can run everything
from Step 5 onward in one shot:

```bash
make all
```

This runs Steps 5 through 13 sequentially. Wall-clock: ~30–45 minutes.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `make load` fails with `S3ServiceException ... Access Denied` | The IAM role attached to Redshift can't read the bucket. Verify the role's policy has `s3:GetObject` + `s3:ListBucket` on `arn:aws:s3:::${BANKING_S3_BUCKET}/*` and that `REDSHIFT_IAM_ROLE` is the role *the cluster uses*, not your AWS CLI user role. |
| `make dbt` fails on connection timeout | Your Redshift security group blocks your IP. Add an inbound rule for your public IP on port 5439. |
| `make superset-up` first run hangs | Docker is fetching the Superset image (~700 MB). Wait. If it actually fails: `cd docker/superset && docker compose logs superset`. |
| `make ingest-metadata` fails with `dbt manifest not found` | `make dbt` now runs `dbt docs generate` for you; if you built dbt by hand, run `make dbt-docs` and re-run. |
| `make ingest-metadata` succeeds but lineage is empty in OpenMetadata | The lineage workflow uses Redshift's `STL_QUERY` view, which only contains queries from the last ~7 days. Re-run `make dbt` to repopulate the query log, then re-run `make ingest-metadata`. |
| `make glossaries` fails on `403 Forbidden` | Your `$AI_SDK_TOKEN` doesn't have the `EditGlossary` / `EditClassification` policies. Use an admin-level bot token. |
| Need to start over | `make superset-down`, `aws s3 rm s3://$BANKING_S3_BUCKET/$BANKING_S3_PREFIX/ --recursive`, then drop the Redshift schemas (see [Cleanup](README.md#cleanup) in README). Re-run from Step 5. |

---

## What's in the box

After completion you have:

- **8 raw + 4 mart schemas** in Redshift with 38 source tables + 20 mart tables (= 58 tables, ~270k transactions, ~3k loans with IFRS 9 staging, ~2k AML alerts with templated narratives, an engineered fraud burst, and an engineered chargeback storm)
- **4 Superset dashboards** with 20 charts wired to Redshift
- **OpenMetadata catalog** populated with: full table lineage S3 → Redshift → marts → Superset, dbt model descriptions on every column (792 documented), column-level PII tags (19 columns), 290+ data tests (8 intentionally failing for DQ demos), 6 glossaries + 112 terms, 35 business metrics with owners, 6 domains, 6 teams, 6 personas
- **Reproducible**: every run is deterministic (seed=42), so demo screenshots stay stable across runs
