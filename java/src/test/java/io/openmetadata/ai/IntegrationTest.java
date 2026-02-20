package io.openmetadata.ai;

import static org.junit.jupiter.api.Assertions.*;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.UUID;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;

import io.openmetadata.ai.exceptions.AuthenticationException;
import io.openmetadata.ai.exceptions.BotNotFoundException;
import io.openmetadata.ai.exceptions.MetadataException;
import io.openmetadata.ai.exceptions.PersonaNotFoundException;
import io.openmetadata.ai.models.*;

/**
 * Integration tests for Metadata AI Java SDK.
 *
 * <p>These tests run against a real Metadata instance and require: - METADATA_HOST: Base URL of the
 * Metadata instance - METADATA_TOKEN: JWT authentication token
 *
 * <p>Optional: - METADATA_TEST_AGENT: Name of an agent to test invocation (defaults to first
 * available) - METADATA_RUN_CHAT_TESTS: Set to "true" to run chat tests - invoke and streaming
 * (uses AI tokens)
 *
 * <p>Run with: mvn test -Dtest=IntegrationTest
 */
@EnabledIfEnvironmentVariable(named = "METADATA_HOST", matches = ".+")
@EnabledIfEnvironmentVariable(named = "METADATA_TOKEN", matches = ".+")
public class IntegrationTest {

  private static MetadataAI client;
  private static String testAgentName;

  /** Check if chat tests should run (invoke + streaming - they use AI tokens) */
  private static boolean isChatTestsEnabled() {
    String enabled = System.getenv("METADATA_RUN_CHAT_TESTS");
    return "true".equalsIgnoreCase(enabled);
  }

  /** Generate a unique name for test entities */
  private static String uniqueName(String prefix) {
    return prefix + "-test-" + UUID.randomUUID().toString().substring(0, 8);
  }

  @BeforeAll
  static void setUp() {
    String host = System.getenv("METADATA_HOST");
    String token = System.getenv("METADATA_TOKEN");

    client = MetadataAI.builder().host(host).token(token).build();

    // Get test agent name from env or create one dynamically
    testAgentName = System.getenv("METADATA_TEST_AGENT");
    if (testAgentName == null || testAgentName.isEmpty()) {
      try {
        // First, try to find an existing persona with LLM configured
        List<PersonaInfo> personas = client.listPersonas();
        if (!personas.isEmpty()) {
          String personaName = personas.get(0).getName();
          // Create a test agent with discoveryAndSearch ability
          String agentName = uniqueName("invoke-test-agent");
          CreateAgentRequest.Builder builder =
              CreateAgentRequest.builder()
                  .name(agentName)
                  .description("Auto-created agent for integration testing")
                  .persona(personaName)
                  .mode("chat")
                  .apiEnabled(true) // Enable API access for invoke/stream
                  .abilities(Arrays.asList("discoveryAndSearch"));
          client.createAgent(builder);
          testAgentName = agentName;
          System.out.println("Created test agent: " + testAgentName);
        } else {
          // Fallback to first available agent
          List<AgentInfo> agents = client.listAgents();
          if (!agents.isEmpty()) {
            testAgentName = agents.get(0).getName();
          }
        }
      } catch (MetadataException e) {
        // Will be handled in individual tests
        System.out.println("Failed to create test agent: " + e.getMessage());
      }
    }
  }

  // ==================== Connection Tests ====================

  @Nested
  @DisplayName("Connection Tests")
  class ConnectionTests {

    @Test
    @DisplayName("Client can be created and list agents")
    void testClientCreation() {
      assertNotNull(client);
      List<AgentInfo> agents = client.listAgents();
      assertNotNull(agents);
    }

    @Test
    @DisplayName("List agents returns a list")
    void testListAgents() {
      List<AgentInfo> agents = client.listAgents();
      assertNotNull(agents);
      System.out.println("Found " + agents.size() + " API-enabled agents");
    }

    @Test
    @DisplayName("Invalid token is rejected with AuthenticationException")
    void testInvalidTokenRejected() {
      MetadataAI badClient =
          MetadataAI.builder()
              .host(System.getenv("METADATA_HOST"))
              .token("invalid-token-12345")
              .build();

      assertThrows(AuthenticationException.class, badClient::listAgents);
    }
  }

  // ==================== Agent Operations Tests ====================

  @Nested
  @DisplayName("Agent Operations Tests")
  class AgentOperationsTests {

    @Test
    @DisplayName("Get agent info returns correct agent")
    void testGetAgentInfo() {
      if (testAgentName == null) {
        System.out.println("Skipping: No test agent available");
        return;
      }

      AgentHandle agent = client.agent(testAgentName);
      AgentInfo info = agent.info();

      assertNotNull(info);
      assertEquals(testAgentName, info.getName());
      System.out.println(
          "Agent '"
              + testAgentName
              + "' info: "
              + (info.getDescription() != null ? info.getDescription() : "No description"));
    }

    @Test
    @DisplayName("Invoke agent returns response")
    void testInvokeAgent() {
      if (!isChatTestsEnabled()) {
        System.out.println(
            "Skipping: Chat tests disabled (set METADATA_RUN_CHAT_TESTS=true to enable)");
        return;
      }
      if (testAgentName == null) {
        System.out.println("Skipping: No test agent available");
        return;
      }

      AgentHandle agent = client.agent(testAgentName);
      InvokeResponse response =
          agent.invoke("Hello, this is an integration test. Please respond briefly.");

      assertNotNull(response);
      assertNotNull(response.getResponse());
      assertFalse(response.getResponse().isEmpty());
      System.out.println(
          "Agent response: "
              + response.getResponse().substring(0, Math.min(200, response.getResponse().length()))
              + "...");
    }

    @Test
    @DisplayName("Stream agent returns chunks")
    void testStreamAgent() {
      if (!isChatTestsEnabled()) {
        System.out.println(
            "Skipping: Chat tests disabled (set METADATA_RUN_CHAT_TESTS=true to enable)");
        return;
      }
      if (testAgentName == null || testAgentName.isEmpty()) {
        System.out.println("Skipping: No test agent available");
        return;
      }

      AgentHandle agent = client.agent(testAgentName);
      List<String> chunks = new ArrayList<>();

      // Use a prompt that triggers tool use with discoveryAndSearch ability
      agent.stream(
          "do we have any customer data",
          event -> {
            if (event.getContent() != null) {
              chunks.add(event.getContent());
            }
          });

      assertFalse(chunks.isEmpty());
      String fullResponse = String.join("", chunks);
      System.out.println(
          "Streamed response: "
              + fullResponse.substring(0, Math.min(200, fullResponse.length()))
              + "...");
    }

    @Test
    @DisplayName("Stream iterator returns chunks")
    void testStreamIterator() {
      if (!isChatTestsEnabled()) {
        System.out.println(
            "Skipping: Chat tests disabled (set METADATA_RUN_CHAT_TESTS=true to enable)");
        return;
      }
      if (testAgentName == null || testAgentName.isEmpty()) {
        System.out.println("Skipping: No test agent available");
        return;
      }

      AgentHandle agent = client.agent(testAgentName);
      List<String> chunks = new ArrayList<>();

      try (var stream = agent.streamIterator("do we have any customer data")) {
        stream.forEach(
            event -> {
              if (event.getContent() != null) {
                chunks.add(event.getContent());
              }
            });
      }

      assertFalse(chunks.isEmpty());
      String fullResponse = String.join("", chunks);
      System.out.println(
          "Streamed (iterator) response: "
              + fullResponse.substring(0, Math.min(200, fullResponse.length()))
              + "...");
    }
  }

  // ==================== Persona Operations Tests ====================

  @Nested
  @DisplayName("Persona Operations Tests")
  class PersonaOperationsTests {

    @Test
    @DisplayName("List personas returns a list")
    void testListPersonas() {
      List<PersonaInfo> personas = client.listPersonas();
      assertNotNull(personas);
      System.out.println("Found " + personas.size() + " personas");
    }

    @Test
    @DisplayName("List personas with limit respects limit")
    void testListPersonasWithLimit() {
      List<PersonaInfo> personas = client.listPersonas(5);
      assertNotNull(personas);
      assertTrue(personas.size() <= 5);
    }

    @Test
    @DisplayName("Get persona by name returns correct persona")
    void testGetPersona() {
      List<PersonaInfo> personas = client.listPersonas();
      if (personas.isEmpty()) {
        System.out.println("Skipping: No personas available");
        return;
      }

      String personaName = personas.get(0).getName();
      PersonaInfo persona = client.getPersona(personaName);

      assertNotNull(persona);
      assertEquals(personaName, persona.getName());
      System.out.println(
          "Got persona: "
              + persona.getName()
              + " ("
              + (persona.getDisplayName() != null ? persona.getDisplayName() : "No display name")
              + ")");
    }

    @Test
    @DisplayName("Get non-existent persona throws PersonaNotFoundException")
    void testGetPersonaNotFound() {
      assertThrows(
          PersonaNotFoundException.class, () -> client.getPersona("non-existent-persona-12345"));
    }

    @Test
    @DisplayName("Create persona creates new persona")
    void testCreatePersona() {
      String personaName = uniqueName("persona");
      CreatePersonaRequest request =
          CreatePersonaRequest.builder()
              .name(personaName)
              .description("Integration test persona")
              .prompt("You are a helpful test assistant.")
              .displayName("Test Persona")
              .build();

      PersonaInfo created = client.createPersona(request);

      assertNotNull(created);
      assertEquals(personaName, created.getName());
      assertEquals("Integration test persona", created.getDescription());
      System.out.println("Created persona: " + created.getName());
    }
  }

  // ==================== Bot Operations Tests ====================

  @Nested
  @DisplayName("Bot Operations Tests")
  class BotOperationsTests {

    @Test
    @DisplayName("List bots returns a list")
    void testListBots() {
      List<BotInfo> bots = client.listBots();
      assertNotNull(bots);
      System.out.println("Found " + bots.size() + " bots");
    }

    @Test
    @DisplayName("List bots with limit respects limit")
    void testListBotsWithLimit() {
      List<BotInfo> bots = client.listBots(5);
      assertNotNull(bots);
      assertTrue(bots.size() <= 5);
    }

    @Test
    @DisplayName("Get bot by name returns correct bot")
    void testGetBot() {
      List<BotInfo> bots = client.listBots();
      if (bots.isEmpty()) {
        System.out.println("Skipping: No bots available");
        return;
      }

      String botName = bots.get(0).getName();
      BotInfo bot = client.getBot(botName);

      assertNotNull(bot);
      assertEquals(botName, bot.getName());
      System.out.println(
          "Got bot: "
              + bot.getName()
              + " ("
              + (bot.getDisplayName() != null ? bot.getDisplayName() : "No display name")
              + ")");
    }

    @Test
    @DisplayName("Get non-existent bot throws BotNotFoundException")
    void testGetBotNotFound() {
      assertThrows(BotNotFoundException.class, () -> client.getBot("non-existent-bot-12345"));
    }
  }

  // ==================== Ability Operations Tests ====================

  @Nested
  @DisplayName("Ability Operations Tests")
  class AbilityOperationsTests {

    @Test
    @DisplayName("List abilities returns a list")
    void testListAbilities() {
      List<AbilityInfo> abilities = client.listAbilities();
      assertNotNull(abilities);
      System.out.println("Found " + abilities.size() + " abilities");
    }

    @Test
    @DisplayName("List abilities with limit respects limit")
    void testListAbilitiesWithLimit() {
      List<AbilityInfo> abilities = client.listAbilities(5);
      assertNotNull(abilities);
      assertTrue(abilities.size() <= 5);
    }

    @Test
    @DisplayName("Abilities have expected fields")
    void testAbilityFields() {
      List<AbilityInfo> abilities = client.listAbilities();
      if (abilities.isEmpty()) {
        System.out.println("Skipping: No abilities available");
        return;
      }

      AbilityInfo ability = abilities.get(0);
      assertNotNull(ability.getName());
      System.out.println("Ability: " + ability.getName());
    }
  }

  // ==================== Agent CRUD Operations Tests ====================

  @Nested
  @DisplayName("Agent CRUD Operations Tests")
  class AgentCRUDOperationsTests {

    @Test
    @DisplayName("Create agent creates new agent")
    void testCreateAgent() {
      List<PersonaInfo> personas = client.listPersonas();
      if (personas.isEmpty()) {
        System.out.println("Skipping: No personas available to create agent");
        return;
      }

      String agentName = uniqueName("agent");
      CreateAgentRequest.Builder builder =
          CreateAgentRequest.builder()
              .name(agentName)
              .description("Integration test agent")
              .persona(personas.get(0).getName())
              .mode("chat")
              .apiEnabled(true);

      AgentInfo created = client.createAgent(builder);

      assertNotNull(created);
      assertEquals(agentName, created.getName());
      System.out.println("Created agent: " + created.getName());
    }

    @Test
    @DisplayName("Create agent with abilities")
    void testCreateAgentWithAbilities() {
      List<PersonaInfo> personas = client.listPersonas();
      List<AbilityInfo> abilities = client.listAbilities();

      if (personas.isEmpty()) {
        System.out.println("Skipping: No personas available");
        return;
      }
      if (abilities.isEmpty()) {
        System.out.println("Skipping: No abilities available");
        return;
      }

      String agentName = uniqueName("agent-abilities");
      List<String> abilityNames =
          abilities.stream()
              .limit(2)
              .map(AbilityInfo::getName)
              .collect(java.util.stream.Collectors.toList());

      CreateAgentRequest.Builder builder =
          CreateAgentRequest.builder()
              .name(agentName)
              .description("Integration test agent with abilities")
              .persona(personas.get(0).getName())
              .mode("agent")
              .abilities(abilityNames)
              .apiEnabled(true);

      AgentInfo created = client.createAgent(builder);

      assertNotNull(created);
      assertEquals(agentName, created.getName());
      System.out.println("Created agent with abilities: " + created.getName());
    }
  }
}
