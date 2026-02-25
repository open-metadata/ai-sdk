.DEFAULT_GOAL := help

.PHONY: help
help:
	@grep -EH '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":"}; {split($$0, a, "## "); printf "\033[35m%-20s\033[0m %s\n", $$2, a[2]}'

.PHONY: install
install: ## Install npm dependencies
	npm install

.PHONY: build
build: ## Build the node (compile TypeScript + copy icons)
	npm run build

.PHONY: dev
dev: ## Watch mode for development
	npm run dev

.PHONY: run
run: ## Start n8n with the custom node loaded
	N8N_CUSTOM_EXTENSIONS="$$(pwd)" N8N_SECURE_COOKIE=false npx n8n

.PHONY: clean
clean: ## Remove build artifacts
	rm -rf dist/
