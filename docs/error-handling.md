# Error Handling

This guide covers error handling patterns for the Metadata AI SDK.

## Exception Hierarchy

The SDK provides a structured exception hierarchy:

```
MetadataError (base)
├── AuthenticationError (401)
├── AgentNotFoundError (404)
├── AgentNotEnabledError (403)
├── RateLimitError (429)
└── AgentExecutionError (500)
```

## Import Exceptions

```python
from ai_sdk.exceptions import (
    MetadataError,
    AuthenticationError,
    AgentNotFoundError,
    AgentNotEnabledError,
    RateLimitError,
    AgentExecutionError,
)
```

## Exception Details

### AuthenticationError

Raised when the JWT token is invalid or expired.

```python
try:
    response = client.agent("MyAgent").call("Hello")
except AuthenticationError:
    print("Invalid or expired token")
    # Action: Check METADATA_TOKEN, regenerate bot token
```

**Status Code**: 401

### AgentNotFoundError

Raised when the requested agent doesn't exist.

```python
try:
    response = client.agent("NonExistent").call("Hello")
except AgentNotFoundError as e:
    print(f"Agent not found: {e.agent_name}")
    # Action: Check agent name spelling, verify agent exists
```

**Status Code**: 404
**Properties**: `agent_name`

### AgentNotEnabledError

Raised when the agent exists but isn't enabled for API access.

```python
try:
    response = client.agent("PrivateAgent").call("Hello")
except AgentNotEnabledError as e:
    print(f"Agent '{e.agent_name}' is not API-enabled")
    # Action: Enable API access in AI Studio
```

**Status Code**: 403
**Properties**: `agent_name`

### RateLimitError

Raised when API rate limits are exceeded.

```python
import time

try:
    response = client.agent("MyAgent").call("Hello")
except RateLimitError as e:
    print(f"Rate limited")
    if e.retry_after:
        print(f"Retry after: {e.retry_after} seconds")
        time.sleep(e.retry_after)
```

**Status Code**: 429
**Properties**: `retry_after` (seconds, may be `None`)

### AgentExecutionError

Raised when the agent fails during execution.

```python
try:
    response = client.agent("MyAgent").call("Hello")
except AgentExecutionError as e:
    print(f"Agent failed: {e.message}")
    if e.agent_name:
        print(f"Agent: {e.agent_name}")
```

**Status Code**: 500
**Properties**: `agent_name` (may be `None`), `message`

### MetadataError (Base)

Base class for all SDK exceptions.

```python
try:
    response = client.agent("MyAgent").call("Hello")
except MetadataError as e:
    print(f"Error ({e.status_code}): {e.message}")
```

**Properties**: `message`, `status_code`

## Error Handling Patterns

### Basic Pattern

```python
from ai_sdk import MetadataAI
from ai_sdk.exceptions import (
    AuthenticationError,
    AgentNotFoundError,
    AgentNotEnabledError,
    RateLimitError,
    AgentExecutionError,
    MetadataError,
)

def invoke_agent(client: MetadataAI, agent_name: str, message: str) -> str:
    try:
        response = client.agent(agent_name).call(message)
        return response.response

    except AuthenticationError:
        raise SystemExit("Authentication failed. Check your token.")

    except AgentNotFoundError as e:
        raise ValueError(f"Unknown agent: {e.agent_name}")

    except AgentNotEnabledError as e:
        raise ValueError(f"Agent not enabled: {e.agent_name}")

    except RateLimitError as e:
        raise RuntimeError(f"Rate limited. Retry after {e.retry_after}s")

    except AgentExecutionError as e:
        raise RuntimeError(f"Agent failed: {e.message}")
```

### With Retry Logic

```python
import time
from typing import TypeVar

T = TypeVar("T")

def with_retry(
    func: callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> T:
    """Execute function with automatic retry for rate limits."""
    last_error = None

    for attempt in range(max_retries):
        try:
            return func()

        except RateLimitError as e:
            last_error = e
            delay = e.retry_after or (base_delay * (2 ** attempt))
            print(f"Rate limited, waiting {delay}s...")
            time.sleep(delay)

        except AgentExecutionError as e:
            last_error = e
            delay = base_delay * (2 ** attempt)
            print(f"Agent error, retrying in {delay}s...")
            time.sleep(delay)

    raise last_error

# Usage
response = with_retry(
    lambda: client.agent("MyAgent").call("Hello")
)
```

### Graceful Degradation

```python
def safe_invoke(
    client: MetadataAI,
    agent_name: str,
    message: str,
    fallback: str = "Unable to process request",
) -> str:
    """Invoke agent with graceful fallback."""
    try:
        return client.agent(agent_name).call(message).response

    except (AgentNotFoundError, AgentNotEnabledError) as e:
        print(f"Agent unavailable: {e}")
        return fallback

    except AgentExecutionError as e:
        print(f"Agent error: {e.message}")
        return fallback

    except MetadataError as e:
        print(f"SDK error: {e}")
        return fallback
```

### Async Error Handling

```python
import asyncio

async def async_invoke(
    client: MetadataAI,
    agent_name: str,
    message: str,
) -> str:
    try:
        response = await client.agent(agent_name).acall(message)
        return response.response

    except RateLimitError as e:
        if e.retry_after:
            await asyncio.sleep(e.retry_after)
            response = await client.agent(agent_name).acall(message)
            return response.response
        raise
```

### Logging Errors

```python
import logging

logger = logging.getLogger(__name__)

def logged_invoke(client: MetadataAI, agent_name: str, message: str) -> str:
    try:
        response = client.agent(agent_name).call(message)
        logger.info("Agent %s invoked successfully", agent_name)
        return response.response

    except AuthenticationError:
        logger.error("Authentication failed - check token")
        raise

    except AgentNotFoundError as e:
        logger.warning("Agent not found: %s", e.agent_name)
        raise

    except MetadataError as e:
        logger.error(
            "Metadata error (status=%s): %s",
            e.status_code,
            e.message,
        )
        raise
```

## Streaming Error Handling

Errors during streaming raise exceptions when encountered:

```python
try:
    for event in agent.stream("Generate something"):
        if event.type == "error":
            print(f"Stream error: {event.error}")
            break
        if event.type == "content":
            print(event.content, end="")

except AgentExecutionError as e:
    print(f"Stream failed: {e.message}")
```

## Validation Errors

Input validation happens at initialization:

```python
from ai_sdk.auth import TokenAuth
from ai_sdk import MetadataConfig

# Token validation
try:
    auth = TokenAuth("")  # Empty token
except ValueError as e:
    print(f"Invalid token: {e}")

# Config validation
try:
    config = MetadataConfig(host="", token="valid")
except ValueError as e:
    print(f"Invalid config: {e}")

# Environment validation
try:
    config = MetadataConfig.from_env()  # Missing env vars
except ValueError as e:
    print(f"Missing environment: {e}")
```

## Best Practices

1. **Handle specific exceptions** - Don't catch generic `Exception`
2. **Log errors** - Include context for debugging
3. **Implement retry logic** - For rate limits and transient errors
4. **Provide fallbacks** - Graceful degradation when possible
5. **Validate early** - Check config before making calls
6. **Clean up resources** - Use context managers or try/finally
