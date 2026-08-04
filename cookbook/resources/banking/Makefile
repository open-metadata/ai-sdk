# =============================================================================
# Banking Demo — local Makefile
# =============================================================================
# End-to-end banking demo on either warehouse:
#
#   Redshift:  seeds -> S3 -> Redshift -> Superset -> OpenMetadata
#   BigQuery:  seeds -> BigQuery -> Superset -> OpenMetadata
#
# Pick the warehouse with WAREHOUSE; it defaults to redshift.
# All paths are relative to this directory. Run targets from here:
#
#   cd cookbook/resources/banking
#   make all
#   WAREHOUSE=bigquery make all
#
# See README.md for prerequisites and env-var setup.
# =============================================================================

.DEFAULT_GOAL := help

WAREHOUSE ?= redshift

# Per-warehouse service names, overridable. Keeping the BI service distinct
# lets both targets coexist in one OpenMetadata instance.
BANKING_DB_SERVICE ?= banking-$(WAREHOUSE)
BANKING_BI_SERVICE ?= banking-superset-$(WAREHOUSE)

# The "database" level of an OpenMetadata FQN: <service>.<database>.<schema>.<table>.
# On BigQuery that is the GCP project; on Redshift it is the database name. Every
# seeding script needs it to resolve table FQNs — get it wrong and ownership,
# domains and PII tags silently attach to nothing.
ifeq ($(WAREHOUSE),bigquery)
BANKING_DATABASE ?= $(BANKING_GCP_PROJECT)
else
BANKING_DATABASE ?= $(if $(REDSHIFT_DATABASE),$(REDSHIFT_DATABASE),dev)
endif

# The ingestion YAMLs interpolate this with os.path.expandvars, which leaves an
# unset variable as the literal ${NAME} rather than falling back — so it must
# always carry a value, not just when the shell scripts set one.
BANKING_BQ_LOCATION ?= US

export WAREHOUSE
export BANKING_DB_SERVICE
export BANKING_BI_SERVICE
export BANKING_DATABASE
export BANKING_BQ_LOCATION

help:  ## Show this help
	@echo "Warehouse: $(WAREHOUSE)   (override with WAREHOUSE=bigquery)"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## / {printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install-deps:  ## Install Python deps for the selected warehouse
ifeq ($(WAREHOUSE),bigquery)
	@echo "Installing banking (BigQuery) Python deps..."
	pip install dbt-bigquery faker sqlglot "openmetadata-ingestion[bigquery,dbt,superset]"
else
	@echo "Installing banking (Redshift) Python deps..."
	pip install dbt-redshift faker sqlglot "openmetadata-ingestion[redshift,dbt,superset,s3]"
endif
	@echo "Deps installed."

generate-seeds:  ## Generate the 38 raw CSV seeds (deterministic, seed=42)
	@echo "Generating seed data..."
	python scripts/generate_seed_data.py
	@$(MAKE) validate-seeds --no-print-directory

validate-seeds:  ## Check every seed CSV against the types in schema/registry.py
	python scripts/validate_seeds.py

generate-ddl:  ## Render sql/*.sql and sql/bq_schemas/ from schema/registry.py
	@echo "Generating DDL from the schema registry..."
	python scripts/generate_ddl.py

# -----------------------------------------------------------------------------
# Warehouse: create schemas/datasets + tables, then load the seed data
# -----------------------------------------------------------------------------

init:  ## Create the raw schemas/datasets and source tables
ifeq ($(WAREHOUSE),bigquery)
	@echo "Required env: BANKING_GCP_PROJECT (optional: BANKING_BQ_LOCATION)"
	bash scripts/bigquery/bootstrap_bigquery.sh
else
	@echo "Required env: REDSHIFT_HOST, REDSHIFT_PORT, REDSHIFT_DATABASE, REDSHIFT_USER, REDSHIFT_PASSWORD"
	bash scripts/redshift/bootstrap_redshift.sh
endif

load:  ## Load the seed CSVs into the raw tables
ifeq ($(WAREHOUSE),bigquery)
	@echo "Required env: BANKING_GCP_PROJECT (optional: BANKING_BQ_LOCATION)"
	bash scripts/bigquery/load_to_bigquery.sh
else
	@echo "Required env: REDSHIFT_*, BANKING_S3_BUCKET, REDSHIFT_IAM_ROLE"
	bash scripts/redshift/load_to_redshift.sh
endif

upload-s3:  ## [redshift only] Upload the seed CSVs to s3://$$BANKING_S3_BUCKET/$$BANKING_S3_PREFIX/
ifeq ($(WAREHOUSE),bigquery)
	@echo "Skipping upload-s3: the BigQuery target loads local files directly."
else
	@echo "Required env: AWS_REGION, BANKING_S3_BUCKET (optional: BANKING_S3_PREFIX)"
	bash scripts/redshift/upload_to_s3.sh
endif

destroy-bigquery:  ## [bigquery only] Delete every raw dataset and its contents
	@echo "Required env: BANKING_GCP_PROJECT"
	@echo "About to delete every raw_* dataset in $${BANKING_GCP_PROJECT} and all their tables."
	@read -p "Type 'yes' to continue: " confirm && [ "$$confirm" = "yes" ] || (echo "Aborted." && exit 1)
	@for schema in $$(python3 -c 'from schema.registry import raw_schemas; print(" ".join(raw_schemas()))'); do \
		echo "  removing $$schema"; \
		bq --project_id="$${BANKING_GCP_PROJECT}" rm -r -f --dataset "$${BANKING_GCP_PROJECT}:$$schema"; \
	done

# -----------------------------------------------------------------------------
# dbt
# -----------------------------------------------------------------------------

dbt:  ## dbt deps + compile + dialect check + run + test + docs generate
	@echo "Running dbt against $(WAREHOUSE)..."
	cd dbt && DBT_PROFILES_DIR=$$(pwd) dbt deps && \
	         DBT_PROFILES_DIR=$$(pwd) dbt compile --target $(WAREHOUSE)
	@$(MAKE) validate-models --no-print-directory
	# docs generate is not optional: it writes catalog.json, which the dbt
	# ingestion workflow requires alongside manifest.json and run_results.json.
	cd dbt && DBT_PROFILES_DIR=$$(pwd) dbt run  --target $(WAREHOUSE) && \
	         DBT_PROFILES_DIR=$$(pwd) dbt test --target $(WAREHOUSE) && \
	         DBT_PROFILES_DIR=$$(pwd) dbt docs generate --target $(WAREHOUSE)

validate-models:  ## Check the compiled SQL against the target warehouse's dialect
	python scripts/validate_models.py --target $(WAREHOUSE)

dbt-docs:  ## Regenerate just the dbt artifacts that OpenMetadata ingestion reads
	cd dbt && DBT_PROFILES_DIR=$$(pwd) dbt docs generate --target $(WAREHOUSE)

dbt-seed:  ## Fallback: load raw data via dbt seed --full-refresh (skips the native loader)
	@echo "dbt seed has no null-marker setting, so the CSVs are regenerated with"
	@echo "empty fields for NULLs. Re-run 'make generate-seeds' before 'make load'."
	python scripts/generate_seed_data.py --null-marker ''
	cd dbt && DBT_PROFILES_DIR=$$(pwd) dbt seed --target $(WAREHOUSE) --full-refresh

# -----------------------------------------------------------------------------
# Superset
# -----------------------------------------------------------------------------

superset-up:  ## Start the Superset docker-compose stack at http://localhost:8088
	cd docker/superset && docker-compose up -d --build
	@echo ""
	@echo "Superset: http://localhost:8088"

superset-setup:  ## Provision Superset: database, datasets, charts, dashboards
	bash scripts/setup_superset.sh

superset-down:  ## Stop the Superset docker-compose stack
	cd docker/superset && docker-compose down

# -----------------------------------------------------------------------------
# OpenMetadata ingestion
# -----------------------------------------------------------------------------

ingest-metadata:  ## Run all OpenMetadata ingestion workflows for the selected warehouse
	@echo "Required env: AI_SDK_HOST, AI_SDK_TOKEN, and the warehouse credentials"
	bash scripts/ingest_metadata.sh

profile:  ## Run only the profiler + PII auto-classification workflows
	@echo "Required env: AI_SDK_HOST, AI_SDK_TOKEN, and the warehouse credentials"
	cd ingestion/$(WAREHOUSE) && metadata profile  -c $(WAREHOUSE)_profiler.yaml
	cd ingestion/$(WAREHOUSE) && metadata classify -c $(WAREHOUSE)_autoclassification.yaml

ingest-warehouse:  ## Run only the warehouse metadata workflow
	@echo "Required env: AI_SDK_HOST, AI_SDK_TOKEN, and the warehouse credentials"
	cd ingestion/$(WAREHOUSE) && metadata ingest -c $(WAREHOUSE).yaml

ingest-lineage:  ## Run only the warehouse query-lineage workflow
	@echo "Required env: AI_SDK_HOST, AI_SDK_TOKEN, and the warehouse credentials"
	cd ingestion/$(WAREHOUSE) && metadata ingest -c $(WAREHOUSE)_lineage.yaml

ingest-s3:  ## [redshift only] Run only the S3 storage workflow
ifeq ($(WAREHOUSE),bigquery)
	@echo "Skipping ingest-s3: the BigQuery target has no storage service."
else
	@echo "Required env: AI_SDK_HOST, AI_SDK_TOKEN, AWS_*, BANKING_S3_BUCKET"
	cd ingestion/redshift && metadata ingest -c s3.yaml
endif

s3-lineage:  ## [redshift only] Create S3 container -> Redshift table lineage edges
ifeq ($(WAREHOUSE),bigquery)
	@echo "Skipping s3-lineage: the BigQuery target has no storage service."
else
	@echo "Required env: AI_SDK_HOST, AI_SDK_TOKEN"
	python scripts/redshift/create_s3_redshift_lineage.py --database $${REDSHIFT_DATABASE:-dev}
endif

ingest-dbt:  ## Run only dbt metadata workflow
	@echo "Required env: AI_SDK_HOST, AI_SDK_TOKEN (optional: BANKING_DBT_TARGET)"
	export BANKING_DBT_TARGET="$${BANKING_DBT_TARGET:-$$(pwd)/dbt/target}" && \
	  cd ingestion/shared && metadata ingest -c dbt.yaml

ingest-superset:  ## Run only Superset dashboards workflow
	@echo "Required env: AI_SDK_HOST, AI_SDK_TOKEN, SUPERSET_ADMIN_PASSWORD (optional: SUPERSET_URL, SUPERSET_ADMIN_USER)"
	export SUPERSET_URL="$${SUPERSET_URL:-http://localhost:8088}" && \
	  export SUPERSET_ADMIN_USER="$${SUPERSET_ADMIN_USER:-admin}" && \
	  cd ingestion/shared && metadata ingest -c superset.yaml

# -----------------------------------------------------------------------------
# OpenMetadata content seeding
# -----------------------------------------------------------------------------

glossaries:  ## Seed glossaries, terms, metrics, owners, domains, teams, personas, PII tags
	@echo "Required env: AI_SDK_HOST, AI_SDK_TOKEN"
	@test -n "$(BANKING_DATABASE)" || (echo "BANKING_DATABASE is empty — set BANKING_GCP_PROJECT (bigquery) or REDSHIFT_DATABASE." && exit 1)
	python scripts/create_glossaries_and_metrics.py \
		--service $(BANKING_DB_SERVICE) \
		--database $(BANKING_DATABASE)
	python scripts/create_owners_and_domains.py \
		--service $(BANKING_DB_SERVICE) \
		--database $(BANKING_DATABASE)

context-center:  ## Seed Context Center folders, files, pages and memories (banking-themed)
	@echo "Required env: AI_SDK_HOST, AI_SDK_TOKEN"
	@test -n "$(BANKING_DATABASE)" || (echo "BANKING_DATABASE is empty — set BANKING_GCP_PROJECT (bigquery) or REDSHIFT_DATABASE." && exit 1)
	python scripts/create_context_center.py \
		--db-service $(BANKING_DB_SERVICE) \
		--database $(BANKING_DATABASE)

context-center-clean:  ## Hard-delete ALL Context Center entities (folders, files, pages, memories)
	@echo "Required env: AI_SDK_HOST, AI_SDK_TOKEN"
	@echo "About to hard-delete every Context Center folder, file, page and memory."
	@read -p "Type 'yes' to continue: " confirm && [ "$$confirm" = "yes" ] || (echo "Aborted." && exit 1)
	python scripts/create_context_center.py --purge

context-center-clean-memories:  ## Hard-delete ALL Context Center memories only
	@echo "Required env: AI_SDK_HOST, AI_SDK_TOKEN"
	@echo "About to hard-delete every Context Center memory."
	@read -p "Type 'yes' to continue: " confirm && [ "$$confirm" = "yes" ] || (echo "Aborted." && exit 1)
	python scripts/create_context_center.py --purge-memories

context-center-reset:  ## Hard-delete then re-seed Context Center end-to-end
	@$(MAKE) context-center-clean --no-print-directory
	@$(MAKE) context-center --no-print-directory

# -----------------------------------------------------------------------------

all:  ## Run the full banking demo end-to-end for the selected warehouse
	@$(MAKE) generate-seeds --no-print-directory
	@$(MAKE) generate-ddl --no-print-directory
	@$(MAKE) upload-s3 --no-print-directory
	@$(MAKE) init --no-print-directory
	@$(MAKE) load --no-print-directory
	@$(MAKE) dbt --no-print-directory
	@$(MAKE) superset-up --no-print-directory
	@$(MAKE) superset-setup --no-print-directory
	@$(MAKE) ingest-metadata --no-print-directory
	@$(MAKE) glossaries --no-print-directory
	@$(MAKE) context-center --no-print-directory
	@echo ""
	@echo "banking demo ($(WAREHOUSE)) is ready. See README.md for demo scenarios."

.PHONY: help install-deps generate-seeds validate-seeds generate-ddl init load upload-s3 \
        destroy-bigquery dbt validate-models dbt-docs dbt-seed superset-up superset-setup superset-down \
        ingest-metadata profile ingest-warehouse ingest-lineage ingest-s3 \
        s3-lineage ingest-dbt ingest-superset glossaries \
        context-center context-center-clean context-center-clean-memories \
        context-center-reset all
