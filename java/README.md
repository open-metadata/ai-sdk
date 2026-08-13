# AI SDK for Java

Java SDK for interacting with AI Agents.

## Requirements

- Java 11 or later
- Maven or Gradle

## Installation

### Maven

```xml
<dependency>
    <groupId>org.open-metadata</groupId>
    <artifactId>ai-sdk</artifactId>
    <version>0.1.0</version>
</dependency>
```

### Gradle

```groovy
implementation 'org.open-metadata:ai-sdk:0.1.0'
```

## Quick Start

```java
import io.openmetadata.ai.AISdk;
import io.openmetadata.ai.models.InvokeResponse;
import io.openmetadata.ai.models.StreamEvent;
import io.openmetadata.ai.models.AgentInfo;

import java.time.Duration;
import java.util.List;

public class Example {
    public static void main(String[] args) {
        // Create client
        AISdk client = AISdk.builder()
            .host("https://metadata.example.com")
            .token("your-jwt-token")
            .timeout(Duration.ofSeconds(120))  // optional
            .maxRetries(3)                     // optional
            .build();

        // default AskCollate agent
        InvokeResponse defaultResponse = client.agent()
            .invoke("What tables exist?");
        System.out.println(defaultResponse.getResponse());

        // Named dynamic agent
        InvokeResponse response = client.agent("semantic-layer-agent")
            .invoke("What tables exist?");

        System.out.println(response.getResponse());
        System.out.println("Tools used: " + response.getToolsUsed());

        // Don't forget to close
        client.close();
    }
}
```

## Usage

### Creating a Client

```java
AISdk client = AISdk.builder()
    .host("https://metadata.example.com")  // Required
    .token("your-jwt-token")              // Required
    .timeout(Duration.ofSeconds(120))     // Optional, default: 120s
    .maxRetries(3)                        // Optional, default: 3
    .retryDelay(Duration.ofSeconds(1))    // Optional, default: 1s
    .build();
```

### Synchronous Invocation

```java
InvokeResponse response = client.agent("semantic-layer-agent")
    .invoke("What tables exist?");

System.out.println(response.getResponse());
System.out.println("Conversation ID: " + response.getConversationId());
System.out.println("Tools used: " + response.getToolsUsed());

// Token usage (if available)
if (response.getUsage() != null) {
    System.out.println("Tokens: " + response.getUsage().getTotalTokens());
}
```

### Streaming with Consumer Callback

```java
client.agent("semantic-layer-agent")
    .stream("Analyze data quality", event -> {
        switch (event.getType()) {
            case START:
                System.out.println("Started, conversation: " + event.getConversationId());
                break;
            case CONTENT:
                System.out.print(event.getContent());
                break;
            case TOOL_USE:
                System.out.println("[Using tool: " + event.getToolName() + "]");
                break;
            case END:
                System.out.println("\nCompleted");
                break;
        }
    });
```

### Streaming with Java Stream API

```java
import java.util.stream.Stream;

try (Stream<StreamEvent> events = client.agent("planner")
        .streamIterator("Analyze orders")) {
    events.filter(e -> e.getType() == StreamEvent.Type.CONTENT)
          .forEach(e -> System.out.print(e.getContent()));
}
```

### Multi-turn Conversations

```java
// First message
InvokeResponse r1 = client.agent("planner")
    .invoke("Analyze the orders table");

// Continue the conversation using the conversation ID
InvokeResponse r2 = client.agent("planner")
    .conversationId(r1.getConversationId())
    .invoke("Create tests for the issues you found");

System.out.println(r2.getResponse());
```

### Additional Parameters

```java
import java.util.Map;
import java.util.HashMap;

Map<String, Object> params = new HashMap<>();
params.put("temperature", 0.7);
params.put("maxTokens", 1000);

InvokeResponse response = client.agent("semantic-layer-agent")
    .parameters(params)
    .invoke("Generate a report");
```

### Listing Agents

```java
List<AgentInfo> agents = client.agents().list();

for (AgentInfo agent : agents) {
    System.out.println(agent.getName() + ": " + agent.getDescription());
    System.out.println("  API Enabled: " + agent.isApiEnabled());
    System.out.println("  Skills: " + agent.getSkills());
}
```

### Getting Agent Information

```java
AgentInfo info = client.agent("semantic-layer-agent").info();

System.out.println("Name: " + info.getName());
System.out.println("Display Name: " + info.getDisplayName());
System.out.println("Description: " + info.getDescription());
System.out.println("Skills: " + info.getSkills());
```

### Create Agents

```java
import io.openmetadata.ai.models.CreateAgentRequest;

CreateAgentRequest request = CreateAgentRequest.builder()
    .name("MyCustomAgent")
    .description("A custom agent for data analysis")
    .persona("DataAnalyst")
    .apiEnabled(true)
    .skills(List.of("search", "query"))
    .build();

AgentInfo newAgent = client.agents().create(request);
System.out.println("Created agent: " + newAgent.getName());
```

### Bots

```java
import io.openmetadata.ai.models.BotInfo;

// List all bots
List<BotInfo> bots = client.bots().list();
for (BotInfo bot : bots) {
    System.out.println(bot.getName() + ": " + bot.getDisplayName());
}

// Get a specific bot
BotInfo bot = client.bots().get("my-bot-name");
System.out.println("Bot: " + bot.getName());
```

### Personas

```java
import io.openmetadata.ai.models.PersonaInfo;
import io.openmetadata.ai.models.CreatePersonaRequest;

// List all personas
List<PersonaInfo> personas = client.personas().list();
for (PersonaInfo persona : personas) {
    System.out.println(persona.getName() + ": " + persona.getDescription());
}

// Get a specific persona
PersonaInfo persona = client.personas().get("DataAnalyst");

// Create a new persona
CreatePersonaRequest request = CreatePersonaRequest.builder()
    .name("CustomAnalyst")
    .description("A specialized data analyst")
    .prompt("You are an expert data analyst who helps users understand their data...")
    .build();

PersonaInfo newPersona = client.personas().create(request);
System.out.println("Created persona: " + newPersona.getName());
```

### Skills

```java
import io.openmetadata.ai.models.SkillInfo;

// List all skills
List<SkillInfo> skills = client.skills().list();
for (SkillInfo skill : skills) {
    System.out.println(skill.getName() + ": " + skill.getDescription());
}

// Get a specific skill
SkillInfo skill = client.skills().get("search");
System.out.println("Skill: " + skill.getName());
```

### Context Memories

The `client.memories()` namespace manages reusable Context Center knowledge — preferences, use cases, runbooks, and FAQs that any AI agent can read.

```java
import io.openmetadata.ai.models.*;
import java.util.List;
import java.util.Map;

// Create
ContextMemory created = client.memories().create(
    CreateContextMemoryRequest.builder()
        .name("orders-grain")
        .title("Orders grain")
        .question("What is the grain of the orders table?")
        .answer("One row per order_id.")
        .memoryType(MemoryType.NOTE)              // PREFERENCE | USE_CASE | NOTE | RUNBOOK | FAQ
        .visibility(MemoryVisibility.SHARED)      // PRIVATE | ENTITY | SHARED
        .primaryEntity(EntityReference.builder().id("<table-uuid>").type("table").build())
        .tags(List.of("Domain.Analytics"))
        .build()
);

// Get
ContextMemory fetched = client.memories().get(created.getId());

// List (optional FQN filter, optional limit)
List<ContextMemory> all = client.memories().list();
List<ContextMemory> forTable = client.memories().list("prod.warehouse.orders", 50);
for (ContextMemory m : forTable) {
    System.out.println(m.getTitle());
}

// Hybrid NLQ search — combines vector + keyword ranking over the contextMemory index
MemorySearchResults results = client.memories().search("how do we measure order volume");
for (MemorySearchHit hit : results.getHits()) {
    System.out.printf("[%.2f] %s%n", hit.getScore(), hit.getMemory().getTitle());
}

// Search with filters and pagination
MemorySearchResults filtered = client.memories().search(
    "explain churn",
    Map.of(
        "primaryEntityId", List.of("<uuid>"),
        "visibility", List.of("Entity", "Shared")
    ),
    20,   // size
    0     // from
);

// Soft delete by default; pass true for hard delete
client.memories().delete(created.getId());
client.memories().delete(created.getId(), true);
```

**Stored fields:**

| Field | Notes |
|-------|-------|
| `name` | Stable system name (required) |
| `question` / `answer` | Canonical Q/A pair (required) — what an agent retrieves |
| `title`, `description`, `summary` | Human-facing text, optional |
| `memoryType` | `PREFERENCE`, `USE_CASE`, `NOTE`, `RUNBOOK`, or `FAQ` |
| `memoryScope` | `ENTITY_SCOPED` (default) or `USER_GLOBAL` |
| `visibility` | `PRIVATE`, `ENTITY`, or `SHARED` (controls who can read it) |
| `primaryEntity` | Attaches the memory to a specific asset for entity-scoped recall |
| `tags` | List of tag FQN strings (e.g. `"PII.Sensitive"`) |

## Error Handling

The SDK provides specific exception types for different error conditions:

```java
import io.openmetadata.ai.exceptions.*;

try {
    InvokeResponse response = client.agent("my-agent").invoke("Hello");
} catch (AuthenticationException e) {
    // Invalid or expired token (HTTP 401)
    System.err.println("Authentication failed: " + e.getMessage());
} catch (AgentNotFoundException e) {
    // Agent does not exist (HTTP 404)
    System.err.println("Agent not found: " + e.getAgentName());
} catch (AgentNotEnabledException e) {
    // Agent exists but is not API-enabled (HTTP 403)
    System.err.println("Agent not API-enabled: " + e.getAgentName());
} catch (BotNotFoundException e) {
    // Bot does not exist (HTTP 404)
    System.err.println("Bot not found: " + e.getBotName());
} catch (PersonaNotFoundException e) {
    // Persona does not exist (HTTP 404)
    System.err.println("Persona not found: " + e.getPersonaName());
} catch (SkillNotFoundException e) {
    // Skill does not exist (HTTP 404)
    System.err.println("Skill not found: " + e.getSkillName());
} catch (RateLimitException e) {
    // Rate limit exceeded (HTTP 429)
    System.err.println("Rate limited. Retry after: " +
        e.getRetryAfter().orElse(60) + " seconds");
} catch (AISdkException e) {
    // Other API errors
    System.err.println("Error (status " + e.getStatusCode() + "): " + e.getMessage());
}
```

## Resource Management

The client implements `AutoCloseable`, so you can use try-with-resources:

```java
try (AISdk client = AISdk.builder()
        .host("https://metadata.example.com")
        .token("your-jwt-token")
        .build()) {

    InvokeResponse response = client.agent("my-agent").invoke("Hello");
    System.out.println(response.getResponse());
}
// Client is automatically closed
```

## Thread Safety

The `AISdk` client and `AgentHandle` are thread-safe and can be shared across multiple threads. It's recommended to create a single client instance and reuse it throughout your application.

## Building from Source

```bash
# Build
mvn clean package

# Run tests
mvn test

# Install to local Maven repository
mvn clean install
```

## License

Apache License 2.0
