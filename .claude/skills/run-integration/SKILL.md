---
name: run-integration
description: Use when running integration tests against a real Metadata instance.
  Guides setup of environment variables (AI_SDK_HOST, AI_SDK_TOKEN) and runs
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
- `AI_SDK_HOST` - Base URL of the Metadata instance (e.g., `https://your-instance.getcollate.io`)
- `AI_SDK_TOKEN` - Valid JWT token for authentication
- `AI_SDK_TEST_AGENT` - (Optional) Name of agent to test with

## Commands

### Run All Integration Tests
```bash
AI_SDK_HOST=https://... AI_SDK_TOKEN=... make test-integration
```

### Run Individual SDK Tests

**Python:**
```bash
cd python && AI_SDK_HOST=... AI_SDK_TOKEN=... pytest tests/integration/ -v
```

**TypeScript:**
```bash
cd typescript && AI_SDK_HOST=... AI_SDK_TOKEN=... npm run test:integration
```

**Java:**
```bash
cd java && AI_SDK_HOST=... AI_SDK_TOKEN=... mvn test -Dtest=IntegrationTest
```

**Rust CLI:**
```bash
cd cli && AI_SDK_HOST=... AI_SDK_TOKEN=... cargo test --test integration_test
```

**n8n:**
```bash
cd n8n-nodes-metadata && AI_SDK_HOST=... AI_SDK_TOKEN=... npm run test:integration
```

## What Integration Tests Verify

1. **Authentication** - Token is valid and accepted
2. **Agent Discovery** - Can list available agents
3. **Agent Invocation** - Can invoke an agent and get response
4. **Streaming** - SSE streaming works correctly (if `AI_SDK_RUN_CHAT_TESTS=true`)
5. **Error Handling** - Proper errors for invalid requests

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| 401 Unauthorized | Invalid/expired token | Get fresh token from Metadata UI |
| 404 Not Found | Agent doesn't exist | Check `AI_SDK_TEST_AGENT` value |
| Connection refused | Wrong host URL | Verify `AI_SDK_HOST` |
| Timeout | Network/firewall issue | Check connectivity |

## Notes

- Integration tests are **skipped in CI** unless secrets are configured
- Tests use real AI tokens when `AI_SDK_RUN_CHAT_TESTS=true`
- Always test locally before pushing changes that affect API calls
