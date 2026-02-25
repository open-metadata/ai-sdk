# CLAUDE.md - Java SDK

## Overview

Java SDK for AI agents. Uses java.net.http.HttpClient (Java 11+).

## Build Commands

```bash
mvn clean package        # Build JAR
mvn test                 # Run tests
mvn clean verify         # Full build + tests
mvn spotless:apply       # Format code (if configured)
```

## Project Structure

```
java/
├── src/main/java/io/metadata/ai/
│   ├── AISdk.java             # Main client with builder
│   ├── AgentHandle.java      # Agent operations
│   ├── models/               # POJOs
│   │   ├── InvokeRequest.java
│   │   ├── InvokeResponse.java
│   │   ├── StreamEvent.java
│   │   ├── AgentInfo.java
│   │   └── Usage.java
│   ├── exceptions/           # Exception hierarchy
│   │   ├── AISdkException.java
│   │   ├── AuthenticationException.java
│   │   └── ...
│   └── internal/             # Implementation details
│       ├── AISdkHttpClient.java
│       └── SseParser.java
├── src/test/java/io/metadata/ai/
│   └── AISdkTest.java
└── pom.xml
```

## Key Design Decisions

- **Java 11 minimum** - Uses HttpClient, no Apache HttpClient
- **Builder pattern** - `AISdk.builder().host(...).build()`
- **Jackson** - JSON serialization (only external dependency)
- **AutoCloseable** - Client implements close() for resource cleanup

## API Pattern

```java
AISdk client = AISdk.builder()
    .host("https://...")
    .token("...")
    .build();

// Sync
InvokeResponse response = client.agent("name").invoke("message");

// Streaming with Consumer
client.agent("name").stream("message", event -> { });

// Streaming with Iterator
try (Stream<StreamEvent> events = client.agent("name").streamIterator("msg")) { }
```

## Adding a New Method

1. Add method to `AgentHandle.java`
2. Add model classes if needed in `models/`
3. Update `AISdkHttpClient.java` if new HTTP logic needed
4. Add tests in `AISdkTest.java`

## DO NOT

- Use Java < 11 features expectations
- Add dependencies beyond Jackson without justification
- Make internal classes public
