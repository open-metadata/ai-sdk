package io.openmetadata.ai;

import io.openmetadata.ai.internal.MetadataHttpClient;
import io.openmetadata.ai.models.AgentInfo;
import io.openmetadata.ai.models.InvokeRequest;
import io.openmetadata.ai.models.InvokeResponse;
import io.openmetadata.ai.models.StreamEvent;

import java.util.Map;
import java.util.function.Consumer;
import java.util.stream.Stream;

/**
 * Handle for interacting with a specific AI agent.
 * <p>
 * Instances are obtained via {@link MetadataAI#agent(String)}.
 * <p>
 * Example usage:
 * <pre>{@code
 * MetadataAI client = MetadataAI.builder()
 *     .host("https://metadata.example.com")
 *     .token("your-jwt-token")
 *     .build();
 *
 * // Simple invocation
 * InvokeResponse response = client.agent("semantic-layer-agent")
 *     .invoke("What tables exist?");
 *
 * // Multi-turn conversation
 * InvokeResponse r1 = client.agent("planner").invoke("Analyze orders");
 * InvokeResponse r2 = client.agent("planner")
 *     .conversationId(r1.getConversationId())
 *     .invoke("Create tests for the issues");
 * }</pre>
 */
public class AgentHandle {

    private final MetadataHttpClient httpClient;
    private final String agentName;
    private String conversationId;
    private Map<String, Object> parameters;

    AgentHandle(MetadataHttpClient httpClient, String agentName) {
        this.httpClient = httpClient;
        this.agentName = agentName;
    }

    /**
     * Sets the conversation ID for multi-turn conversations.
     *
     * @param conversationId the conversation ID from a previous response
     * @return this handle for method chaining
     */
    public AgentHandle conversationId(String conversationId) {
        this.conversationId = conversationId;
        return this;
    }

    /**
     * Sets additional parameters for the invocation.
     *
     * @param parameters a map of parameter names to values
     * @return this handle for method chaining
     */
    public AgentHandle parameters(Map<String, Object> parameters) {
        this.parameters = parameters;
        return this;
    }

    /**
     * Gets information about this agent.
     *
     * @return the agent information
     */
    public AgentInfo info() {
        return httpClient.getAgent(agentName);
    }

    /**
     * Invokes the agent synchronously using the agent's default prompt.
     * <p>
     * When no message is provided, the backend will use the agent's configured
     * {@code prompt} field as the default message.
     *
     * @return the agent's response
     */
    public InvokeResponse invoke() {
        InvokeRequest request = new InvokeRequest(null, conversationId, parameters);
        return httpClient.invoke(agentName, request);
    }

    /**
     * Invokes the agent synchronously with the given message.
     *
     * @param message the message to send to the agent
     * @return the agent's response
     */
    public InvokeResponse invoke(String message) {
        InvokeRequest request = new InvokeRequest(message, conversationId, parameters);
        return httpClient.invoke(agentName, request);
    }

    /**
     * Invokes the agent with streaming using the agent's default prompt, calling the consumer for each event.
     * <p>
     * When no message is provided, the backend will use the agent's configured
     * {@code prompt} field as the default message.
     * <p>
     * Example:
     * <pre>{@code
     * client.agent("semantic-layer-agent")
     *     .stream(event -> {
     *         if (event.getType() == StreamEvent.Type.CONTENT) {
     *             System.out.print(event.getContent());
     *         }
     *     });
     * }</pre>
     *
     * @param eventConsumer a consumer that will be called for each streaming event
     */
    public void stream(Consumer<StreamEvent> eventConsumer) {
        InvokeRequest request = new InvokeRequest(null, conversationId, parameters);
        httpClient.stream(agentName, request, eventConsumer);
    }

    /**
     * Invokes the agent with streaming, calling the consumer for each event.
     * <p>
     * Example:
     * <pre>{@code
     * client.agent("semantic-layer-agent")
     *     .stream("Analyze data quality", event -> {
     *         if (event.getType() == StreamEvent.Type.CONTENT) {
     *             System.out.print(event.getContent());
     *         }
     *     });
     * }</pre>
     *
     * @param message the message to send to the agent
     * @param eventConsumer a consumer that will be called for each streaming event
     */
    public void stream(String message, Consumer<StreamEvent> eventConsumer) {
        InvokeRequest request = new InvokeRequest(message, conversationId, parameters);
        httpClient.stream(agentName, request, eventConsumer);
    }

    /**
     * Invokes the agent with streaming using the agent's default prompt, returning a Stream of events.
     * <p>
     * When no message is provided, the backend will use the agent's configured
     * {@code prompt} field as the default message.
     * <p>
     * The caller must close the returned Stream when done (use try-with-resources).
     * <p>
     * Example:
     * <pre>{@code
     * try (Stream<StreamEvent> events = client.agent("planner")
     *         .streamIterator()) {
     *     events.filter(e -> e.getType() == StreamEvent.Type.CONTENT)
     *           .forEach(e -> System.out.print(e.getContent()));
     * }
     * }</pre>
     *
     * @return a Stream of events that must be closed when done
     */
    public Stream<StreamEvent> streamIterator() {
        InvokeRequest request = new InvokeRequest(null, conversationId, parameters);
        return httpClient.streamIterator(agentName, request);
    }

    /**
     * Invokes the agent with streaming, returning a Stream of events.
     * <p>
     * The caller must close the returned Stream when done (use try-with-resources).
     * <p>
     * Example:
     * <pre>{@code
     * try (Stream<StreamEvent> events = client.agent("planner")
     *         .streamIterator("Analyze orders")) {
     *     events.filter(e -> e.getType() == StreamEvent.Type.CONTENT)
     *           .forEach(e -> System.out.print(e.getContent()));
     * }
     * }</pre>
     *
     * @param message the message to send to the agent
     * @return a Stream of events that must be closed when done
     */
    public Stream<StreamEvent> streamIterator(String message) {
        InvokeRequest request = new InvokeRequest(message, conversationId, parameters);
        return httpClient.streamIterator(agentName, request);
    }
}
