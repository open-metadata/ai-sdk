# CLAUDE.md - Metadata AI SDK

This repository contains SDKs and CLI for invoking Metadata Dynamic Agents.

## Repository Structure

```
metadata-ai-sdk/
├── cli/                    # Rust CLI (metadata-ai)
├── python/                 # Python SDK (metadata-ai on PyPI) - NOTE: in root as pyproject.toml
├── typescript/             # TypeScript SDK (@openmetadata/ai-sdk on npm)
├── java/                   # Java SDK (io.openmetadata:metadata-ai-sdk)
├── n8n-nodes-metadata/     # n8n community node
├── VERSION                 # Single source of truth for version
├── Makefile                # Version management across all SDKs
└── pyproject.toml          # Python SDK config (at root level)
```

## Version Management

All SDKs share a single version from the `VERSION` file:

```bash
make version          # Show current version
make check-versions   # Verify all SDKs have same version
make bump-version V=0.2.0  # Update all SDKs to new version
```

## Building

```bash
# Build all SDKs
make build-all

# Build individual components
cd cli && cargo build
pip install -e .
cd typescript && npm install && npm run build
cd java && mvn package -DskipTests
cd n8n-nodes-metadata && npm install && npm run build
```

## Testing

```bash
# Unit tests
make test-all

# Integration tests (requires credentials)
METADATA_HOST=https://... METADATA_TOKEN=... make test-integration
```

## SDK-Specific Development

### CLI (Rust)
- Entry point: `cli/src/main.rs`
- Config location: `~/.metadata/`
- Binary name: `metadata-ai`

### Python SDK
- Package: `metadata_ai`
- Main class: `MetadataAI`
- Config class: `MetadataConfig`
- pyproject.toml at repository root

### TypeScript SDK
- Package: `@openmetadata/ai-sdk`
- Main class: `MetadataAI`
- Located in `typescript/`

### Java SDK
- Package: `io.openmetadata.ai`
- Main class: `MetadataAI`
- Located in `java/`

### n8n Integration
- Package: `n8n-nodes-metadata`
- Node: `MetadataAgent`
- Credential: `MetadataApi`
- Located in `n8n-nodes-metadata/`

## DO NOT

- Edit files in `src/metadata_ai/generated/` (auto-generated from JSON schemas)
- Change version numbers manually (use `make bump-version`)
- Mix up package naming conventions between SDKs
