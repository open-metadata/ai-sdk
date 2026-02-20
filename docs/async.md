# Async Usage Guide

This guide covers async patterns for the AI SDK.

**Prerequisites:** You need `AI_SDK_HOST` and `AI_SDK_TOKEN` configured. See [Getting Your Credentials](README.md#getting-your-credentials) if you haven't set these up.

## Enabling Async

Async must be explicitly enabled when creating the client:

```python
from ai_sdk import AiSdk

client = AiSdk(
    host="https://metadata.example.com",
    token="your-token",
    enable_async=True  # Required for async operations
)
```

Or via configuration:

```python
from ai_sdk import AiSdk, AiSdkConfig

config = AiSdkConfig.from_env(enable_async=True)
client = AiSdk.from_config(config)
```

## Async Methods

All sync methods have async counterparts:

| Sync | Async |
|------|-------|
| `client.list_agents()` | `await client.alist_agents()` |
| `agent.call()` | `await agent.acall()` |
| `agent.stream()` | `await agent.astream()` |
| `agent.get_info()` | `await agent.aget_info()` |
| `client.close()` | `await client.aclose()` |
| `conv.send()` | `await conv.asend()` |
| `conv.stream()` | `await conv.astream()` |

## Basic Async Example

```python
import asyncio
from ai_sdk import AiSdk, AiSdkConfig

async def main():
    config = AiSdkConfig.from_env(enable_async=True)
    client = AiSdk.from_config(config)

    try:
        # Async agent call
        agent = client.agent("DataQualityPlannerAgent")
        response = await agent.acall("Analyze the customers table")
        print(response.response)

    finally:
        await client.aclose()
        client.close()

asyncio.run(main())
```

## Async Context Manager

```python
async def main():
    async with AiSdk(
        host="https://metadata.example.com",
        token="your-token",
        enable_async=True
    ) as client:
        response = await client.agent("MyAgent").acall("Hello")
        print(response.response)
    # Client automatically closed
```

## Concurrent Requests

Make multiple agent calls concurrently:

```python
async def analyze_tables(client: AiSdk, tables: list[str]) -> dict[str, str]:
    """Analyze multiple tables concurrently."""
    agent = client.agent("DataQualityPlannerAgent")

    async def analyze_one(table: str) -> tuple[str, str]:
        response = await agent.acall(f"Analyze the {table} table")
        return table, response.response

    # Run all analyses concurrently
    results = await asyncio.gather(*[
        analyze_one(table) for table in tables
    ])

    return dict(results)

# Usage
async def main():
    client = AiSdk(host="...", token="...", enable_async=True)

    results = await analyze_tables(client, [
        "customers",
        "orders",
        "products",
        "inventory",
    ])

    for table, analysis in results.items():
        print(f"=== {table} ===")
        print(analysis[:200])

    await client.aclose()
```

## Async Streaming

```python
async def stream_response(client: AiSdk, message: str):
    agent = client.agent("SqlQueryAgent")

    async for event in await agent.astream(message):
        match event.type:
            case "start":
                print("Started...")
            case "content":
                print(event.content, end="", flush=True)
            case "tool_use":
                print(f"\n[Tool: {event.tool_name}]")
            case "end":
                print("\nDone!")
            case "error":
                print(f"\nError: {event.error}")
```

## Async Conversation

```python
from ai_sdk import Conversation

async def chat(client: AiSdk):
    agent = client.agent("DataQualityPlannerAgent")
    conv = Conversation(agent)

    # Async send
    response1 = await conv.asend("Analyze the orders table")
    print(response1)

    response2 = await conv.asend("Create tests for the issues")
    print(response2)

    # Async stream
    async for event in await conv.astream("Show me the SQL"):
        if event.type == "content":
            print(event.content, end="")
```

## Async List Agents

```python
async def list_all_agents(client: AiSdk) -> list:
    agents = await client.alist_agents(limit=100)
    return [a for a in agents if a.api_enabled]
```

## Error Handling

```python
from ai_sdk.exceptions import (
    RateLimitError,
    AgentExecutionError,
    AiSdkError,
)

async def safe_call(client: AiSdk, message: str) -> str | None:
    try:
        response = await client.agent("MyAgent").acall(message)
        return response.response

    except RateLimitError as e:
        if e.retry_after:
            await asyncio.sleep(e.retry_after)
            response = await client.agent("MyAgent").acall(message)
            return response.response
        return None

    except AgentExecutionError as e:
        print(f"Agent failed: {e.message}")
        return None
```

## Retry with Backoff

```python
async def with_retry(
    coro_func,
    max_retries: int = 3,
    base_delay: float = 1.0,
):
    """Execute async function with retry."""
    last_error = None

    for attempt in range(max_retries):
        try:
            return await coro_func()

        except RateLimitError as e:
            last_error = e
            delay = e.retry_after or (base_delay * (2 ** attempt))
            await asyncio.sleep(delay)

        except AgentExecutionError as e:
            last_error = e
            delay = base_delay * (2 ** attempt)
            await asyncio.sleep(delay)

    raise last_error

# Usage
response = await with_retry(
    lambda: client.agent("MyAgent").acall("Hello")
)
```

## Timeout Control

```python
async def call_with_timeout(
    client: AiSdk,
    message: str,
    timeout: float = 30.0,
) -> str:
    """Call agent with timeout."""
    try:
        response = await asyncio.wait_for(
            client.agent("MyAgent").acall(message),
            timeout=timeout,
        )
        return response.response

    except asyncio.TimeoutError:
        raise TimeoutError(f"Agent call timed out after {timeout}s")
```

## Parallel with Semaphore

Limit concurrent requests:

```python
async def rate_limited_calls(
    client: AiSdk,
    messages: list[str],
    max_concurrent: int = 5,
) -> list[str]:
    """Make calls with concurrency limit."""
    semaphore = asyncio.Semaphore(max_concurrent)
    agent = client.agent("MyAgent")

    async def call_one(message: str) -> str:
        async with semaphore:
            response = await agent.acall(message)
            return response.response

    return await asyncio.gather(*[
        call_one(msg) for msg in messages
    ])
```

## Producer-Consumer Pattern

```python
async def process_queue(
    client: AiSdk,
    queue: asyncio.Queue,
    results: list,
):
    """Consumer that processes messages from queue."""
    agent = client.agent("MyAgent")

    while True:
        message = await queue.get()
        if message is None:  # Sentinel
            break

        response = await agent.acall(message)
        results.append(response.response)
        queue.task_done()

async def main():
    client = AiSdk(host="...", token="...", enable_async=True)
    queue = asyncio.Queue()
    results = []

    # Start workers
    workers = [
        asyncio.create_task(process_queue(client, queue, results))
        for _ in range(3)
    ]

    # Add messages
    for msg in ["Query 1", "Query 2", "Query 3"]:
        await queue.put(msg)

    # Signal completion
    for _ in workers:
        await queue.put(None)

    await asyncio.gather(*workers)
    print(f"Processed {len(results)} messages")
```

## Best Practices

1. **Always enable async explicitly** - Set `enable_async=True`
2. **Use context managers** - Ensure proper cleanup
3. **Handle both close methods** - Call `aclose()` and `close()`
4. **Limit concurrency** - Use semaphores for rate limiting
5. **Set timeouts** - Prevent hanging operations
6. **Handle cancellation** - Clean up on `asyncio.CancelledError`

## Common Mistakes

### Forgetting to enable async

```python
# Wrong - async not enabled
client = AiSdk(host="...", token="...")
await client.agent("MyAgent").acall("Hi")  # RuntimeError!

# Correct
client = AiSdk(host="...", token="...", enable_async=True)
await client.agent("MyAgent").acall("Hi")
```

### Not closing properly

```python
# Wrong - async client not closed
client = AiSdk(host="...", token="...", enable_async=True)
response = await client.agent("MyAgent").acall("Hi")
client.close()  # Only closes sync client!

# Correct
await client.aclose()  # Close async first
client.close()         # Then sync
```

### Using sync in async context

```python
# Inefficient - blocks event loop
async def bad():
    response = client.agent("MyAgent").call("Hi")  # Sync call!

# Correct
async def good():
    response = await client.agent("MyAgent").acall("Hi")
```
