---
name: run-integration
description: Use when running integration tests against a real Metadata instance.
  Guides setup of environment variables (METADATA_HOST, METADATA_TOKEN) and runs
  tests that make actual API calls.
---

# Run Integration Tests

Runs integration tests against a real Metadata instance. These tests use actual API calls.

## Usage
```
/run-integration [sdk]
```

Where `[sdk]` is optional: `python`, `typescript`, `java`, `cli`, `n8n`, or `all` (default).

## Prerequisites

Integration tests require environment variables:
- `METADATA_HOST` - Base URL of the Metadata instance (e.g., `https://your-instance.getcollate.io`)
- `METADATA_TOKEN` - Valid JWT token for authentication
- `METADATA_TEST_AGENT` - (Optional) Name of agent to test with

## Commands

### Run All Integration Tests
```bash
METADATA_HOST=https://... METADATA_TOKEN=... make test-integration
```

### Run Individual SDK Tests

**Python:**
```bash
cd python && METADATA_HOST=... METADATA_TOKEN=... pytest tests/integration/ -v
```

**TypeScript:**
```bash
cd typescript && METADATA_HOST=... METADATA_TOKEN=... npm run test:integration
```

**Java:**
```bash
cd java && METADATA_HOST=... METADATA_TOKEN=... mvn test -Dtest=IntegrationTest
```

**Rust CLI:**
```bash
cd cli && METADATA_HOST=... METADATA_TOKEN=... cargo test --test integration_test
```

**n8n:**
```bash
cd n8n-nodes-metadata && METADATA_HOST=... METADATA_TOKEN=... npm run test:integration
```

## What Integration Tests Verify

1. **Authentication** - Token is valid and accepted
2. **Agent Discovery** - Can list available agents
3. **Agent Invocation** - Can invoke an agent and get response
4. **Streaming** - SSE streaming works correctly (if `METADATA_RUN_CHAT_TESTS=true`)
5. **Error Handling** - Proper errors for invalid requests

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| 401 Unauthorized | Invalid/expired token | Get fresh token from Metadata UI |
| 404 Not Found | Agent doesn't exist | Check `METADATA_TEST_AGENT` value |
| Connection refused | Wrong host URL | Verify `METADATA_HOST` |
| Timeout | Network/firewall issue | Check connectivity |

## Notes

- Integration tests are **skipped in CI** unless secrets are configured
- Tests use real AI tokens when `METADATA_RUN_CHAT_TESTS=true`
- Always test locally before pushing changes that affect API calls
