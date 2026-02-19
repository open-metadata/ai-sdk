# Metadata AI Java SDK

Java SDK for interacting with Metadata AI Agents.

## Requirements

- Java 11 or later
- Maven or Gradle

## Installation

### Maven

```xml
<dependency>
    <groupId>io.openmetadata</groupId>
    <artifactId>ai-sdk</artifactId>
    <version>0.1.0</version>
</dependency>
```

### Gradle

```groovy
implementation 'io.openmetadata:ai-sdk:0.1.0'
```

## Quick Start

```java
import io.openmetadata.ai.MetadataAI;
import io.openmetadata.ai.models.InvokeResponse;
import io.openmetadata.ai.models.StreamEvent;
import io.openmetadata.ai.models.AgentInfo;

import java.time.Duration;
import java.util.List;

public class Example {
    public static void main(String[] args) {
        // Create client
        MetadataAI client = MetadataAI.builder()
            .host("https://metadata.example.com")
            .token("your-jwt-token")
            .timeout(Duration.ofSeconds(120))  // optional
            .maxRetries(3)                     // optional
            .build();

        // Simple invocation
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
MetadataAI client = MetadataAI.builder()
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
List<AgentInfo> agents = client.listAgents();

for (AgentInfo agent : agents) {
    System.out.println(agent.getName() + ": " + agent.getDescription());
    System.out.println("  API Enabled: " + agent.isApiEnabled());
    System.out.println("  Abilities: " + agent.getAbilities());
}
```

### Getting Agent Information

```java
AgentInfo info = client.agent("semantic-layer-agent").info();

System.out.println("Name: " + info.getName());
System.out.println("Display Name: " + info.getDisplayName());
System.out.println("Description: " + info.getDescription());
System.out.println("Abilities: " + info.getAbilities());
```

### Create Agents

```java
import io.openmetadata.ai.models.CreateAgentRequest;

CreateAgentRequest request = CreateAgentRequest.builder()
    .name("MyCustomAgent")
    .description("A custom agent for data analysis")
    .persona("DataAnalyst")
    .apiEnabled(true)
    .abilities(List.of("search", "query"))
    .build();

AgentInfo newAgent = client.createAgent(request);
System.out.println("Created agent: " + newAgent.getName());
```

### Bots

```java
import io.openmetadata.ai.models.BotInfo;

// List all bots
List<BotInfo> bots = client.listBots();
for (BotInfo bot : bots) {
    System.out.println(bot.getName() + ": " + bot.getDisplayName());
}

// Get a specific bot
BotInfo bot = client.getBot("my-bot-name");
System.out.println("Bot: " + bot.getName());
```

### Personas

```java
import io.openmetadata.ai.models.PersonaInfo;
import io.openmetadata.ai.models.CreatePersonaRequest;

// List all personas
List<PersonaInfo> personas = client.listPersonas();
for (PersonaInfo persona : personas) {
    System.out.println(persona.getName() + ": " + persona.getDescription());
}

// Get a specific persona
PersonaInfo persona = client.getPersona("DataAnalyst");

// Create a new persona
CreatePersonaRequest request = CreatePersonaRequest.builder()
    .name("CustomAnalyst")
    .description("A specialized data analyst")
    .prompt("You are an expert data analyst who helps users understand their data...")
    .build();

PersonaInfo newPersona = client.createPersona(request);
System.out.println("Created persona: " + newPersona.getName());
```

### Abilities

```java
import io.openmetadata.ai.models.AbilityInfo;

// List all abilities
List<AbilityInfo> abilities = client.listAbilities();
for (AbilityInfo ability : abilities) {
    System.out.println(ability.getName() + ": " + ability.getDescription());
}

// Get a specific ability
AbilityInfo ability = client.getAbility("search");
System.out.println("Ability: " + ability.getName());
```

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
} catch (AbilityNotFoundException e) {
    // Ability does not exist (HTTP 404)
    System.err.println("Ability not found: " + e.getAbilityName());
} catch (RateLimitException e) {
    // Rate limit exceeded (HTTP 429)
    System.err.println("Rate limited. Retry after: " +
        e.getRetryAfter().orElse(60) + " seconds");
} catch (MetadataException e) {
    // Other API errors
    System.err.println("Error (status " + e.getStatusCode() + "): " + e.getMessage());
}
```

## Resource Management

The client implements `AutoCloseable`, so you can use try-with-resources:

```java
try (MetadataAI client = MetadataAI.builder()
        .host("https://metadata.example.com")
        .token("your-jwt-token")
        .build()) {

    InvokeResponse response = client.agent("my-agent").invoke("Hello");
    System.out.println(response.getResponse());
}
// Client is automatically closed
```

## Thread Safety

The `MetadataAI` client and `AgentHandle` are thread-safe and can be shared across multiple threads. It's recommended to create a single client instance and reuse it throughout your application.

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
