# Metadata AI SDK

SDKs and CLI for invoking Metadata Dynamic Agents from your AI applications.

## Components

| Component | Language | Package | Status |
|-----------|----------|---------|--------|
| CLI | Rust | `metadata-ai` | ✅ Ready |
| Python SDK | Python | `metadata-ai` | ✅ Ready |
| TypeScript SDK | TypeScript | `@openmetadata/ai-sdk` | ✅ Ready |
| Java SDK | Java | `io.openmetadata:metadata-ai-sdk` | ✅ Ready |
| n8n Integration | TypeScript | `n8n-nodes-metadata` | ✅ Ready |

## Quick Start

### CLI

```bash
# Install
curl -sSL https://open-metadata.org/cli | sh

# Configure
metadata-ai configure

# Invoke an agent
metadata-ai invoke DataQualityPlannerAgent "Analyze the customers table"
```

### Python

```bash
pip install metadata-ai
```

```python
from metadata_ai import MetadataAI

client = MetadataAI(
    host="https://your-metadata-instance.com",
    token="your-bot-jwt-token"
)

response = client.agent("DataQualityPlannerAgent").call(
    "What data quality tests should I add for the customers table?"
)
print(response.response)
```

### TypeScript

```bash
npm install @openmetadata/ai-sdk
```

```typescript
import { MetadataAI } from '@openmetadata/ai-sdk';

const client = new MetadataAI({
  host: 'https://your-metadata-instance.com',
  token: 'your-bot-jwt-token'
});

const response = await client.agent('DataQualityPlannerAgent').call(
  'What data quality tests should I add for the customers table?'
);
console.log(response.response);
```

### Java

```xml
<dependency>
  <groupId>io.openmetadata</groupId>
  <artifactId>metadata-ai-sdk</artifactId>
  <version>0.1.0</version>
</dependency>
```

```java
import io.openmetadata.ai.MetadataAI;

MetadataAI client = new MetadataAI.Builder()
    .host("https://your-metadata-instance.com")
    .token("your-bot-jwt-token")
    .build();

InvokeResponse response = client.agent("DataQualityPlannerAgent")
    .call("What data quality tests should I add?");
System.out.println(response.getResponse());
```

## Features

All SDKs support:

- **Synchronous invocation** - Simple request/response pattern
- **Streaming responses** - Real-time token streaming with SSE
- **Multi-turn conversations** - Maintain context across messages
- **Async support** - Native async/await (Python, TypeScript)
- **Error handling** - Typed exceptions for common errors
- **Retry logic** - Automatic retries with exponential backoff

## Documentation

- [Python SDK](python/README.md)
- [TypeScript SDK](typescript/README.md)
- [Java SDK](java/README.md)
- [CLI](cli/README.md)
- [n8n Integration](n8n-nodes-metadata/README.md)

## Version Management

All components share a version number in the `VERSION` file. Use the Makefile to manage versions:

```bash
make version          # Show current version
make check-versions   # Validate all versions match
make bump-version V=0.2.0  # Update all SDKs
```

## Releasing

Creating a GitHub Release triggers CI to publish all SDKs automatically.

### Release Flow

```bash
# 1. Bump version across all SDKs
make bump-version V=0.2.0

# 2. Commit and push
git add -A && git commit -m "Bump version to 0.2.0"
git push

# 3. Create a GitHub Release (triggers CI)
make release
```

`make release` uses `gh release create` to create a release with tag `v0.2.0`. This triggers the release workflow which publishes all SDKs in parallel:

| SDK | Target | Workflow |
|-----|--------|----------|
| Python | PyPI (`metadata-ai`) | `ai-sdk-release-python.yml` |
| TypeScript | npm (`@openmetadata/ai-sdk`) | `ai-sdk-release-typescript.yml` |
| Java | Maven Central (`io.openmetadata:metadata-ai-sdk`) | `ai-sdk-release-java.yml` |
| CLI | GitHub Release binaries | `ai-sdk-release-cli.yml` |

### Individual SDK Releases

To release a single SDK (e.g., for a hotfix), push an SDK-specific tag:

```bash
make tag-python    # Creates python-v0.2.0 tag
git push origin python-v0.2.0
```

### Required Secrets

The Java secrets are reused from the `open-metadata/OpenMetadata` org. Only `NPM_TOKEN` needs to be created.

| Secret | Used By | Description |
|--------|---------|-------------|
| `NPM_TOKEN` | TypeScript | npm access token with publish permission for `@openmetadata/ai-sdk` |
| `OSSRH_USERNAME` | Java | Sonatype OSSRH username (org secret) |
| `OSSRH_TOKEN` | Java | Sonatype OSSRH token (org secret) |
| `OSSRH_GPG_SECRET_KEY` | Java | GPG private key for signing (org secret) |
| `OSSRH_GPG_SECRET_KEY_PASSWORD` | Java | GPG key passphrase (org secret) |
| `MAVEN_MASTER_PASSWORD` | Java | Maven master password for settings-security.xml (org secret) |

`GITHUB_TOKEN` is provided automatically by GitHub Actions for CLI binary uploads.

### Required Environment

Create a GitHub environment named **`publish`** (**Settings → Environments → New environment**):

- Optionally add **required reviewers** for release approval
- The Python SDK uses **PyPI trusted publishing** (OIDC). Configure the trusted publisher on [pypi.org](https://pypi.org):
  - Repository: `open-metadata/metadata-ai-sdk`
  - Workflow: `ai-sdk-release-python.yml`
  - Environment: `publish`

### CLI Install Path

The CLI is distributed as pre-built binaries attached to GitHub Releases. Users install via:

```bash
# Automatic installer (recommended)
curl -sSL https://open-metadata.org/cli | sh

# Or download manually from the releases page
# https://github.com/open-metadata/metadata-ai-sdk/releases
```

The installer downloads the binary to `~/.local/bin/metadata-ai` (falls back to `/usr/local/bin/`).

## Development

```bash
# Build all SDKs
make build-all

# Run unit tests
make test-all

# Run integration tests (requires credentials)
METADATA_HOST=https://... METADATA_TOKEN=... make test-integration
```

## License

Collate Community License 1.0
