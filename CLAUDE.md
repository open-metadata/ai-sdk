# CLAUDE.md - Metadata AI SDK

This repository contains SDKs and CLI for invoking Metadata Dynamic Agents.

## Repository Structure

```
metadata-ai-sdk/
├── cli/                    # Rust CLI (ai-sdk)
├── python/                 # Python SDK (ai-sdk on PyPI)
│   ├── src/ai_sdk/    # Source code
│   ├── tests/              # Unit and integration tests
│   └── pyproject.toml      # Package config
├── typescript/             # TypeScript SDK (@openmetadata/ai-sdk on npm)
├── java/                   # Java SDK (io.openmetadata:ai-sdk)
├── n8n-nodes-metadata/     # n8n community node (depends on TypeScript SDK)
├── cookbook/                # Guides, scripts, and resources for common use cases
│   └── resources/
│       └── demo-database/  # Jaffle Shop demo (PostgreSQL + Metabase + dbt)
│           ├── docker/     # docker-compose.yml, Dockerfile, init.sql
│           └── dbt/        # dbt project (models, profiles, tests)
├── scripts/                # Development scripts (pre-commit hooks)
├── .claude/skills/         # Claude Code skills for this repo
├── VERSION                 # Single source of truth for version
└── Makefile                # Cross-SDK commands (single source of truth)
```

## Quick Commands

```bash
# Linting & Formatting
make lint              # Check all SDKs (CI equivalent)
make format            # Fix all SDKs (pre-commit equivalent)

# Testing
make test-all          # Run all unit tests
make test-integration  # Run integration tests (requires METADATA_HOST, METADATA_TOKEN)

# Building
make build-all         # Build all SDKs

# Version Management
make version           # Show current version
make bump-version V=X.Y.Z  # Update all SDKs

# Local Development
make install-local       # Install Python SDK in editable mode (all extras)

# Demo Database
make install-dbt         # Install dbt-postgres for the demo
make demo-database       # Start PostgreSQL (port 5433) + Metabase (port 3000)
make demo-database-stop  # Stop demo database containers
make demo-dbt            # Run dbt models and tests against the demo database
make demo-gdpr           # Start the GDPR DSAR compliance demo (port 8080)

# Git Hooks
make install-hooks     # Install pre-commit hooks
```

## Architecture

### Design Principles

1. **Multi-SDK Consistency** - All SDKs implement the same API surface with language-idiomatic patterns
2. **Zero/Minimal Dependencies** - TypeScript has zero runtime deps; others minimize external deps
3. **Streaming First** - SSE streaming is a primary use case, not an afterthought
4. **Typed Errors** - Structured error hierarchy for proper error handling

### API Pattern (All SDKs)

```
client = MetadataAI(host, token)
response = client.agent("agent-name").invoke("message")

# Streaming
for event in client.agent("agent-name").stream("message"):
    handle(event)
```

### Event Types (Streaming)
- `message` - Partial response content
- `tool_call` - Agent calling a tool
- `tool_result` - Tool result
- `error` - Error occurred
- `done` - Stream complete

### Error Hierarchy
```
MetadataError (base)
├── AuthenticationError (401)
├── AuthorizationError (403)
├── NotFoundError (404)
├── ValidationError (400)
├── RateLimitError (429)
└── ServerError (5xx)
```

## SDK Development

### Naming Conventions

| Concept | Python | TypeScript | Java | Rust |
|---------|--------|------------|------|------|
| Methods | `snake_case` | `camelCase` | `camelCase` | `snake_case` |
| Classes | `PascalCase` | `PascalCase` | `PascalCase` | `PascalCase` |
| Files | `snake_case.py` | `camelCase.ts` | `PascalCase.java` | `snake_case.rs` |

### Adding a New Method

When adding functionality, update ALL SDKs:

1. **Python** (`python/src/ai_sdk/`)
   - Add to `_client.py` or `_agent.py`
   - Add types to models
   - Add tests in `python/tests/`

2. **TypeScript** (`typescript/src/`)
   - Add to `agent.ts`
   - Add interfaces to `models.ts`
   - Add tests in `typescript/tests/`

3. **Java** (`java/src/main/java/io/metadata/ai/`)
   - Add to `AgentHandle.java`
   - Add model classes in `models/`
   - Add tests in `java/src/test/`

4. **Rust CLI** (`cli/src/`)
   - Add subcommand in `main.rs`
   - Add tests

5. **Verify**
   ```bash
   make lint && make test-all
   ```

### Testing

**Unit Tests** - Mock HTTP responses, no real API calls:
```bash
cd python && pytest --ignore=tests/integration
cd typescript && npm test
cd java && mvn test -DexcludedGroups=integration
cd cli && cargo test --lib
```

**Integration Tests** - Real API calls (requires credentials):
```bash
export METADATA_HOST=https://your-instance.getcollate.io
export METADATA_TOKEN=your-jwt-token
export METADATA_TEST_AGENT=agent-name  # optional

make test-integration
```

## Code Quality

### Linting Tools

| SDK | Formatter | Linter | Type Checker |
|-----|-----------|--------|--------------|
| Python | `ruff format` | `ruff check` | `ty` |
| Rust | `cargo fmt` | `cargo clippy` | (built-in) |
| TypeScript | ESLint | ESLint | `tsc` |
| Java | Spotless | Spotless | `javac` |

### Pre-commit Hook

Install with `make install-hooks`. Runs on staged files:
1. Detects which SDKs have changes
2. Runs formatter (auto-fixes)
3. Runs linter
4. Runs type checker (Python)
5. Re-stages fixed files

### CI Pipeline

Every PR runs:
- Linting (format check + lint + types)
- Unit tests with coverage
- Security scanning (CodeQL, dependency audit)

## Available Skills

Use these with `/skill-name` in Claude Code:

- `/add-sdk-method` - Add a method across all SDKs
- `/add-test` - Add unit or integration tests
- `/run-integration` - Run integration tests
- `/debug-ci` - Diagnose CI failures
- `/validate-docs` - Validate documentation for clarity and completeness

## Demo Database (Jaffle Shop)

A local PostgreSQL + Metabase + dbt setup at `cookbook/resources/demo-database/` for testing cookbook features (DQ, lineage, PII classification, etc.).

### Setup

```bash
# 1. Start containers (requires Docker)
make demo-database

# 2. Run dbt models (requires dbt-postgres: pip install dbt-postgres)
make demo-dbt
```

### Connection Details

| Service    | Host      | Port | User                | Password            |
|------------|-----------|------|---------------------|---------------------|
| PostgreSQL | localhost | 5433 | `jaffle_user`       | `jaffle_pass`       |
| PostgreSQL | localhost | 5433 | `openmetadata_user` | `openmetadata_pass` |
| Metabase   | localhost | 3000 | `admin@jaffle.shop` | `JaffleAdmin123!`   |

**Port 5433** is used intentionally to avoid conflicts with a local PostgreSQL on the default 5432.

### Key Files

- `docker/docker-compose.yml` — PostgreSQL (port 5433) and Metabase services
- `docker/init.sql` — Schema creation, seed data, analytics views, user grants
- `dbt/profiles.yml` — dbt connection profile (points to localhost:5433)
- `dbt/models/` — staging, intermediate, and marts models

### Teardown

```bash
make demo-database-stop            # Stop containers
# To also remove data volumes:
cd cookbook/resources/demo-database/docker && docker-compose down -v
```

## Key Architecture Decisions

**Why multiple SDKs in one repo?**
- Users work in different languages (Python for data engineers, TypeScript for web, Java for enterprise)
- Single repo ensures version consistency and coordinated releases
- Every feature must be implemented in ALL SDKs - no partial implementations

**Why zero runtime dependencies (TypeScript)?**
- Minimal bundle size (~10KB)
- Works everywhere: Node.js 18+, browsers, Deno, Bun, edge runtimes
- No dependency vulnerabilities to track
- Native `fetch` API is sufficient; SSE parsing is simple enough to implement

**Why SSE streaming over WebSockets?**
- Simpler protocol, one-way communication is sufficient
- Better HTTP/2 support
- Each SDK exposes streaming idiomatically: async generators (Python), async iterators (TypeScript), callbacks/streams (Java)

**Why typed error hierarchy?**
- Users can catch specific errors (AuthenticationError vs NotFoundError)
- Enables proper error handling (refresh token on 401, retry on 429)
- Consistent across all SDKs

**Why single VERSION file?**
- One source of truth prevents version drift
- `make bump-version V=X.Y.Z` updates all SDKs atomically
- CI validates all versions match

## MANDATORY Skills

- **Python files**: You MUST invoke `/dignified-python` before writing, reviewing, or refactoring ANY Python file (`.py`). This is non-negotiable — no Python code changes without loading the skill first.

## DO NOT

- Edit files in `python/src/ai_sdk/generated/` (auto-generated)
- Change version numbers manually (use `make bump-version`)
- Add a method to only one SDK (all must be updated)
- Add dependencies without strong justification
- Skip tests for new functionality
- Use different naming conventions than established patterns
- Commit without running `make lint`

## Common Issues

| Issue | Solution |
|-------|----------|
| Pre-commit fails | Run `make format` then commit |
| Type errors (Python) | Check type annotations, run `ty check src` |
| Import errors | Check `__init__.py` exports |
| n8n build fails | Build TypeScript SDK first: `cd typescript && npm run build` |
| Integration tests skip | Set `METADATA_HOST` and `METADATA_TOKEN` env vars |
