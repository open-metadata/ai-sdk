# Dashboards

The four banking demo dashboards (Executive / CFO, Risk & Compliance,
Customer & Ops, Digital Engagement) are created programmatically by
`scripts/setup_superset_charts.py`. That script is idempotent — re-running
it will not duplicate existing charts or dashboards.

## Workflow

1. Start the Superset stack:
   ```bash
   cd docker/superset
   cp .env.example .env  # edit values as needed
   docker compose up -d
   ```

2. Export the credentials for your warehouse and run the provisioning script.
   The datasets, charts and dashboards are identical either way — only the
   database connection differs.

   Redshift:
   ```bash
   export WAREHOUSE=redshift
   export REDSHIFT_HOST=...
   export REDSHIFT_PORT=5439
   export REDSHIFT_DATABASE=...
   export REDSHIFT_USER=...
   export REDSHIFT_PASSWORD=...
   bash scripts/setup_superset.sh
   ```

   BigQuery:
   ```bash
   export WAREHOUSE=bigquery
   export BANKING_GCP_PROJECT=...
   export GOOGLE_APPLICATION_CREDENTIALS=~/keys/banking-sa.json
   bash scripts/setup_superset.sh
   ```

3. Open <http://localhost:8088> and log in as `admin / BankAdmin123!`.

## Exporting dashboards to JSON (optional)

If you tweak a dashboard in the Superset UI and want to version-control the
result, export it via the UI (Settings → Export) and drop the resulting
`.json` (or `.zip`) into this directory:

```
superset/dashboards/
├── executive-cfo.json
├── risk-compliance.json
├── customer-ops.json
└── digital-engagement.json
```

These files are not consumed by the setup script today — they're only kept
here so that customisations made in the UI can be reviewed in git.
