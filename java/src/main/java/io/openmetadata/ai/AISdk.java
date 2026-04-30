package io.openmetadata.ai;

import java.time.Duration;
import java.util.Objects;

import io.openmetadata.ai.api.AbilitiesApi;
import io.openmetadata.ai.api.AgentsApi;
import io.openmetadata.ai.api.BotsApi;
import io.openmetadata.ai.api.MemoriesApi;
import io.openmetadata.ai.api.PersonasApi;
import io.openmetadata.ai.internal.AISdkHttpClient;

/**
 * Main client for interacting with the AI SDK Agents API.
 *
 * <p>Use the {@link #builder()} method to create a new instance:
 *
 * <pre>{@code
 * AISdk client = AISdk.builder()
 *     .host("https://metadata.example.com")
 *     .token("your-jwt-token")
 *     .build();
 *
 * // Simple invocation
 * InvokeResponse response = client.agent("semantic-layer-agent")
 *     .invoke("What tables exist?");
 *
 * // Namespaced operations
 * List<AgentInfo> agents = client.agents().list();
 * BotInfo bot = client.bots().get("ingestion-bot");
 * List<ContextMemory> memories = client.memories().list();
 *
 * client.close();
 * }</pre>
 */
public class AISdk implements AutoCloseable {

  // Generous default — agent runs can take many minutes. Note this maps to
  // HttpClient.Builder.connectTimeout(...) only (TCP connect), so SSE bodies
  // are never bounded by it. Per-request HttpRequest.timeout(...) is
  // intentionally NOT set on streaming requests; see AISdkHttpClient.
  private static final Duration DEFAULT_TIMEOUT = Duration.ofSeconds(900);
  private static final int DEFAULT_MAX_RETRIES = 3;
  private static final Duration DEFAULT_RETRY_DELAY = Duration.ofSeconds(1);
  private static final String MEMORIES_BASE_PATH = "/api/v1/contextCenter/memories";
  private static final String SEARCH_BASE_PATH = "/api/v1";

  private final AISdkHttpClient httpClient;
  private final AISdkHttpClient memoriesHttpClient;
  private final AISdkHttpClient searchHttpClient;

  private final AgentsApi agentsApi;
  private final BotsApi botsApi;
  private final PersonasApi personasApi;
  private final AbilitiesApi abilitiesApi;
  private final MemoriesApi memoriesApi;

  private AISdk(Builder builder) {
    Duration timeout = builder.timeout != null ? builder.timeout : DEFAULT_TIMEOUT;
    int maxRetries = builder.maxRetries != null ? builder.maxRetries : DEFAULT_MAX_RETRIES;
    Duration retryDelay = builder.retryDelay != null ? builder.retryDelay : DEFAULT_RETRY_DELAY;

    this.httpClient =
        new AISdkHttpClient(builder.host, builder.token, timeout, maxRetries, retryDelay);
    this.memoriesHttpClient =
        new AISdkHttpClient(
            builder.host, builder.token, timeout, maxRetries, retryDelay, MEMORIES_BASE_PATH);
    this.searchHttpClient =
        new AISdkHttpClient(
            builder.host, builder.token, timeout, maxRetries, retryDelay, SEARCH_BASE_PATH);

    this.agentsApi = new AgentsApi(httpClient, this);
    this.botsApi = new BotsApi(httpClient);
    this.personasApi = new PersonasApi(httpClient);
    this.abilitiesApi = new AbilitiesApi(httpClient);
    this.memoriesApi = new MemoriesApi(memoriesHttpClient, searchHttpClient);
  }

  /**
   * Creates a new builder.
   *
   * @return a new builder instance
   */
  public static Builder builder() {
    return new Builder();
  }

  /**
   * Gets a handle for interacting with the specified agent.
   *
   * @param name the name of the agent
   * @return an agent handle
   */
  public AgentHandle agent(String name) {
    Objects.requireNonNull(name, "Agent name cannot be null");
    return new AgentHandle(httpClient, name);
  }

  /**
   * Gets a handle for the platform's default agent.
   *
   * <p>The default agent uses agentType=PLANNER, agentMode=CHAT_MODE. A chat conversation is
   * auto-created when {@link DefaultAgentHandle#conversationId} is not set.
   *
   * @return a handle for the default agent
   */
  public DefaultAgentHandle agent() {
    return new DefaultAgentHandle(httpClient);
  }

  /** Returns the agents namespace. */
  public AgentsApi agents() {
    return agentsApi;
  }

  /** Returns the bots namespace. */
  public BotsApi bots() {
    return botsApi;
  }

  /** Returns the personas namespace. */
  public PersonasApi personas() {
    return personasApi;
  }

  /** Returns the abilities namespace. */
  public AbilitiesApi abilities() {
    return abilitiesApi;
  }

  /** Returns the memories namespace. */
  public MemoriesApi memories() {
    return memoriesApi;
  }

  /** Closes the client and releases resources. */
  @Override
  public void close() {
    httpClient.close();
    memoriesHttpClient.close();
    searchHttpClient.close();
  }

  /** Builder for creating {@link AISdk} instances. */
  public static class Builder {
    private String host;
    private String token;
    private Duration timeout;
    private Integer maxRetries;
    private Duration retryDelay;

    private Builder() {}

    /**
     * Sets the host URL.
     *
     * @param host the host URL (e.g., "https://metadata.example.com")
     * @return this builder
     */
    public Builder host(String host) {
      this.host = host;
      return this;
    }

    /**
     * Sets the JWT authentication token.
     *
     * @param token the JWT token
     * @return this builder
     */
    public Builder token(String token) {
      this.token = token;
      return this;
    }

    /**
     * Sets the request timeout.
     *
     * <p>This value is applied as the {@link
     * java.net.http.HttpClient.Builder#connectTimeout(Duration) TCP connect timeout} on the
     * underlying {@link java.net.http.HttpClient}. It does NOT bound the time spent reading a
     * response body: SSE streams from long-running agent runs may continue for many minutes, and
     * the stream's own events (thinking/message/tool) signal liveness.
     *
     * <p>Default: 900 seconds
     *
     * @param timeout the timeout duration
     * @return this builder
     */
    public Builder timeout(Duration timeout) {
      this.timeout = timeout;
      return this;
    }

    /**
     * Sets the maximum number of retries for failed requests.
     *
     * <p>Default: 3
     *
     * @param maxRetries the maximum number of retries
     * @return this builder
     */
    public Builder maxRetries(int maxRetries) {
      this.maxRetries = maxRetries;
      return this;
    }

    /**
     * Sets the delay between retries.
     *
     * <p>Default: 1 second
     *
     * @param retryDelay the retry delay duration
     * @return this builder
     */
    public Builder retryDelay(Duration retryDelay) {
      this.retryDelay = retryDelay;
      return this;
    }

    /**
     * Builds the AISdk instance.
     *
     * @return a new AISdk instance
     * @throws NullPointerException if host or token is null
     * @throws IllegalArgumentException if host is empty
     */
    public AISdk build() {
      Objects.requireNonNull(host, "host is required");
      Objects.requireNonNull(token, "token is required");
      if (host.isEmpty()) {
        throw new IllegalArgumentException("host cannot be empty");
      }
      if (token.isEmpty()) {
        throw new IllegalArgumentException("token cannot be empty");
      }
      return new AISdk(this);
    }
  }
}
