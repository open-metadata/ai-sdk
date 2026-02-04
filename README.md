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
