package io.openmetadata.ai.internal;

import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Consumer;
import java.util.stream.Stream;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import io.openmetadata.ai.exceptions.*;
import io.openmetadata.ai.models.*;

/** Internal HTTP client for communicating with the AI SDK API. */
public class AISdkHttpClient implements AutoCloseable {

  private static final String API_BASE_PATH = "/api/v1/agents/dynamic";
  private static final String BOTS_API_PATH = "/api/v1/bots";
  private static final String PERSONAS_API_PATH = "/api/v1/agents/personas";
  private static final String ABILITIES_API_PATH = "/api/v1/agents/abilities";
  private static final String CONTENT_TYPE_JSON = "application/json";
  private static final String ACCEPT_SSE = "text/event-stream";

  private final String host;
  private final String baseUrl;
  private final String token;
  private final HttpClient httpClient;
  private final ObjectMapper objectMapper;
  private final SseParser sseParser;
  private final int maxRetries;
  private final Duration retryDelay;

  public AISdkHttpClient(
      String host, String token, Duration timeout, int maxRetries, Duration retryDelay) {
    this.host = normalizeHost(host);
    this.baseUrl = this.host + API_BASE_PATH;
    this.token = token;
    this.httpClient = HttpClient.newBuilder().connectTimeout(timeout).build();
    this.objectMapper = new ObjectMapper();
    this.sseParser = new SseParser(objectMapper);
    this.maxRetries = maxRetries;
    this.retryDelay = retryDelay;
  }

  private String normalizeHost(String host) {
    if (host.endsWith("/")) {
      return host.substring(0, host.length() - 1);
    }
    return host;
  }

  /**
   * Lists all API-enabled agents with pagination. Automatically fetches all pages.
   *
   * @return a list of all agent information
   */
  public List<AgentInfo> listAgents() {
    return listAgents(null);
  }

  /**
   * Lists API-enabled agents with optional limit. Automatically paginates through all results.
   *
   * @param limit the maximum number of agents to return, or null for all
   * @return a list of agent information
   */
  public List<AgentInfo> listAgents(Integer limit) {
    return paginateList(
        baseUrl + "?apiEnabled=true", limit, new TypeReference<List<AgentInfo>>() {});
  }

  /**
   * Lists all API-enabled agents with pagination (deprecated, use listAgents() instead).
   *
   * @param limit the maximum number of agents to return per page
   * @param offset ignored - use listAgents(Integer limit) for limiting results
   * @return a list of agent information
   * @deprecated Use listAgents() or listAgents(Integer limit) instead
   */
  @Deprecated
  public List<AgentInfo> listAgents(int limit, int offset) {
    // For backwards compatibility, just return a single page
    String url = baseUrl + "?limit=" + limit + "&offset=" + offset;
    HttpRequest request =
        HttpRequest.newBuilder()
            .uri(URI.create(url))
            .header("Authorization", "Bearer " + token)
            .header("Accept", CONTENT_TYPE_JSON)
            .GET()
            .build();

    HttpResponse<String> response = executeWithRetry(request);
    try {
      JsonNode root = objectMapper.readTree(response.body());
      JsonNode data = root.get("data");
      if (data == null || !data.isArray()) {
        return new ArrayList<>();
      }
      return objectMapper.convertValue(data, new TypeReference<List<AgentInfo>>() {});
    } catch (JsonProcessingException e) {
      throw new AISdkException("Failed to parse agent list response", e);
    }
  }

  /** Paginates through all results from a list endpoint. */
  private <T> List<T> paginateList(String baseUrl, Integer limit, TypeReference<List<T>> typeRef) {
    List<T> results = new ArrayList<>();
    String after = null;
    int pageSize = 100;

    while (true) {
      StringBuilder urlBuilder = new StringBuilder(baseUrl);
      String separator = baseUrl.contains("?") ? "&" : "?";
      urlBuilder.append(separator).append("limit=").append(pageSize);
      if (after != null) {
        urlBuilder.append("&after=").append(URLEncoder.encode(after, StandardCharsets.UTF_8));
      }

      HttpRequest request =
          HttpRequest.newBuilder()
              .uri(URI.create(urlBuilder.toString()))
              .header("Authorization", "Bearer " + token)
              .header("Accept", CONTENT_TYPE_JSON)
              .GET()
              .build();

      HttpResponse<String> response = executeWithRetry(request);
      try {
        JsonNode root = objectMapper.readTree(response.body());
        JsonNode data = root.get("data");
        if (data != null && data.isArray()) {
          List<T> page = objectMapper.convertValue(data, typeRef);
          results.addAll(page);
        }

        // Check if we've hit the limit
        if (limit != null && results.size() >= limit) {
          return results.subList(0, Math.min(results.size(), limit));
        }

        // Check for more pages
        JsonNode paging = root.get("paging");
        if (paging != null && paging.has("after") && !paging.get("after").isNull()) {
          after = paging.get("after").asText();
        } else {
          break;
        }
      } catch (JsonProcessingException e) {
        throw new AISdkException("Failed to parse list response", e);
      }
    }

    return results;
  }

  /** Gets information about a specific agent. */
  public AgentInfo getAgent(String agentName) {
    String encodedName = URLEncoder.encode(agentName, StandardCharsets.UTF_8);
    HttpRequest request =
        HttpRequest.newBuilder()
            .uri(URI.create(baseUrl + "/name/" + encodedName))
            .header("Authorization", "Bearer " + token)
            .header("Accept", CONTENT_TYPE_JSON)
            .GET()
            .build();

    HttpResponse<String> response = executeWithRetry(request, agentName);
    try {
      return objectMapper.readValue(response.body(), AgentInfo.class);
    } catch (JsonProcessingException e) {
      throw new AISdkException("Failed to parse agent response", e);
    }
  }

  /** Invokes an agent synchronously. */
  public InvokeResponse invoke(String agentName, InvokeRequest invokeRequest) {
    String encodedName = URLEncoder.encode(agentName, StandardCharsets.UTF_8);
    String requestBody;
    try {
      requestBody = objectMapper.writeValueAsString(invokeRequest);
    } catch (JsonProcessingException e) {
      throw new AISdkException("Failed to serialize request", e);
    }

    HttpRequest request =
        HttpRequest.newBuilder()
            .uri(URI.create(baseUrl + "/name/" + encodedName + "/invoke"))
            .header("Authorization", "Bearer " + token)
            .header("Content-Type", CONTENT_TYPE_JSON)
            .header("Accept", CONTENT_TYPE_JSON)
            .POST(HttpRequest.BodyPublishers.ofString(requestBody))
            .build();

    HttpResponse<String> response = executeWithRetry(request, agentName);
    try {
      return objectMapper.readValue(response.body(), InvokeResponse.class);
    } catch (JsonProcessingException e) {
      throw new AISdkException("Failed to parse invoke response", e);
    }
  }

  /** Invokes an agent with streaming, calling the consumer for each event. */
  public void stream(
      String agentName, InvokeRequest invokeRequest, Consumer<StreamEvent> eventConsumer) {
    String encodedName = URLEncoder.encode(agentName, StandardCharsets.UTF_8);
    String requestBody;
    try {
      requestBody = objectMapper.writeValueAsString(invokeRequest);
    } catch (JsonProcessingException e) {
      throw new AISdkException("Failed to serialize request", e);
    }

    HttpRequest request =
        HttpRequest.newBuilder()
            .uri(URI.create(baseUrl + "/name/" + encodedName + "/stream"))
            .header("Authorization", "Bearer " + token)
            .header("Content-Type", CONTENT_TYPE_JSON)
            .header("Accept", ACCEPT_SSE)
            .POST(HttpRequest.BodyPublishers.ofString(requestBody))
            .build();

    try {
      HttpResponse<InputStream> response =
          httpClient.send(request, HttpResponse.BodyHandlers.ofInputStream());
      handleErrorStatus(response.statusCode(), agentName, parseRetryAfter(response));

      try (InputStream inputStream = response.body()) {
        sseParser.parse(inputStream, eventConsumer);
      }
    } catch (AISdkException e) {
      throw e;
    } catch (IOException | InterruptedException e) {
      if (e instanceof InterruptedException) {
        Thread.currentThread().interrupt();
      }
      throw new AISdkException("Stream request failed: " + e.getMessage(), e);
    }
  }

  /**
   * Invokes an agent with streaming, returning a Stream of events. The caller must close the
   * returned Stream when done.
   */
  public Stream<StreamEvent> streamIterator(String agentName, InvokeRequest invokeRequest) {
    String encodedName = URLEncoder.encode(agentName, StandardCharsets.UTF_8);
    String requestBody;
    try {
      requestBody = objectMapper.writeValueAsString(invokeRequest);
    } catch (JsonProcessingException e) {
      throw new AISdkException("Failed to serialize request", e);
    }

    HttpRequest request =
        HttpRequest.newBuilder()
            .uri(URI.create(baseUrl + "/name/" + encodedName + "/stream"))
            .header("Authorization", "Bearer " + token)
            .header("Content-Type", CONTENT_TYPE_JSON)
            .header("Accept", ACCEPT_SSE)
            .POST(HttpRequest.BodyPublishers.ofString(requestBody))
            .build();

    try {
      HttpResponse<InputStream> response =
          httpClient.send(request, HttpResponse.BodyHandlers.ofInputStream());
      handleErrorStatus(response.statusCode(), agentName, parseRetryAfter(response));

      return sseParser.parseAsStream(response.body());
    } catch (AISdkException e) {
      throw e;
    } catch (IOException | InterruptedException e) {
      if (e instanceof InterruptedException) {
        Thread.currentThread().interrupt();
      }
      throw new AISdkException("Stream request failed: " + e.getMessage(), e);
    }
  }

  // ==================== Bot Operations ====================

  /**
   * Lists all bots with automatic pagination.
   *
   * @return a list of all bot information
   */
  public List<BotInfo> listBots() {
    return listBots(null);
  }

  /**
   * Lists bots with optional limit. Automatically paginates through all results.
   *
   * @param limit the maximum number of bots to return, or null for all
   * @return a list of bot information
   */
  public List<BotInfo> listBots(Integer limit) {
    return paginateList(host + BOTS_API_PATH, limit, new TypeReference<List<BotInfo>>() {});
  }

  /**
   * Gets a bot by name.
   *
   * @param name the name of the bot
   * @return the bot information
   * @throws BotNotFoundException if the bot is not found
   */
  public BotInfo getBotByName(String name) {
    String encodedName = URLEncoder.encode(name, StandardCharsets.UTF_8);
    String url = host + BOTS_API_PATH + "/name/" + encodedName;
    HttpRequest request =
        HttpRequest.newBuilder()
            .uri(URI.create(url))
            .header("Authorization", "Bearer " + token)
            .header("Accept", CONTENT_TYPE_JSON)
            .GET()
            .build();

    HttpResponse<String> response = executeWithRetryForResource(request, ResourceType.BOT, name);
    try {
      return objectMapper.readValue(response.body(), BotInfo.class);
    } catch (JsonProcessingException e) {
      throw new AISdkException("Failed to parse bot response", e);
    }
  }

  // ==================== Persona Operations ====================

  /**
   * Lists all personas with automatic pagination.
   *
   * @return a list of all persona information
   */
  public List<PersonaInfo> listPersonas() {
    return listPersonas(null);
  }

  /**
   * Lists personas with optional limit. Automatically paginates through all results.
   *
   * @param limit the maximum number of personas to return, or null for all
   * @return a list of persona information
   */
  public List<PersonaInfo> listPersonas(Integer limit) {
    return paginateList(host + PERSONAS_API_PATH, limit, new TypeReference<List<PersonaInfo>>() {});
  }

  /**
   * Gets a persona by name.
   *
   * @param name the name of the persona
   * @return the persona information
   * @throws PersonaNotFoundException if the persona is not found
   */
  public PersonaInfo getPersonaByName(String name) {
    String encodedName = URLEncoder.encode(name, StandardCharsets.UTF_8);
    String url = host + PERSONAS_API_PATH + "/name/" + encodedName;
    HttpRequest request =
        HttpRequest.newBuilder()
            .uri(URI.create(url))
            .header("Authorization", "Bearer " + token)
            .header("Accept", CONTENT_TYPE_JSON)
            .GET()
            .build();

    HttpResponse<String> response =
        executeWithRetryForResource(request, ResourceType.PERSONA, name);
    try {
      return objectMapper.readValue(response.body(), PersonaInfo.class);
    } catch (JsonProcessingException e) {
      throw new AISdkException("Failed to parse persona response", e);
    }
  }

  /**
   * Creates a new persona.
   *
   * @param createRequest the request to create the persona
   * @return the created persona information
   */
  public PersonaInfo createPersona(CreatePersonaRequest createRequest) {
    String requestBody;
    try {
      requestBody = objectMapper.writeValueAsString(createRequest);
    } catch (JsonProcessingException e) {
      throw new AISdkException("Failed to serialize persona create request", e);
    }

    String url = host + PERSONAS_API_PATH;
    HttpRequest request =
        HttpRequest.newBuilder()
            .uri(URI.create(url))
            .header("Authorization", "Bearer " + token)
            .header("Content-Type", CONTENT_TYPE_JSON)
            .header("Accept", CONTENT_TYPE_JSON)
            .POST(HttpRequest.BodyPublishers.ofString(requestBody))
            .build();

    HttpResponse<String> response =
        executeWithRetryForResource(request, ResourceType.PERSONA, null);
    try {
      return objectMapper.readValue(response.body(), PersonaInfo.class);
    } catch (JsonProcessingException e) {
      throw new AISdkException("Failed to parse persona create response", e);
    }
  }

  // ==================== Agent Operations ====================

  /**
   * Creates a new dynamic agent.
   *
   * @param createRequest the request to create the agent
   * @return the created agent information
   */
  public AgentInfo createAgent(CreateAgentRequest createRequest) {
    String requestBody;
    try {
      requestBody = objectMapper.writeValueAsString(createRequest);
    } catch (JsonProcessingException e) {
      throw new AISdkException("Failed to serialize agent create request", e);
    }

    HttpRequest request =
        HttpRequest.newBuilder()
            .uri(URI.create(baseUrl))
            .header("Authorization", "Bearer " + token)
            .header("Content-Type", CONTENT_TYPE_JSON)
            .header("Accept", CONTENT_TYPE_JSON)
            .POST(HttpRequest.BodyPublishers.ofString(requestBody))
            .build();

    HttpResponse<String> response = executeWithRetryForResource(request, ResourceType.AGENT, null);
    try {
      return objectMapper.readValue(response.body(), AgentInfo.class);
    } catch (JsonProcessingException e) {
      throw new AISdkException("Failed to parse agent create response", e);
    }
  }

  // ==================== Ability Operations ====================

  /**
   * Lists all abilities with automatic pagination.
   *
   * @return a list of all ability information
   */
  public List<AbilityInfo> listAbilities() {
    return listAbilities(null);
  }

  /**
   * Lists abilities with optional limit. Automatically paginates through all results.
   *
   * @param limit the maximum number of abilities to return, or null for all
   * @return a list of ability information
   */
  public List<AbilityInfo> listAbilities(Integer limit) {
    return paginateList(
        host + ABILITIES_API_PATH, limit, new TypeReference<List<AbilityInfo>>() {});
  }

  /**
   * Gets an ability by name.
   *
   * @param name the name of the ability
   * @return the ability information
   * @throws AbilityNotFoundException if the ability is not found
   */
  public AbilityInfo getAbilityByName(String name) {
    String encodedName = URLEncoder.encode(name, StandardCharsets.UTF_8);
    String url = host + ABILITIES_API_PATH + "/name/" + encodedName;
    HttpRequest request =
        HttpRequest.newBuilder()
            .uri(URI.create(url))
            .header("Authorization", "Bearer " + token)
            .header("Accept", CONTENT_TYPE_JSON)
            .GET()
            .build();

    HttpResponse<String> response =
        executeWithRetryForResource(request, ResourceType.ABILITY, name);
    try {
      return objectMapper.readValue(response.body(), AbilityInfo.class);
    } catch (JsonProcessingException e) {
      throw new AISdkException("Failed to parse ability response", e);
    }
  }

  // ==================== Internal Helpers ====================

  private enum ResourceType {
    AGENT,
    BOT,
    PERSONA,
    ABILITY
  }

  private HttpResponse<String> executeWithRetryForResource(
      HttpRequest request, ResourceType resourceType, String resourceName) {
    int attempts = 0;
    Exception lastException = null;

    while (attempts <= maxRetries) {
      try {
        HttpResponse<String> response =
            httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        handleErrorStatusForResource(
            response.statusCode(), resourceType, resourceName, parseRetryAfter(response));
        return response;
      } catch (RateLimitException e) {
        lastException = e;
        attempts++;
        if (attempts <= maxRetries) {
          Duration waitTime = e.getRetryAfter().map(Duration::ofSeconds).orElse(retryDelay);
          sleep(waitTime);
        }
      } catch (AISdkException e) {
        throw e;
      } catch (IOException | InterruptedException e) {
        if (e instanceof InterruptedException) {
          Thread.currentThread().interrupt();
          throw new AISdkException("Request interrupted", e);
        }
        lastException = e;
        attempts++;
        if (attempts <= maxRetries) {
          sleep(retryDelay);
        }
      }
    }

    if (lastException instanceof AISdkException) {
      throw (AISdkException) lastException;
    }
    throw new AISdkException("Request failed after " + maxRetries + " retries", lastException);
  }

  private void handleErrorStatusForResource(
      int statusCode, ResourceType resourceType, String resourceName, Integer retryAfter) {
    switch (statusCode) {
      case 200:
      case 201:
        return;
      case 401:
        throw new AuthenticationException();
      case 403:
        if (resourceType == ResourceType.AGENT) {
          throw new AgentNotEnabledException(resourceName != null ? resourceName : "unknown");
        }
        throw new AISdkException("Access forbidden", 403);
      case 404:
        switch (resourceType) {
          case BOT:
            throw new BotNotFoundException(resourceName != null ? resourceName : "unknown");
          case PERSONA:
            throw new PersonaNotFoundException(resourceName != null ? resourceName : "unknown");
          case ABILITY:
            throw new AbilityNotFoundException(resourceName != null ? resourceName : "unknown");
          case AGENT:
          default:
            throw new AgentNotFoundException(resourceName != null ? resourceName : "unknown");
        }
      case 429:
        throw new RateLimitException("Rate limit exceeded", retryAfter);
      default:
        if (statusCode >= 400) {
          throw new AISdkException("Request failed with status " + statusCode, statusCode);
        }
    }
  }

  private HttpResponse<String> executeWithRetry(HttpRequest request) {
    return executeWithRetry(request, null);
  }

  private HttpResponse<String> executeWithRetry(HttpRequest request, String agentName) {
    int attempts = 0;
    Exception lastException = null;

    while (attempts <= maxRetries) {
      try {
        HttpResponse<String> response =
            httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        handleErrorStatus(response.statusCode(), agentName, parseRetryAfter(response));
        return response;
      } catch (RateLimitException e) {
        lastException = e;
        attempts++;
        if (attempts <= maxRetries) {
          Duration waitTime = e.getRetryAfter().map(Duration::ofSeconds).orElse(retryDelay);
          sleep(waitTime);
        }
      } catch (AISdkException e) {
        throw e;
      } catch (IOException | InterruptedException e) {
        if (e instanceof InterruptedException) {
          Thread.currentThread().interrupt();
          throw new AISdkException("Request interrupted", e);
        }
        lastException = e;
        attempts++;
        if (attempts <= maxRetries) {
          sleep(retryDelay);
        }
      }
    }

    if (lastException instanceof AISdkException) {
      throw (AISdkException) lastException;
    }
    throw new AISdkException("Request failed after " + maxRetries + " retries", lastException);
  }

  private void handleErrorStatus(int statusCode, String agentName, Integer retryAfter) {
    switch (statusCode) {
      case 200:
      case 201:
        return;
      case 401:
        throw new AuthenticationException();
      case 403:
        throw new AgentNotEnabledException(agentName != null ? agentName : "unknown");
      case 404:
        throw new AgentNotFoundException(agentName != null ? agentName : "unknown");
      case 429:
        throw new RateLimitException("Rate limit exceeded", retryAfter);
      default:
        if (statusCode >= 400) {
          throw new AISdkException("Request failed with status " + statusCode, statusCode);
        }
    }
  }

  private static Integer parseRetryAfter(HttpResponse<?> response) {
    return response
        .headers()
        .firstValue("Retry-After")
        .map(
            value -> {
              try {
                return Integer.parseInt(value.trim());
              } catch (NumberFormatException e) {
                return null;
              }
            })
        .orElse(null);
  }

  private void sleep(Duration duration) {
    try {
      Thread.sleep(duration.toMillis());
    } catch (InterruptedException e) {
      Thread.currentThread().interrupt();
    }
  }

  @Override
  public void close() {
    // HttpClient doesn't need explicit closing in Java 11+
    // but we keep this for consistency and future compatibility
  }
}
