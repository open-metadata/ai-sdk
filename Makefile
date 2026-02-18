# Metadata AI SDK - Centralized Version Management
#
# Usage:
#   make version              # Show current version
#   make check-versions       # Validate all versions match
#   make bump-version V=0.2.0 # Update all SDKs to new version
#   make tag-all              # Create git tags for all components
#   make tag-cli              # Create tag for CLI only
#   make tag-python           # Create tag for Python only
#   make tag-typescript       # Create tag for TypeScript only
#   make tag-java             # Create tag for Java only
#   make tag-n8n              # Create tag for n8n only

.PHONY: help version check-versions bump-version sync-versions \
        tag-all tag-cli tag-python tag-typescript tag-java tag-n8n

# Version file paths
VERSION_FILE := VERSION
CLI_CARGO := cli/Cargo.toml
PYTHON_PYPROJECT := python/pyproject.toml
TS_PACKAGE := typescript/package.json
JAVA_POM := java/pom.xml
N8N_PACKAGE := n8n-nodes-metadata/package.json

# Read current version from VERSION file
CURRENT_VERSION := $(shell cat $(VERSION_FILE) 2>/dev/null | tr -d '[:space:]')

help:  ## Show this help message
	@echo "Metadata AI SDK - Version Management"
	@echo ""
	@echo "Current version: $(CURRENT_VERSION)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

version:  ## Show current version from VERSION file
	@echo "$(CURRENT_VERSION)"

check-versions:  ## Validate all SDK versions match the VERSION file
	@echo "Checking version consistency..."
	@echo "VERSION file: $(CURRENT_VERSION)"
	@echo ""
	@ERRORS=0; \
	\
	CLI_VER=$$(grep '^version = ' $(CLI_CARGO) | head -1 | sed 's/version = "\(.*\)"/\1/'); \
	if [ "$$CLI_VER" = "$(CURRENT_VERSION)" ]; then \
		echo "  [OK] CLI (Rust):     $$CLI_VER"; \
	else \
		echo "  [MISMATCH] CLI (Rust):     $$CLI_VER"; \
		ERRORS=1; \
	fi; \
	\
	PY_VER=$$(grep '^version = ' $(PYTHON_PYPROJECT) | head -1 | sed 's/version = "\(.*\)"/\1/'); \
	if [ "$$PY_VER" = "$(CURRENT_VERSION)" ]; then \
		echo "  [OK] Python:         $$PY_VER"; \
	else \
		echo "  [MISMATCH] Python:         $$PY_VER"; \
		ERRORS=1; \
	fi; \
	\
	TS_VER=$$(grep '"version"' $(TS_PACKAGE) | head -1 | sed 's/.*"version": "\(.*\)".*/\1/'); \
	if [ "$$TS_VER" = "$(CURRENT_VERSION)" ]; then \
		echo "  [OK] TypeScript:     $$TS_VER"; \
	else \
		echo "  [MISMATCH] TypeScript:     $$TS_VER"; \
		ERRORS=1; \
	fi; \
	\
	JAVA_VER=$$(grep -A1 '<artifactId>metadata-ai-sdk</artifactId>' $(JAVA_POM) | grep '<version>' | sed 's/.*<version>\(.*\)<\/version>.*/\1/'); \
	if [ "$$JAVA_VER" = "$(CURRENT_VERSION)" ]; then \
		echo "  [OK] Java:           $$JAVA_VER"; \
	else \
		echo "  [MISMATCH] Java:           $$JAVA_VER"; \
		ERRORS=1; \
	fi; \
	\
	N8N_VER=$$(grep '"version"' $(N8N_PACKAGE) | head -1 | sed 's/.*"version": "\(.*\)".*/\1/'); \
	if [ "$$N8N_VER" = "$(CURRENT_VERSION)" ]; then \
		echo "  [OK] n8n:            $$N8N_VER"; \
	else \
		echo "  [MISMATCH] n8n:            $$N8N_VER"; \
		ERRORS=1; \
	fi; \
	\
	echo ""; \
	if [ $$ERRORS -eq 0 ]; then \
		echo "All versions match!"; \
	else \
		echo "Version mismatches detected. Run 'make sync-versions' to fix."; \
		exit 1; \
	fi

bump-version:  ## Update VERSION file and all SDKs (usage: make bump-version V=0.2.0)
	@if [ -z "$(V)" ]; then \
		echo "Error: Version not specified. Usage: make bump-version V=0.2.0"; \
		exit 1; \
	fi
	@echo "Bumping version from $(CURRENT_VERSION) to $(V)..."
	@echo "$(V)" > $(VERSION_FILE)
	@$(MAKE) sync-versions --no-print-directory
	@echo ""
	@echo "Version updated to $(V)"
	@echo "Next steps:"
	@echo "  1. Review changes: git diff"
	@echo "  2. Commit: git add -A && git commit -m 'Bump version to $(V)'"
	@echo "  3. Tag releases: make tag-all"

sync-versions:  ## Sync all SDK versions to match VERSION file
	@echo "Syncing all SDKs to version $(CURRENT_VERSION)..."
	@# CLI - Cargo.toml
	@sed -i.bak 's/^version = ".*"/version = "$(CURRENT_VERSION)"/' $(CLI_CARGO) && rm -f $(CLI_CARGO).bak
	@echo "  Updated: $(CLI_CARGO)"
	@# Python - pyproject.toml
	@sed -i.bak 's/^version = ".*"/version = "$(CURRENT_VERSION)"/' $(PYTHON_PYPROJECT) && rm -f $(PYTHON_PYPROJECT).bak
	@echo "  Updated: $(PYTHON_PYPROJECT)"
	@# TypeScript - package.json (update first "version" occurrence)
	@sed -i.bak 's/"version": ".*"/"version": "$(CURRENT_VERSION)"/' $(TS_PACKAGE) && rm -f $(TS_PACKAGE).bak
	@echo "  Updated: $(TS_PACKAGE)"
	@# Java - pom.xml (update version after artifactId line)
	@sed -i.bak '/<artifactId>metadata-ai-sdk<\/artifactId>/{ n; s/<version>.*<\/version>/<version>$(CURRENT_VERSION)<\/version>/; }' $(JAVA_POM) && rm -f $(JAVA_POM).bak
	@echo "  Updated: $(JAVA_POM)"
	@# n8n - package.json
	@sed -i.bak 's/"version": ".*"/"version": "$(CURRENT_VERSION)"/' $(N8N_PACKAGE) && rm -f $(N8N_PACKAGE).bak
	@echo "  Updated: $(N8N_PACKAGE)"
	@echo ""
	@$(MAKE) check-versions --no-print-directory

# Git tagging targets
tag-all:  ## Create git tags for all components
	@echo "Creating tags for version $(CURRENT_VERSION)..."
	@$(MAKE) tag-cli tag-python tag-typescript tag-java tag-n8n --no-print-directory
	@echo ""
	@echo "Tags created. Push with: git push origin --tags"

tag-cli:  ## Create git tag for CLI release
	@echo "Creating tag: cli-v$(CURRENT_VERSION)"
	@git tag -a "cli-v$(CURRENT_VERSION)" -m "CLI release $(CURRENT_VERSION)"

tag-python:  ## Create git tag for Python release
	@echo "Creating tag: python-v$(CURRENT_VERSION)"
	@git tag -a "python-v$(CURRENT_VERSION)" -m "Python SDK release $(CURRENT_VERSION)"

tag-typescript:  ## Create git tag for TypeScript release
	@echo "Creating tag: typescript-v$(CURRENT_VERSION)"
	@git tag -a "typescript-v$(CURRENT_VERSION)" -m "TypeScript SDK release $(CURRENT_VERSION)"

tag-java:  ## Create git tag for Java release
	@echo "Creating tag: java-v$(CURRENT_VERSION)"
	@git tag -a "java-v$(CURRENT_VERSION)" -m "Java SDK release $(CURRENT_VERSION)"

tag-n8n:  ## Create git tag for n8n release
	@echo "Creating tag: n8n-v$(CURRENT_VERSION)"
	@git tag -a "n8n-v$(CURRENT_VERSION)" -m "n8n node release $(CURRENT_VERSION)"

# Development helpers
.PHONY: build-all test-all test-integration install-cli \
        lint lint-python lint-rust lint-typescript lint-java lint-n8n \
        format format-python format-rust format-typescript format-java format-n8n \
        install-hooks install-local install-dbt demo-database demo-database-stop demo-dbt demo-gdpr demo-n8n

install-local:  ## Install Python SDK locally in editable mode (for development)
	@echo "Installing Python SDK (editable, all extras)..."
	pip install -e "python/[all]"
	@echo "Python SDK installed"

install-dbt:  ## Install dbt-postgres for the demo database
	@echo "Installing dbt-postgres..."
	pip install dbt-postgres
	@echo "dbt-postgres installed"

demo-database:  ## Start the demo Jaffle Shop database (PostgreSQL + Metabase)
	@echo "Starting demo database..."
	cd cookbook/resources/demo-database/docker && docker-compose up -d
	@echo ""
	@echo "Services started:"
	@echo "  PostgreSQL: localhost:5433 (user: jaffle_user / jaffle_pass)"
	@echo "  Metabase:   localhost:3000"

demo-database-stop:  ## Stop the demo database
	@echo "Stopping demo database..."
	cd cookbook/resources/demo-database/docker && docker-compose down
	@echo "Demo database stopped"

demo-dbt:  ## Run dbt models against the demo database
	@echo "Running dbt against Jaffle Shop database..."
	cd cookbook/resources/demo-database/dbt && DBT_PROFILES_DIR=$$(pwd) dbt run
	@echo ""
	@echo "Running dbt tests..."
	cd cookbook/resources/demo-database/dbt && DBT_PROFILES_DIR=$$(pwd) dbt test
	@echo ""
	@echo "dbt models and tests completed"

demo-gdpr:  ## Start the GDPR DSAR compliance demo (bundles SDK + starts server)
	@echo "Bundling TypeScript SDK..."
	@npx esbuild typescript/src/index.ts --bundle --format=esm \
		--outfile=cookbook/gdpr-dsar-compliance/metadata-ai.js --target=es2022 --log-level=warning
	@echo "Starting server (SDK runs server-side)..."
	@node cookbook/gdpr-dsar-compliance/serve.js

demo-n8n:  ## Build n8n node and start n8n with it loaded
	@echo "Building TypeScript SDK..."
	@cd typescript && npm install --silent && npm run build
	@echo "Building n8n node..."
	@cd n8n-nodes-metadata && npm install --silent && npm run build
	@echo ""
	@echo "Starting n8n with Metadata Agent node..."
	@echo "  Open: http://localhost:5678"
	@echo ""
	@N8N_CUSTOM_EXTENSIONS=$(CURDIR)/n8n-nodes-metadata N8N_SECURE_COOKIE=false npx n8n

install-cli:  ## Build CLI (release) and install to ~/.local/bin
	@echo "Building CLI in release mode..."
	cd cli && cargo build --release
	@echo ""
	@echo "Installing to ~/.local/bin..."
	@mkdir -p ~/.local/bin
	@cp cli/target/release/metadata-ai ~/.local/bin/metadata-ai
	@chmod +x ~/.local/bin/metadata-ai
	@if [ "$$(uname)" = "Darwin" ]; then codesign --sign - --force ~/.local/bin/metadata-ai 2>/dev/null; fi
	@echo ""
	@echo "Installed: ~/.local/bin/metadata-ai"
	@echo "Version: $$(~/.local/bin/metadata-ai --version 2>/dev/null || echo 'unknown')"
	@echo ""
	@if echo "$$PATH" | grep -q "$$HOME/.local/bin"; then \
		echo "Ready to use: metadata-ai"; \
	else \
		echo "Note: Add ~/.local/bin to your PATH:"; \
		echo "  export PATH=\"\$$HOME/.local/bin:\$$PATH\""; \
	fi

build-all:  ## Build all SDKs
	@echo "Building all SDKs..."
	cd cli && cargo build
	pip install -e python/ -q
	cd typescript && npm install --silent && npm run build
	cd java && mvn package -q -DskipTests
	cd n8n-nodes-metadata && npm install --silent && npm run build
	@echo "All SDKs built successfully"

test-all:  ## Run unit tests for all SDKs
	@echo "Running unit tests for all SDKs..."
	cd cli && cargo test
	cd python && pytest -q --ignore=tests/integration
	cd typescript && npm test
	cd java && mvn test -q
	@echo "All unit tests completed"

test-integration:  ## Run integration tests (requires METADATA_HOST and METADATA_TOKEN)
	@if [ -z "$(METADATA_HOST)" ] || [ -z "$(METADATA_TOKEN)" ]; then \
		echo "Error: METADATA_HOST and METADATA_TOKEN must be set"; \
		echo "Usage: METADATA_HOST=https://... METADATA_TOKEN=... make test-integration"; \
		exit 1; \
	fi
	@echo "Running integration tests against $(METADATA_HOST)..."
	@echo ""
	@echo "=== Python SDK ==="
	cd python && pytest tests/integration/ -v --tb=short
	@echo ""
	@echo "=== TypeScript SDK ==="
	cd typescript && npm run test:integration
	@echo ""
	@echo "=== Java SDK ==="
	cd java && mvn test -Dtest=IntegrationTest -q
	@echo ""
	@echo "=== CLI ==="
	cd cli && cargo test --test integration_test
	@echo ""
	@echo "=== n8n Node ==="
	cd n8n-nodes-metadata && npm run test:integration
	@echo ""
	@echo "All integration tests completed"

# =============================================================================
# Linting
# =============================================================================

lint: lint-python lint-rust lint-typescript lint-java lint-n8n  ## Run linters for all SDKs
	@echo "All linters passed!"

lint-python:  ## Lint Python SDK
	@echo "Linting Python SDK..."
	cd python && ruff check src tests && ruff format --check src tests && ty check src

lint-rust:  ## Lint Rust CLI
	@echo "Linting Rust CLI..."
	cd cli && cargo fmt --check && cargo clippy -- -D warnings

lint-typescript:  ## Lint TypeScript SDK
	@echo "Linting TypeScript SDK..."
	cd typescript && npm run lint

lint-java:  ## Lint Java SDK
	@echo "Linting Java SDK..."
	cd java && mvn spotless:check -q

lint-n8n:  ## Lint n8n node
	@echo "Linting n8n node..."
	cd n8n-nodes-metadata && npm run lint

# =============================================================================
# Formatting
# =============================================================================

format: format-python format-rust format-typescript format-java format-n8n  ## Format all SDKs
	@echo "All SDKs formatted!"

format-python:  ## Format Python SDK
	@echo "Formatting Python SDK..."
	cd python && ruff format src tests && ruff check --fix src tests

format-rust:  ## Format Rust CLI
	@echo "Formatting Rust CLI..."
	cd cli && cargo fmt

format-typescript:  ## Format TypeScript SDK
	@echo "Formatting TypeScript SDK..."
	cd typescript && npm run lint -- --fix

format-java:  ## Format Java SDK
	@echo "Formatting Java SDK..."
	cd java && mvn spotless:apply -q

format-n8n:  ## Format n8n node
	@echo "Formatting n8n node..."
	cd n8n-nodes-metadata && npm run lint:fix

# =============================================================================
# Git Hooks
# =============================================================================

install-hooks:  ## Install git pre-commit hooks
	@echo "Installing git hooks..."
	@cp scripts/pre-commit .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "Pre-commit hook installed!"
