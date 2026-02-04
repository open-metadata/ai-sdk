# Add Test

Add unit or integration tests for existing functionality.

## Usage
```
/add-test <sdk> <component> [--integration]
```

## Test Patterns by SDK

### Python (`python/tests/`)

**Unit Test:**
```python
import pytest
from unittest.mock import AsyncMock, patch
from metadata_ai import MetadataAI

@pytest.fixture
def client():
    return MetadataAI(host="https://test.example.com", token="test-token")

@pytest.mark.asyncio
async def test_method_name(client):
    """Test description."""
    with patch.object(client._http, 'request', new_callable=AsyncMock) as mock:
        mock.return_value = {"expected": "response"}

        result = await client.agent("test").method_name("param")

        assert result.expected == "response"
        mock.assert_called_once_with("POST", "/expected/path", json={"param": "param"})
```

**Integration Test:** (`python/tests/integration/`)
```python
import pytest
import os

@pytest.fixture
def live_client():
    host = os.environ.get("METADATA_HOST")
    token = os.environ.get("METADATA_TOKEN")
    if not host or not token:
        pytest.skip("Integration test credentials not configured")
    return MetadataAI(host=host, token=token)

@pytest.mark.asyncio
async def test_real_api_call(live_client):
    """Integration test against real API."""
    result = await live_client.agent("test-agent").invoke("hello")
    assert result.response is not None
```

### TypeScript (`typescript/tests/`)

**Unit Test:**
```typescript
import { describe, it, expect, vi } from 'vitest';
import { MetadataAI } from '../src';

describe('MethodName', () => {
  it('should do expected behavior', async () => {
    const client = new MetadataAI({ host: 'https://test.example.com', token: 'test' });

    // Mock fetch
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ expected: 'response' }),
    });

    const result = await client.agent('test').methodName('param');

    expect(result.expected).toBe('response');
    expect(fetch).toHaveBeenCalledWith(
      'https://test.example.com/expected/path',
      expect.objectContaining({ method: 'POST' })
    );
  });
});
```

### Java (`java/src/test/java/io/metadata/ai/`)

**Unit Test:**
```java
package io.metadata.ai;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class MethodNameTest {
    private MetadataAI client;
    private MetadataHttpClient mockHttp;

    @BeforeEach
    void setUp() {
        mockHttp = mock(MetadataHttpClient.class);
        client = new MetadataAI.Builder()
            .host("https://test.example.com")
            .token("test-token")
            .httpClient(mockHttp)
            .build();
    }

    @Test
    void testMethodName() throws Exception {
        when(mockHttp.post(anyString(), any())).thenReturn(new ResponseModel("expected"));

        ResponseModel result = client.agent("test").methodName("param");

        assertEquals("expected", result.getValue());
        verify(mockHttp).post("/expected/path", any());
    }
}
```

### Rust (`cli/src/` or `cli/tests/`)

**Unit Test:**
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_method_name() {
        let result = method_name("input");
        assert_eq!(result, expected_output);
    }

    #[tokio::test]
    async fn test_async_method() {
        let client = TestClient::new();
        let result = client.method_name("param").await.unwrap();
        assert_eq!(result.field, "expected");
    }
}
```

## Test Naming Conventions

| SDK | Convention | Example |
|-----|------------|---------|
| Python | `test_<method>_<scenario>` | `test_invoke_returns_response` |
| TypeScript | `should <behavior>` | `should return response on success` |
| Java | `test<Method><Scenario>` | `testInvokeReturnsResponse` |
| Rust | `test_<method>_<scenario>` | `test_invoke_returns_response` |

## Checklist

- [ ] Test covers the happy path
- [ ] Test covers error cases (400, 401, 404, 500)
- [ ] Test covers edge cases (empty input, null values)
- [ ] Mocks are used for unit tests (no real API calls)
- [ ] Integration tests skip gracefully when credentials missing
- [ ] Test names clearly describe what's being tested

## Run Tests

```bash
# All unit tests
make test-all

# Specific SDK
cd python && pytest tests/ -v
cd typescript && npm test
cd java && mvn test
cd cli && cargo test

# With coverage
cd python && pytest --cov=src/metadata_ai tests/
cd typescript && npm test -- --coverage
cd java && mvn test jacoco:report
```
