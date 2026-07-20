# =============================================================================
# Banking Redshift Demo — local Makefile
# =============================================================================
# End-to-end S3 -> Redshift -> Superset -> OpenMetadata banking demo.
# All paths are relative to this directory. Run targets from here:
#
#   cd cookbook/resources/banking-redshift
#   make all
#
# See README.md for prerequisites and env-var setup.
# =============================================================================

.DEFAULT_GOAL := help

help:  ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## / {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install-deps:  ## Install Python deps (dbt-redshift, faker, openmetadata-ingestion)
	@echo "Installing banking-redshift Python deps..."
	pip install dbt-redshift faker "openmetadata-ingestion[redshift,dbt,superset,s3]"
	@echo "Deps installed."

generate-seeds:  ## Generate the 38 raw CSV seeds (deterministic, seed=42)
	@echo "Generating seed data..."
	python scripts/generate_seed_data.py

upload-s3:  ## Upload the seed CSVs to s3://$$BANKING_S3_BUCKET/$$BANKING_S3_PREFIX/
	@echo "Required env: AWS_REGION, BANKING_S3_BUCKET (optional: BANKING_S3_PREFIX)"
	bash scripts/upload_to_s3.sh

init-redshift:  ## Bootstrap Redshift: create raw_* schemas + tables (sql/redshift_init.sql)
	@echo "Required env: REDSHIFT_HOST, REDSHIFT_PORT, REDSHIFT_DATABASE, REDSHIFT_USER, REDSHIFT_PASSWORD"
	bash scripts/bootstrap_redshift.sh

load:  ## COPY the staged CSVs from S3 into Redshift raw_* tables
	@echo "Required env: REDSHIFT_*, BANKING_S3_BUCKET, REDSHIFT_IAM_ROLE"
	bash scripts/load_to_redshift.sh

dbt:  ## dbt deps + run + test against Redshift
	@echo "Running dbt against Redshift..."
	cd dbt && DBT_PROFILES_DIR=$$(pwd) dbt deps && \
	         DBT_PROFILES_DIR=$$(pwd) dbt run && \
	         DBT_PROFILES_DIR=$$(pwd) dbt test

dbt-seed:  ## Fallback: load raw data via dbt seed --full-refresh (skip S3/COPY path)
	cd dbt && DBT_PROFILES_DIR=$$(pwd) dbt seed --full-refresh

superset-up:  ## Start the Superset docker-compose stack at http://localhost:8088
	cd docker/superset && docker-compose up -d --build
	@echo ""
	@echo "Superset: http://localhost:8088"

superset-setup:  ## Provision Superset: database, datasets, charts, dashboards
	bash scripts/setup_superset.sh

superset-down:  ## Stop the Superset docker-compose stack
	cd docker/superset && docker-compose down

ingest-metadata:  ## Run all OpenMetadata ingestion workflows (S3, Redshift, profiler, dbt, Superset)
	@echo "Required env: AI_SDK_HOST, AI_SDK_TOKEN, REDSHIFT_*, BANKING_S3_BUCKET"
	bash scripts/ingest_metadata.sh

profile:  ## Run only the Redshift profiler + PII auto-classification workflows
	@echo "Required env: AI_SDK_HOST, AI_SDK_TOKEN, REDSHIFT_*"
	cd ingestion && metadata profile  -c redshift_profiler.yaml
	cd ingestion && metadata classify -c redshift_autoclassification.yaml

ingest-s3:  ## Run only the S3 storage workflow
	@echo "Required env: AI_SDK_HOST, AI_SDK_TOKEN, AWS_*, BANKING_S3_BUCKET"
	cd ingestion && metadata ingest -c s3.yaml

ingest-redshift:  ## Run only Redshift metadata workflow
	@echo "Required env: AI_SDK_HOST, AI_SDK_TOKEN, REDSHIFT_*"
	cd ingestion && metadata ingest -c redshift.yaml

ingest-lineage:  ## Run only Redshift query lineage workflow
	@echo "Required env: AI_SDK_HOST, AI_SDK_TOKEN, REDSHIFT_*"
	cd ingestion && metadata ingest -c redshift_lineage.yaml

ingest-dbt:  ## Run only dbt metadata workflow
	@echo "Required env: AI_SDK_HOST, AI_SDK_TOKEN (optional: BANKING_DBT_TARGET)"
	export BANKING_DBT_TARGET="$${BANKING_DBT_TARGET:-$$(pwd)/dbt/target}" && \
	  cd ingestion && metadata ingest -c dbt.yaml

s3-lineage:  ## Create S3 container -> Redshift table lineage edges (run after ingest-s3 + ingest-redshift)
	@echo "Required env: AI_SDK_HOST, AI_SDK_TOKEN"
	python scripts/create_s3_redshift_lineage.py --database $${REDSHIFT_DATABASE:-dev}

ingest-superset:  ## Run only Superset dashboards workflow
	@echo "Required env: AI_SDK_HOST, AI_SDK_TOKEN, SUPERSET_ADMIN_PASSWORD (optional: SUPERSET_URL, SUPERSET_ADMIN_USER)"
	export SUPERSET_URL="$${SUPERSET_URL:-http://localhost:8088}" && \
	  export SUPERSET_ADMIN_USER="$${SUPERSET_ADMIN_USER:-admin}" && \
	  cd ingestion && metadata ingest -c superset.yaml

glossaries:  ## Seed glossaries, terms, metrics, owners, and domains in OpenMetadata
	python scripts/create_glossaries_and_metrics.py
	python scripts/create_owners_and_domains.py

ai-automations:  ## Seed 6 governance AI Automation TEMPLATES (ownership, domain, PII, glossary, certification, compliance)
	@echo "Required env: AI_SDK_HOST, AI_SDK_TOKEN"
	python scripts/create_ai_automations.py

context-center:  ## Seed Context Center folders, files, pages and memories (banking-themed)
	@echo "Required env: AI_SDK_HOST, AI_SDK_TOKEN (optional: REDSHIFT_DATABASE)"
	python scripts/create_context_center.py \
		--db-service $${BANKING_DB_SERVICE:-banking-redshift} \
		--database $${REDSHIFT_DATABASE:-dev}

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

all:  ## Run the full banking-redshift demo end-to-end
	@$(MAKE) generate-seeds --no-print-directory
	@$(MAKE) upload-s3 --no-print-directory
	@$(MAKE) init-redshift --no-print-directory
	@$(MAKE) load --no-print-directory
	@$(MAKE) dbt --no-print-directory
	@$(MAKE) superset-up --no-print-directory
	@$(MAKE) superset-setup --no-print-directory
	@$(MAKE) ingest-metadata --no-print-directory
	@$(MAKE) glossaries --no-print-directory
	@$(MAKE) ai-automations --no-print-directory
	@$(MAKE) context-center --no-print-directory
	@echo ""
	@echo "banking-redshift demo is ready. See README.md for demo scenarios."

.PHONY: help install-deps generate-seeds upload-s3 init-redshift load \
        dbt dbt-seed superset-up superset-setup superset-down \
        ingest-metadata profile ingest-s3 ingest-redshift ingest-lineage \
        ingest-dbt ingest-superset s3-lineage glossaries ai-automations \
        context-center context-center-clean context-center-clean-memories \
        context-center-reset all
