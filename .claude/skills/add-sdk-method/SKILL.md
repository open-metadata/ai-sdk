---
name: add-sdk-method
description: Use when adding a new method, function, or API endpoint to the SDK.
  Ensures consistent implementation across all SDKs (Python, TypeScript, Java, Rust CLI)
  with proper types, tests, and naming conventions.
---

# Add SDK Method

Adds a new method to all SDKs (Python, TypeScript, Java, Rust CLI) with consistent implementation.

## Usage
```
/add-sdk-method <method-name> <description>
```

## Checklist

1. **Understand the Method**
   - [ ] Clarify the method signature (parameters, return type)
   - [ ] Clarify the HTTP endpoint it calls (GET/POST/etc, path, body)
   - [ ] Clarify error handling requirements

2. **Python SDK** (`python/src/ai_sdk/`)
   - [ ] Add method to appropriate class (likely `AgentHandle` in `_client.py`)
   - [ ] Add type hints using Pydantic models
   - [ ] Add async version if sync version exists (or vice versa)
   - [ ] Add unit test in `python/tests/`

3. **TypeScript SDK** (`typescript/src/`)
   - [ ] Add method to `AgentHandle` class in `agent.ts`
   - [ ] Add TypeScript interfaces to `models.ts` if needed
   - [ ] Add unit test in `typescript/tests/`

4. **Java SDK** (`java/src/main/java/io/metadata/ai/`)
   - [ ] Add method to `AgentHandle.java`
   - [ ] Add model classes in `models/` if needed
   - [ ] Add unit test in `java/src/test/`

5. **Rust CLI** (`cli/src/`)
   - [ ] Add subcommand or option to handle the new functionality
   - [ ] Update `main.rs` or relevant module
   - [ ] Add unit test

6. **Verify**
   - [ ] Run `make lint` - all linters pass
   - [ ] Run `make test-all` - all unit tests pass
   - [ ] Update CHANGELOG if exists

## Patterns to Follow

### Python
```python
async def new_method(self, param: str) -> ResponseModel:
    """Short description.

    Args:
        param: Description of param

    Returns:
        ResponseModel with the result
    """
    response = await self._client._request("POST", f"/path/{param}")
    return ResponseModel.model_validate(response)
```

### TypeScript
```typescript
async newMethod(param: string): Promise<ResponseModel> {
  const response = await this.client.request('POST', `/path/${param}`);
  return response as ResponseModel;
}
```

### Java
```java
public ResponseModel newMethod(String param) throws AISdkException {
    return httpClient.post("/path/" + param, ResponseModel.class);
}
```

## DO NOT
- Add method to only some SDKs (all must be updated)
- Skip tests
- Use different naming conventions across SDKs (camelCase in TS/Java, snake_case in Python/Rust)
- Add dependencies without justification
