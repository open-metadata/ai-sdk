package io.openmetadata.ai;

import java.time.Duration;
import java.util.List;
import java.util.Objects;

import io.openmetadata.ai.internal.MetadataHttpClient;
import io.openmetadata.ai.models.*;

/**
 * Main client for interacting with the Metadata AI Agents API.
 *
 * <p>Use the {@link #builder()} method to create a new instance:
 *
 * <pre>{@code
 * MetadataAI client = MetadataAI.builder()
 *     .host("https://metadata.example.com")
 *     .token("your-jwt-token")
 *     .timeout(Duration.ofSeconds(120))  // optional
 *     .maxRetries(3)                     // optional
 *     .build();
 *
 * // Simple invocation
 * InvokeResponse response = client.agent("semantic-layer-agent")
 *     .invoke("What tables exist?");
 *
 * // Streaming with Consumer callback
 * client.agent("semantic-layer-agent")
 *     .stream("Analyze data quality", event -> {
 *         if (event.getType() == StreamEvent.Type.CONTENT) {
 *             System.out.print(event.getContent());
 *         }
 *     });
 *
 * // Streaming with Java Stream API
 * try (Stream<StreamEvent> events = client.agent("planner")
 *         .streamIterator("Analyze orders")) {
 *     events.filter(e -> e.getType() == StreamEvent.Type.CONTENT)
 *           .forEach(e -> System.out.print(e.getContent()));
 * }
 *
 * // Multi-turn conversation
 * InvokeResponse r1 = client.agent("planner").invoke("Analyze orders");
 * InvokeResponse r2 = client.agent("planner")
 *     .conversationId(r1.getConversationId())
 *     .invoke("Create tests for the issues");
 *
 * // List agents
 * List<AgentInfo> agents = client.listAgents();
 *
 * // Clean up
 * client.close();
 * }</pre>
 *
 * <p>This class implements {@link AutoCloseable} for use with try-with-resources:
 *
 * <pre>{@code
 * try (MetadataAI client = MetadataAI.builder()
 *         .host("https://metadata.example.com")
 *         .token("your-jwt-token")
 *         .build()) {
 *     // Use client...
 * }
 * }</pre>
 */
public class MetadataAI implements AutoCloseable {

  private static final Duration DEFAULT_TIMEOUT = Duration.ofSeconds(120);
  private static final int DEFAULT_MAX_RETRIES = 3;
  private static final Duration DEFAULT_RETRY_DELAY = Duration.ofSeconds(1);

  private final MetadataHttpClient httpClient;

  private MetadataAI(Builder builder) {
    this.httpClient =
        new MetadataHttpClient(
            builder.host,
            builder.token,
            builder.timeout != null ? builder.timeout : DEFAULT_TIMEOUT,
            builder.maxRetries != null ? builder.maxRetries : DEFAULT_MAX_RETRIES,
            builder.retryDelay != null ? builder.retryDelay : DEFAULT_RETRY_DELAY);
  }

  /**
   * Creates a new builder for MetadataAI.
   *
   * @return a new builder instance
   */
  public static Builder builder() {
    return new Builder();
  }

  /**
   * Gets a handle for interacting with the specified agent.
   *
   * <p>The returned handle can be used to invoke the agent synchronously, with streaming, or to get
   * agent information.
   *
   * @param name the name of the agent
   * @return an agent handle
   */
  public AgentHandle agent(String name) {
    Objects.requireNonNull(name, "Agent name cannot be null");
    return new AgentHandle(httpClient, name);
  }

  /**
   * Lists all API-enabled agents. Automatically paginates through all results.
   *
   * @return a list of all agent information
   */
  public List<AgentInfo> listAgents() {
    return httpClient.listAgents();
  }

  /**
   * Lists API-enabled agents with optional limit. Automatically paginates through all results.
   *
   * @param limit the maximum number of agents to return
   * @return a list of agent information
   */
  public List<AgentInfo> listAgents(int limit) {
    return httpClient.listAgents(limit);
  }

  /**
   * Lists all API-enabled agents with pagination (deprecated).
   *
   * @param limit the maximum number of agents to return
   * @param offset ignored - use listAgents() or listAgents(int limit) instead
   * @return a list of agent information
   * @deprecated Use listAgents() or listAgents(int limit) instead
   */
  @Deprecated
  public List<AgentInfo> listAgents(int limit, int offset) {
    return httpClient.listAgents(limit, offset);
  }

  // ==================== Bot Operations ====================

  /**
   * Lists all bots. Automatically paginates through all results.
   *
   * @return a list of all bot information
   */
  public List<BotInfo> listBots() {
    return httpClient.listBots();
  }

  /**
   * Lists bots with optional limit. Automatically paginates through all results.
   *
   * @param limit the maximum number of bots to return
   * @return a list of bot information
   */
  public List<BotInfo> listBots(int limit) {
    return httpClient.listBots(limit);
  }

  /**
   * Gets a bot by name.
   *
   * @param name the name of the bot
   * @return the bot information
   * @throws io.openmetadata.ai.exceptions.BotNotFoundException if the bot is not found
   */
  public BotInfo getBot(String name) {
    Objects.requireNonNull(name, "Bot name cannot be null");
    return httpClient.getBotByName(name);
  }

  // ==================== Persona Operations ====================

  /**
   * Lists all personas. Automatically paginates through all results.
   *
   * @return a list of all persona information
   */
  public List<PersonaInfo> listPersonas() {
    return httpClient.listPersonas();
  }

  /**
   * Lists personas with optional limit. Automatically paginates through all results.
   *
   * @param limit the maximum number of personas to return
   * @return a list of persona information
   */
  public List<PersonaInfo> listPersonas(int limit) {
    return httpClient.listPersonas(limit);
  }

  /**
   * Gets a persona by name.
   *
   * @param name the name of the persona
   * @return the persona information
   * @throws io.openmetadata.ai.exceptions.PersonaNotFoundException if the persona is not found
   */
  public PersonaInfo getPersona(String name) {
    Objects.requireNonNull(name, "Persona name cannot be null");
    return httpClient.getPersonaByName(name);
  }

  /**
   * Creates a new persona.
   *
   * @param request the request to create the persona
   * @return the created persona information
   */
  public PersonaInfo createPersona(CreatePersonaRequest request) {
    Objects.requireNonNull(request, "CreatePersonaRequest cannot be null");
    return httpClient.createPersona(request);
  }

  // ==================== Ability Operations ====================

  /**
   * Lists all abilities. Automatically paginates through all results.
   *
   * @return a list of all ability information
   */
  public List<AbilityInfo> listAbilities() {
    return httpClient.listAbilities();
  }

  /**
   * Lists abilities with optional limit. Automatically paginates through all results.
   *
   * @param limit the maximum number of abilities to return
   * @return a list of ability information
   */
  public List<AbilityInfo> listAbilities(int limit) {
    return httpClient.listAbilities(limit);
  }

  /**
   * Gets an ability by name.
   *
   * @param name the name of the ability
   * @return the ability information
   * @throws io.openmetadata.ai.exceptions.AbilityNotFoundException if the ability is not found
   */
  public AbilityInfo getAbility(String name) {
    Objects.requireNonNull(name, "Ability name cannot be null");
    return httpClient.getAbilityByName(name);
  }

  // ==================== Agent Creation ====================

  /**
   * Creates a new dynamic agent.
   *
   * @param builder the builder containing agent configuration. Persona and ability names will be
   *     resolved to IDs automatically.
   * @return the created agent information
   */
  public AgentInfo createAgent(CreateAgentRequest.Builder builder) {
    Objects.requireNonNull(builder, "Builder cannot be null");

    // Resolve persona name to ID
    String personaName = builder.getPersonaName();
    if (personaName == null || personaName.isEmpty()) {
      throw new IllegalArgumentException("persona is required");
    }
    PersonaInfo personaInfo = getPersona(personaName);
    EntityReference personaRef =
        EntityReference.builder().id(personaInfo.getId()).type("persona").build();

    // Resolve ability names to IDs if provided
    List<EntityReference> abilityRefs = null;
    List<String> abilityNames = builder.getAbilityNames();
    if (abilityNames != null && !abilityNames.isEmpty()) {
      abilityRefs = new java.util.ArrayList<>();
      for (String abilityName : abilityNames) {
        AbilityInfo abilityInfo = getAbility(abilityName);
        EntityReference abilityRef =
            EntityReference.builder().id(abilityInfo.getId()).type("ability").build();
        abilityRefs.add(abilityRef);
      }
    }

    CreateAgentRequest request = builder.build(personaRef, abilityRefs);
    return httpClient.createAgent(request);
  }

  /**
   * Creates a new dynamic agent.
   *
   * @param request the request to create the agent (must have resolved persona and ability IDs)
   * @return the created agent information
   * @deprecated Use {@link #createAgent(CreateAgentRequest.Builder)} instead to automatically
   *     resolve persona and ability names
   */
  @Deprecated
  public AgentInfo createAgent(CreateAgentRequest request) {
    Objects.requireNonNull(request, "CreateAgentRequest cannot be null");
    return httpClient.createAgent(request);
  }

  /** Closes the client and releases resources. */
  @Override
  public void close() {
    httpClient.close();
  }

  /** Builder for creating MetadataAI instances. */
  public static class Builder {
    private String host;
    private String token;
    private Duration timeout;
    private Integer maxRetries;
    private Duration retryDelay;

    private Builder() {}

    /**
     * Sets the Metadata host URL.
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
     * <p>Default: 120 seconds
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
     * Builds the MetadataAI instance.
     *
     * @return a new MetadataAI instance
     * @throws NullPointerException if host or token is null
     * @throws IllegalArgumentException if host is empty
     */
    public MetadataAI build() {
      Objects.requireNonNull(host, "host is required");
      Objects.requireNonNull(token, "token is required");
      if (host.isEmpty()) {
        throw new IllegalArgumentException("host cannot be empty");
      }
      return new MetadataAI(this);
    }
  }
}
