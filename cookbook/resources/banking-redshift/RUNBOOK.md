# Banking Redshift Demo — Ingestion Runbook

Operational cheat-sheet for running the **local services** and ingesting the
**already-built** banking demo into **any** OpenMetadata / Collate instance
(local Docker, staging, prod, a teammate's sandbox…). Every export and command
you need, in order, plus the traps that actually bite.

**Use this doc when** the data already exists — Redshift is up and loaded, dbt
has been built at least once — and you just want to (re)point ingestion at an
OpenMetadata instance.

**Use [`QUICKSTART.md`](QUICKSTART.md) instead when** starting from an empty
laptop (it provisions a Redshift cluster, generates seeds, uploads to S3, and
`COPY`s the data). **Use [`README.md`](README.md)** for schema/scenario
reference.

To point at a **different** instance later, only two vars change —
`AI_SDK_HOST` and `AI_SDK_TOKEN` — then re-run the OM-facing targets. The
warehouse (Redshift / S3 / Superset) never moves.

---

## 0. Prerequisites

- Redshift cluster reachable, `raw_*` + `marts_*` schemas loaded (`make load` + `make dbt` done once)
- An OpenMetadata instance reachable, with an **admin/bot JWT** (needs `EditGlossary`, `EditClassification`, and impersonation for Context Center authors)
- Docker running (for the local Superset stack)
- Python deps installed: `make install-deps`

Run everything from this directory:

```bash
cd cookbook/resources/banking-redshift
```

---

## 1. Environment variables — one block

Drop this in `.envrc` (direnv) or `source` it. Replace every `***`.

```bash
# ── Redshift (dbt, ingest-redshift, lineage, profiler, superset-setup) ──
export REDSHIFT_HOST=***.redshift.amazonaws.com
export REDSHIFT_PORT=5439                       # set explicitly — yaml builds host:port
export REDSHIFT_DATABASE=dev
export REDSHIFT_USER=***
export REDSHIFT_PASSWORD=***
# export REDSHIFT_IAM_ROLE=arn:aws:iam::***:role/RedshiftS3Read   # ONLY for `make load` (COPY). Data loaded → skip.

# ── OpenMetadata / Collate (the target instance) ──
export AI_SDK_HOST=http://localhost:8585        # your OM server. NO trailing /api — the yaml appends it
export AI_SDK_TOKEN=***                          # admin/bot JWT
# export AI_SDK_SERVICE=banking-redshift          # DB service name in OM (default already this)

# ── Superset (local docker stack) ──
export SUPERSET_URL=http://localhost:8088
export SUPERSET_ADMIN_USER=admin                # MUST be "admin" — NOT admin@bank.demo
export SUPERSET_ADMIN_PASSWORD='BankAdmin123!'  # required by ingest-superset; unset → 401

# ── AWS / S3 — ONLY if you want S3 container metadata + S3→Redshift lineage ──
export AWS_REGION=us-east-1                      # unset → "invalid AWS region" in ingest-s3
export AWS_ACCESS_KEY_ID=***
export AWS_SECRET_ACCESS_KEY=***
# export AWS_SESSION_TOKEN=***                    # only for temporary/STS creds
export BANKING_S3_BUCKET=***
export BANKING_S3_PREFIX=raw
```

Sanity check:

```bash
env | grep -E "REDSHIFT_|AI_SDK_|SUPERSET_|BANKING_S3_|AWS_REGION" | sort
```

---

## 2. Start the local services (Superset)

Redshift is remote; the only local service is the Superset stack.

```bash
# one-time: create the compose env file (secret key + admin creds)
cp docker/superset/.env.example docker/superset/.env
# optional: set a real secret → SUPERSET_SECRET_KEY=$(openssl rand -base64 42)

make superset-up        # builds + starts superset + superset-db on :8088 (first build ~3-5 min)
```

Verify:

```bash
docker ps --format '{{.Names}}\t{{.Status}}' | grep -i superset
# then open http://localhost:8088  (login: admin / BankAdmin123!)
```

Provision datasets/charts/dashboards (needs Redshift reachable + `REDSHIFT_*`):

```bash
make superset-setup     # registers Redshift DB, 18 datasets, 20 charts, 4 dashboards (idempotent)
```

---

## 3. Ingest into OpenMetadata

First, make sure the dbt artifacts exist (ingest-dbt reads them):

```bash
cd dbt && DBT_PROFILES_DIR=$(pwd) dbt docs generate && cd ..
# produces target/manifest.json + catalog.json + run_results.json
```

Then pick **one** mode.

### Mode A — everything, including S3 (needs the AWS vars from §1)

```bash
make ingest-metadata    # S3 → Redshift → profiler+PII → query lineage → dbt → Superset
make s3-lineage         # S3 container → Redshift table lineage edges
```

### Mode B — skip S3 (no AWS needed)

```bash
make ingest-redshift    # schemas, tables, columns
make profile            # column profiles + auto-PII classification
make ingest-lineage     # STL_QUERY lineage (needs a dbt run in the last ~7 days)
make ingest-dbt         # model descriptions, tags, model lineage
make ingest-superset    # charts, dashboards, dataset→Redshift lineage
```

### Then — governance seeding (both modes)

```bash
make glossaries         # 6 glossaries, ~112 terms, 35 metrics, users, domains, teams, personas, PII column tags
make ai-automations     # 6 governance AI Automation templates
make context-center     # Context Center folders, files, pages, memories
```

---

## 4. Verify

```bash
# OM: service + schemas present
curl -s -H "Authorization: Bearer $AI_SDK_TOKEN" \
  "$AI_SDK_HOST/api/v1/databaseSchemas?service=banking-redshift&limit=50" \
  | python -c "import sys,json; print('schemas:', len(json.load(sys.stdin).get('data',[])))"
# expect 12 (8 raw_* + 4 marts_*)
```

In the UI: `banking-redshift` lists 12 schemas · `customers.ssn` tagged `PII.Sensitive` · lineage from `raw_transactions.transactions` traces staging → intermediate → marts · `banking-superset` lists 4 dashboards.

---

## 5. Re-point to a different instance

```bash
export AI_SDK_HOST=https://other-instance.getcollate.io
export AI_SDK_TOKEN=<its JWT>
# leave every REDSHIFT_/SUPERSET_/AWS_ var untouched
make ingest-metadata && make glossaries && make ai-automations && make context-center
```

The warehouse and Superset don't move — only metadata is re-pushed to the new host.

---

## Troubleshooting — the traps

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Invalid AWS region` / empty region in `ingest-s3` | `AWS_REGION` unset — `s3.yaml` interpolates `${AWS_REGION}` to empty | `export AWS_REGION=us-east-1` (+ AWS creds + bucket), or use **Mode B** to skip S3 entirely |
| `ingest-superset` → `CheckAccess-401 UNAUTHORIZED .../security/login` | Superset creds wrong: `SUPERSET_ADMIN_PASSWORD` unset, or `SUPERSET_ADMIN_USER` set to the **email** instead of `admin` | `export SUPERSET_ADMIN_USER=admin` and `export SUPERSET_ADMIN_PASSWORD='BankAdmin123!'` |
| `ingest-superset` retries `host.docker.internal:8088` → `NameResolutionError` | **Red herring** — OM's connection test auto-swaps `localhost`→`host.docker.internal` *after* the 401; that name only resolves inside containers | Fix the 401 above; the localhost attempt then succeeds and the fallback never fires |
| dbt: `Unable to ingest owner from DBT ... name openmetadata` (repeated) | `catalog.json`'s relation `owner` = the **Redshift role** that built the tables (`openmetadata`); no OM user/team has that name. **Harmless** — mart owners (alice.chen…) come from the manifest and still attach | Ignore it, **or** create an OM user named `openmetadata`, **or** set `dbtUpdateOwners: false` in `ingestion/dbt.yaml` |
| `ingest-metadata` → `dbt manifest not found` | Skipped `dbt docs generate` | Run the §3 dbt artifacts step, re-run |
| Lineage empty after `ingest-lineage` | Redshift `STL_QUERY` only keeps ~7 days; the demo queries aged out | Re-run `make dbt` to repopulate the query log, then re-run lineage |
| `glossaries` → `403 Forbidden` | Token lacks `EditGlossary` / `EditClassification` | Use an admin/bot JWT |
| dbt descriptions stale in OM | `catalog.json` older than the last `dbt run` | Regenerate: `cd dbt && DBT_PROFILES_DIR=$(pwd) dbt docs generate && cd ..` |

---

## Command index

| Target | What |
|--------|------|
| `make superset-up` / `superset-down` | Start / stop local Superset stack |
| `make superset-setup` | Provision Superset DB, datasets, charts, dashboards |
| `make ingest-metadata` | All OM workflows (S3, Redshift, profiler+PII, lineage, dbt, Superset) |
| `make ingest-s3` / `ingest-redshift` / `ingest-lineage` / `ingest-dbt` / `ingest-superset` | Individual OM workflows |
| `make profile` | Redshift profiler + auto-PII classification only |
| `make s3-lineage` | S3 container → Redshift table lineage edges |
| `make glossaries` | Glossaries, terms, metrics, users, domains, teams, personas, PII tags |
| `make ai-automations` | 6 governance AI Automation templates |
| `make context-center` | Context Center folders, files, pages, memories |
| `make context-center-reset` | Wipe + re-seed Context Center |

Full target list: `make help`.
