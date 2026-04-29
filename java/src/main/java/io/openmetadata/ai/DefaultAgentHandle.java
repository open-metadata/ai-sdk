package io.openmetadata.ai;

import java.util.function.Consumer;
import java.util.stream.Stream;

import io.openmetadata.ai.internal.AISdkHttpClient;
import io.openmetadata.ai.models.InvokeResponse;
import io.openmetadata.ai.models.StreamEvent;

/**
 * Handle for the platform's default agent (PLANNER / CHAT_MODE).
 *
 * <p>Auto-creates a chat conversation when one is not supplied, then invokes the sync
 * /api/v1/agents/invoke or streaming /api/v1/agents/run endpoints.
 *
 * <p>Example:
 *
 * <pre>{@code
 * AISdk client = AISdk.builder().host("...").token("...").build();
 * InvokeResponse response = client.agent().invoke("Hello");
 * }</pre>
 */
public class DefaultAgentHandle {

  private static final String AGENT_TYPE = "PLANNER";
  private static final String AGENT_MODE = "CHAT_MODE";
  private static final int TITLE_MAX_LEN = 50;

  private final AISdkHttpClient httpClient;
  private String conversationId;

  DefaultAgentHandle(AISdkHttpClient httpClient) {
    this.httpClient = httpClient;
  }

  /**
   * Sets the conversation ID for multi-turn conversations.
   *
   * @param conversationId the conversation ID from a previous response
   * @return this handle for method chaining
   */
  public DefaultAgentHandle conversationId(String conversationId) {
    this.conversationId = conversationId;
    return this;
  }

  /**
   * Invokes the default agent synchronously.
   *
   * @param message the message to send
   * @return the agent's response
   */
  public InvokeResponse invoke(String message) {
    String cid = ensureConversation(message);
    return httpClient.invokeDefaultAgent(message, cid, AGENT_TYPE, AGENT_MODE);
  }

  /**
   * Invokes the default agent with streaming, calling the consumer for each event.
   *
   * @param message the message to send
   * @param consumer a consumer that will be called for each streaming event
   */
  public void stream(String message, Consumer<StreamEvent> consumer) {
    String cid = ensureConversation(message);
    httpClient.streamDefaultAgent(message, cid, AGENT_TYPE, AGENT_MODE, consumer);
  }

  /**
   * Invokes the default agent with streaming, returning a Stream of events. The caller must close
   * the returned Stream when done (use try-with-resources).
   *
   * @param message the message to send
   * @return a Stream of events that must be closed when done
   */
  public Stream<StreamEvent> streamIterator(String message) {
    String cid = ensureConversation(message);
    return httpClient.streamDefaultAgentIterator(message, cid, AGENT_TYPE, AGENT_MODE);
  }

  /**
   * Invokes the default agent with streaming, calling the consumer for each content chunk.
   *
   * <p>Convenience wrapper around {@link #stream(String, Consumer)} that yields only text content.
   *
   * @param message the message to send
   * @param contentConsumer a consumer that will be called for each content string
   */
  public void streamContent(String message, Consumer<String> contentConsumer) {
    stream(
        message,
        event -> {
          if (event.getType() == StreamEvent.Type.CONTENT && event.getContent() != null) {
            contentConsumer.accept(event.getContent());
          }
        });
  }

  /**
   * Invokes the default agent with streaming, returning a Stream of content strings. The caller
   * must close the returned Stream when done (use try-with-resources).
   *
   * @param message the message to send
   * @return a Stream of content strings that must be closed when done
   */
  public Stream<String> streamContentIterator(String message) {
    return streamIterator(message)
        .filter(e -> e.getType() == StreamEvent.Type.CONTENT && e.getContent() != null)
        .map(StreamEvent::getContent);
  }

  private String ensureConversation(String message) {
    if (conversationId != null && !conversationId.isEmpty()) {
      return conversationId;
    }
    String title = message == null ? "New conversation" : message;
    if (title.length() > TITLE_MAX_LEN) {
      title = title.substring(0, TITLE_MAX_LEN);
    }
    String created = httpClient.createChatConversation(title);
    this.conversationId = created;
    return created;
  }
}
