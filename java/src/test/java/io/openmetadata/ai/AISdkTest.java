package io.openmetadata.ai;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

import java.time.Duration;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import io.openmetadata.ai.exceptions.*;
import io.openmetadata.ai.internal.AISdkHttpClient;
import io.openmetadata.ai.models.*;

/** Unit tests for the AI SDK. */
class AISdkTest {

  // ==================== Builder Tests ====================

  @Test
  @DisplayName("Builder creates client with required parameters")
  void builderCreatesClientWithRequiredParameters() {
    AISdk client = AISdk.builder().host("https://metadata.example.com").token("test-token").build();

    assertNotNull(client);
    client.close();
  }

  @Test
  @DisplayName("Builder throws exception when host is null")
  void builderThrowsWhenHostIsNull() {
    assertThrows(NullPointerException.class, () -> AISdk.builder().token("test-token").build());
  }

  @Test
  @DisplayName("Builder throws exception when token is null")
  void builderThrowsWhenTokenIsNull() {
    assertThrows(
        NullPointerException.class,
        () -> AISdk.builder().host("https://metadata.example.com").build());
  }

  @Test
  @DisplayName("Builder throws exception when host is empty")
  void builderThrowsWhenHostIsEmpty() {
    assertThrows(
        IllegalArgumentException.class, () -> AISdk.builder().host("").token("test-token").build());
  }

  @Test
  @DisplayName("Builder accepts optional timeout")
  void builderAcceptsOptionalTimeout() {
    AISdk client =
        AISdk.builder()
            .host("https://metadata.example.com")
            .token("test-token")
            .timeout(Duration.ofSeconds(60))
            .build();

    assertNotNull(client);
    client.close();
  }

  @Test
  @DisplayName("Builder accepts optional maxRetries")
  void builderAcceptsOptionalMaxRetries() {
    AISdk client =
        AISdk.builder()
            .host("https://metadata.example.com")
            .token("test-token")
            .maxRetries(5)
            .build();

    assertNotNull(client);
    client.close();
  }

  @Test
  @DisplayName("Builder accepts optional retryDelay")
  void builderAcceptsOptionalRetryDelay() {
    AISdk client =
        AISdk.builder()
            .host("https://metadata.example.com")
            .token("test-token")
            .retryDelay(Duration.ofSeconds(2))
            .build();

    assertNotNull(client);
    client.close();
  }

  @Test
  @DisplayName("Builder accepts all optional parameters")
  void builderAcceptsAllOptionalParameters() {
    AISdk client =
        AISdk.builder()
            .host("https://metadata.example.com")
            .token("test-token")
            .timeout(Duration.ofSeconds(60))
            .maxRetries(5)
            .retryDelay(Duration.ofSeconds(2))
            .build();

    assertNotNull(client);
    client.close();
  }

  // ==================== Agent Handle Tests ====================

  @Test
  @DisplayName("Agent method returns a handle")
  void agentMethodReturnsHandle() {
    AISdk client = AISdk.builder().host("https://metadata.example.com").token("test-token").build();

    AgentHandle handle = client.agent("test-agent");
    assertNotNull(handle);
    client.close();
  }

  @Test
  @DisplayName("Agent method throws on null name")
  void agentMethodThrowsOnNullName() {
    AISdk client = AISdk.builder().host("https://metadata.example.com").token("test-token").build();

    assertThrows(NullPointerException.class, () -> client.agent(null));
    client.close();
  }

  // ==================== Bot Method Tests ====================

  @Test
  @DisplayName("getBot method throws on null name")
  void getBotMethodThrowsOnNullName() {
    AISdk client = AISdk.builder().host("https://metadata.example.com").token("test-token").build();

    assertThrows(NullPointerException.class, () -> client.bots().get(null));
    client.close();
  }

  // ==================== Persona Method Tests ====================

  @Test
  @DisplayName("getPersona method throws on null name")
  void getPersonaMethodThrowsOnNullName() {
    AISdk client = AISdk.builder().host("https://metadata.example.com").token("test-token").build();

    assertThrows(NullPointerException.class, () -> client.personas().get(null));
    client.close();
  }

  @Test
  @DisplayName("createPersona method throws on null request")
  void createPersonaMethodThrowsOnNullRequest() {
    AISdk client = AISdk.builder().host("https://metadata.example.com").token("test-token").build();

    assertThrows(NullPointerException.class, () -> client.personas().create(null));
    client.close();
  }

  // ==================== Skill Method Tests ====================

  @Test
  @DisplayName("getSkill method throws on null name")
  void getSkillMethodThrowsOnNullName() {
    AISdk client = AISdk.builder().host("https://metadata.example.com").token("test-token").build();

    assertThrows(NullPointerException.class, () -> client.skills().get(null));
    client.close();
  }

  // ==================== AutoCloseable Tests ====================

  @Test
  @DisplayName("Client can be used with try-with-resources")
  void clientCanBeUsedWithTryWithResources() {
    try (AISdk client =
        AISdk.builder().host("https://metadata.example.com").token("test-token").build()) {
      assertNotNull(client);
    }
  }

  // ==================== Model Tests ====================

  @Test
  @DisplayName("InvokeRequest can be built with all fields")
  void invokeRequestCanBeBuiltWithAllFields() {
    Map<String, Object> params = new HashMap<>();
    params.put("key", "value");

    InvokeRequest request =
        InvokeRequest.builder()
            .message("test message")
            .conversationId("conv-123")
            .parameters(params)
            .build();

    assertEquals("test message", request.getMessage());
    assertEquals("conv-123", request.getConversationId());
    assertEquals(params, request.getParameters());
  }

  @Test
  @DisplayName("InvokeRequest can be built with null message")
  void invokeRequestCanBeBuiltWithNullMessage() {
    InvokeRequest request = InvokeRequest.builder().build();
    assertNull(request.getMessage());
  }

  @Test
  @DisplayName("InvokeResponse can be built with all fields")
  void invokeResponseCanBeBuiltWithAllFields() {
    Usage usage = new Usage(100, 50, 150);
    List<String> tools = Arrays.asList("tool1", "tool2");

    InvokeResponse response =
        InvokeResponse.builder()
            .conversationId("conv-123")
            .response("test response")
            .toolsUsed(tools)
            .usage(usage)
            .build();

    assertEquals("conv-123", response.getConversationId());
    assertEquals("test response", response.getResponse());
    assertEquals(tools, response.getToolsUsed());
    assertEquals(usage, response.getUsage());
  }

  @Test
  @DisplayName("InvokeResponse surfaces thinkingSteps when present")
  void invokeResponseSurfacesThinkingSteps() {
    List<String> steps = Arrays.asList("Exploring assets...", "Synthesizing answer...");

    InvokeResponse response =
        InvokeResponse.builder()
            .conversationId("conv-456")
            .response("Found it.")
            .thinkingSteps(steps)
            .build();

    assertEquals("Found it.", response.getResponse());
    assertEquals(steps, response.getThinkingSteps());
  }

  @Test
  @DisplayName("InvokeResponse defaults thinkingSteps to empty list when absent")
  void invokeResponseDefaultsThinkingStepsToEmptyList() {
    InvokeResponse response =
        InvokeResponse.builder().conversationId("conv-789").response("ok").build();

    assertNotNull(response.getThinkingSteps());
    assertTrue(response.getThinkingSteps().isEmpty());
  }

  @Test
  @DisplayName("StreamEvent can be built with all fields")
  void streamEventCanBeBuiltWithAllFields() {
    StreamEvent event =
        StreamEvent.builder()
            .type(StreamEvent.Type.CONTENT)
            .content("test content")
            .toolName("test-tool")
            .conversationId("conv-123")
            .build();

    assertEquals(StreamEvent.Type.CONTENT, event.getType());
    assertEquals("test content", event.getContent());
    assertEquals("test-tool", event.getToolName());
    assertEquals("conv-123", event.getConversationId());
  }

  @Test
  @DisplayName("AgentInfo contains expected fields")
  void agentInfoContainsExpectedFields() {
    AgentInfo info =
        new AgentInfo("test-agent", "Test Agent", "A test agent", Arrays.asList("skill1"), true);

    assertEquals("test-agent", info.getName());
    assertEquals("Test Agent", info.getDisplayName());
    assertEquals("A test agent", info.getDescription());
    assertEquals(Arrays.asList("skill1"), info.getSkills());
    assertTrue(info.isApiEnabled());
  }

  @Test
  @DisplayName("Usage contains expected fields")
  void usageContainsExpectedFields() {
    Usage usage = new Usage(100, 50, 150);

    assertEquals(100, usage.getPromptTokens());
    assertEquals(50, usage.getCompletionTokens());
    assertEquals(150, usage.getTotalTokens());
  }

  // ==================== Bot Model Tests ====================

  @Test
  @DisplayName("BotInfo contains expected fields")
  void botInfoContainsExpectedFields() {
    EntityReference botUser = new EntityReference("user-123", "user", "bot-user", "Bot User");
    BotInfo info = new BotInfo("bot-123", "test-bot", "Test Bot", "A test bot", botUser);

    assertEquals("bot-123", info.getId());
    assertEquals("test-bot", info.getName());
    assertEquals("Test Bot", info.getDisplayName());
    assertEquals("A test bot", info.getDescription());
    assertNotNull(info.getBotUser());
    assertEquals("user-123", info.getBotUser().getId());
  }

  // ==================== Persona Model Tests ====================

  @Test
  @DisplayName("PersonaInfo contains expected fields")
  void personaInfoContainsExpectedFields() {
    PersonaInfo info =
        new PersonaInfo(
            "persona-123",
            "test-persona",
            "Test Persona",
            "A test persona",
            "You are a helpful assistant",
            "system");

    assertEquals("persona-123", info.getId());
    assertEquals("test-persona", info.getName());
    assertEquals("Test Persona", info.getDisplayName());
    assertEquals("A test persona", info.getDescription());
    assertEquals("You are a helpful assistant", info.getPrompt());
    assertEquals("system", info.getProvider());
  }

  @Test
  @DisplayName("CreatePersonaRequest builder validates required fields")
  void createPersonaRequestBuilderValidatesRequiredFields() {
    // Missing name
    assertThrows(
        IllegalArgumentException.class,
        () ->
            CreatePersonaRequest.builder()
                .description("A test persona")
                .prompt("You are helpful")
                .build());

    // Missing description
    assertThrows(
        IllegalArgumentException.class,
        () ->
            CreatePersonaRequest.builder().name("test-persona").prompt("You are helpful").build());

    // Missing prompt
    assertThrows(
        IllegalArgumentException.class,
        () ->
            CreatePersonaRequest.builder()
                .name("test-persona")
                .description("A test persona")
                .build());
  }

  @Test
  @DisplayName("CreatePersonaRequest can be built with all fields")
  void createPersonaRequestCanBeBuiltWithAllFields() {
    CreatePersonaRequest request =
        CreatePersonaRequest.builder()
            .name("test-persona")
            .description("A test persona")
            .prompt("You are a helpful assistant")
            .displayName("Test Persona")
            .provider("user")
            .build();

    assertEquals("test-persona", request.getName());
    assertEquals("A test persona", request.getDescription());
    assertEquals("You are a helpful assistant", request.getPrompt());
    assertEquals("Test Persona", request.getDisplayName());
    assertEquals("user", request.getProvider());
  }

  // ==================== Skill Model Tests ====================

  @Test
  @DisplayName("SkillInfo contains expected fields")
  void skillInfoContainsExpectedFields() {
    SkillInfo info =
        new SkillInfo(
            "skill-123",
            "test-skill",
            "Test Skill",
            "A test skill",
            "system",
            "test-skill-fqn",
            Arrays.asList("tool1", "tool2"));

    assertEquals("skill-123", info.getId());
    assertEquals("test-skill", info.getName());
    assertEquals("Test Skill", info.getDisplayName());
    assertEquals("A test skill", info.getDescription());
    assertEquals("system", info.getProvider());
    assertEquals("test-skill-fqn", info.getFullyQualifiedName());
    assertEquals(Arrays.asList("tool1", "tool2"), info.getTools());
  }

  // ==================== Agent Creation Model Tests ====================

  @Test
  @DisplayName("CreateAgentRequest builder validates required fields")
  void createAgentRequestBuilderValidatesRequiredFields() {
    // Missing name
    assertThrows(
        IllegalArgumentException.class,
        () ->
            CreateAgentRequest.builder()
                .description("A test agent")
                .persona("test-persona")
                .mode("chat")
                .build());

    // Missing description
    assertThrows(
        IllegalArgumentException.class,
        () ->
            CreateAgentRequest.builder()
                .name("test-agent")
                .persona("test-persona")
                .mode("chat")
                .build());

    // Missing persona
    assertThrows(
        IllegalArgumentException.class,
        () ->
            CreateAgentRequest.builder()
                .name("test-agent")
                .description("A test agent")
                .mode("chat")
                .build());

    // Missing mode
    assertThrows(
        IllegalArgumentException.class,
        () ->
            CreateAgentRequest.builder()
                .name("test-agent")
                .description("A test agent")
                .persona("test-persona")
                .build());

    // Invalid mode
    assertThrows(
        IllegalArgumentException.class,
        () ->
            CreateAgentRequest.builder()
                .name("test-agent")
                .description("A test agent")
                .persona("test-persona")
                .mode("invalid")
                .build());
  }

  @Test
  @DisplayName("CreateAgentRequest builder accepts valid modes")
  void createAgentRequestBuilderAcceptsValidModes() {
    // chat mode
    CreateAgentRequest chatRequest =
        CreateAgentRequest.builder()
            .name("test-agent")
            .description("A test agent")
            .persona("test-persona")
            .mode("chat")
            .build();
    assertEquals("chat", chatRequest.getMode());

    // agent mode
    CreateAgentRequest agentRequest =
        CreateAgentRequest.builder()
            .name("test-agent")
            .description("A test agent")
            .persona("test-persona")
            .mode("agent")
            .build();
    assertEquals("agent", agentRequest.getMode());

    // both mode
    CreateAgentRequest bothRequest =
        CreateAgentRequest.builder()
            .name("test-agent")
            .description("A test agent")
            .persona("test-persona")
            .mode("both")
            .build();
    assertEquals("both", bothRequest.getMode());
  }

  @Test
  @DisplayName("CreateAgentRequest can be built with all fields")
  void createAgentRequestCanBeBuiltWithAllFields() {
    KnowledgeScope knowledge =
        KnowledgeScope.builder().entityTypes(Arrays.asList("table", "database")).build();

    CreateAgentRequest request =
        CreateAgentRequest.builder()
            .name("test-agent")
            .description("A test agent")
            .persona("test-persona")
            .mode("agent")
            .displayName("Test Agent")
            .icon("icon.png")
            .botName("test-bot")
            .skills(Arrays.asList("skill1", "skill2"))
            .knowledge(knowledge)
            .prompt("Custom prompt")
            .schedule("0 0 * * *")
            .apiEnabled(true)
            .provider("user")
            .build();

    assertEquals("test-agent", request.getName());
    assertEquals("A test agent", request.getDescription());
    assertEquals("agent", request.getMode());
    assertEquals("Test Agent", request.getDisplayName());
    assertEquals("icon.png", request.getIcon());
    assertEquals("test-bot", request.getBotName());
    assertEquals("Custom prompt", request.getPrompt());
    assertEquals("0 0 * * *", request.getSchedule());
    assertTrue(request.isApiEnabled());
    assertEquals("user", request.getProvider());
  }

  @Test
  @DisplayName("KnowledgeScope can be built")
  void knowledgeScopeCanBeBuilt() {
    EntityReference service =
        EntityReference.builder().id("service-123").type("databaseService").build();

    KnowledgeScope knowledge =
        KnowledgeScope.builder()
            .entityTypes(Arrays.asList("table", "database"))
            .services(Arrays.asList(service))
            .build();

    assertEquals(Arrays.asList("table", "database"), knowledge.getEntityTypes());
    assertEquals(1, knowledge.getServices().size());
    assertEquals("service-123", knowledge.getServices().get(0).getId());
  }

  @Test
  @DisplayName("EntityReference can be built")
  void entityReferenceCanBeBuilt() {
    EntityReference ref =
        EntityReference.builder()
            .id("entity-123")
            .type("persona")
            .name("test-entity")
            .displayName("Test Entity")
            .build();

    assertEquals("entity-123", ref.getId());
    assertEquals("persona", ref.getType());
    assertEquals("test-entity", ref.getName());
    assertEquals("Test Entity", ref.getDisplayName());
  }

  // ==================== Exception Tests ====================

  @Test
  @DisplayName("AISdkException contains status code")
  void metadataExceptionContainsStatusCode() {
    AISdkException exception = new AISdkException("Test error", 500);
    assertEquals(500, exception.getStatusCode());
    assertEquals("Test error", exception.getMessage());
  }

  @Test
  @DisplayName("AuthenticationException has correct status code")
  void authenticationExceptionHasCorrectStatusCode() {
    AuthenticationException exception = new AuthenticationException();
    assertEquals(401, exception.getStatusCode());
  }

  @Test
  @DisplayName("AgentNotFoundException contains agent name")
  void agentNotFoundExceptionContainsAgentName() {
    AgentNotFoundException exception = new AgentNotFoundException("test-agent");
    assertEquals("test-agent", exception.getAgentName());
    assertEquals(404, exception.getStatusCode());
    assertTrue(exception.getMessage().contains("test-agent"));
  }

  @Test
  @DisplayName("AgentNotEnabledException contains agent name")
  void agentNotEnabledExceptionContainsAgentName() {
    AgentNotEnabledException exception = new AgentNotEnabledException("test-agent");
    assertEquals("test-agent", exception.getAgentName());
    assertEquals(403, exception.getStatusCode());
    assertTrue(exception.getMessage().contains("test-agent"));
  }

  @Test
  @DisplayName("RateLimitException contains retry after")
  void rateLimitExceptionContainsRetryAfter() {
    RateLimitException exception = new RateLimitException("Rate limited", 60);
    assertEquals(429, exception.getStatusCode());
    assertEquals(Optional.of(60), exception.getRetryAfter());
  }

  @Test
  @DisplayName("RateLimitException handles null retry after")
  void rateLimitExceptionHandlesNullRetryAfter() {
    RateLimitException exception = new RateLimitException("Rate limited");
    assertEquals(429, exception.getStatusCode());
    assertEquals(Optional.empty(), exception.getRetryAfter());
  }

  @Test
  @DisplayName("BotNotFoundException contains bot name")
  void botNotFoundExceptionContainsBotName() {
    BotNotFoundException exception = new BotNotFoundException("test-bot");
    assertEquals("test-bot", exception.getBotName());
    assertEquals(404, exception.getStatusCode());
    assertTrue(exception.getMessage().contains("test-bot"));
  }

  @Test
  @DisplayName("PersonaNotFoundException contains persona name")
  void personaNotFoundExceptionContainsPersonaName() {
    PersonaNotFoundException exception = new PersonaNotFoundException("test-persona");
    assertEquals("test-persona", exception.getPersonaName());
    assertEquals(404, exception.getStatusCode());
    assertTrue(exception.getMessage().contains("test-persona"));
  }

  @Test
  @DisplayName("SkillNotFoundException contains skill name")
  void skillNotFoundExceptionContainsSkillName() {
    SkillNotFoundException exception = new SkillNotFoundException("test-skill");
    assertEquals("test-skill", exception.getSkillName());
    assertEquals(404, exception.getStatusCode());
    assertTrue(exception.getMessage().contains("test-skill"));
  }

  // ==================== Stream Content Filtering Tests ====================

  @Test
  @DisplayName("StreamEvent content filtering works correctly")
  void streamEventContentFilteringWorksCorrectly() {
    // Simulate the filtering logic used by streamContent/streamContentIterator
    StreamEvent contentEvent =
        StreamEvent.builder().type(StreamEvent.Type.CONTENT).content("Hello").build();
    StreamEvent startEvent = StreamEvent.builder().type(StreamEvent.Type.START).build();
    StreamEvent toolEvent =
        StreamEvent.builder().type(StreamEvent.Type.TOOL_USE).toolName("search").build();
    StreamEvent endEvent = StreamEvent.builder().type(StreamEvent.Type.END).build();
    StreamEvent contentNullEvent =
        StreamEvent.builder().type(StreamEvent.Type.CONTENT).content(null).build();

    List<StreamEvent> events =
        Arrays.asList(startEvent, contentEvent, toolEvent, contentNullEvent, endEvent);

    List<String> contentChunks =
        events.stream()
            .filter(e -> e.getType() == StreamEvent.Type.CONTENT && e.getContent() != null)
            .map(StreamEvent::getContent)
            .collect(java.util.stream.Collectors.toList());

    assertEquals(1, contentChunks.size());
    assertEquals("Hello", contentChunks.get(0));
  }

  // ==================== Stream Event Type Tests ====================

  @Test
  @DisplayName("StreamEvent types are defined")
  void streamEventTypesAreDefined() {
    assertEquals(5, StreamEvent.Type.values().length);
    assertNotNull(StreamEvent.Type.START);
    assertNotNull(StreamEvent.Type.CONTENT);
    assertNotNull(StreamEvent.Type.TOOL_USE);
    assertNotNull(StreamEvent.Type.ERROR);
    assertNotNull(StreamEvent.Type.END);
  }

  // ==================== Default Agent Handle Tests ====================

  @Test
  @DisplayName("No-arg agent() method returns a DefaultAgentHandle")
  void noArgAgentMethodReturnsDefaultAgentHandle() {
    AISdk client = AISdk.builder().host("https://metadata.example.com").token("test-token").build();

    DefaultAgentHandle handle = client.agent();
    assertNotNull(handle);
    client.close();
  }

  @Test
  @DisplayName("DefaultAgentHandle invoke auto-creates conversation then calls invokeDefaultAgent")
  void defaultAgentInvokeCreatesConversationThenCallsInvoke() {
    AISdkHttpClient mockHttpClient = mock(AISdkHttpClient.class);
    String conversationId = "cccccccc-cccc-cccc-cccc-cccccccccccc";
    InvokeResponse expectedResponse =
        InvokeResponse.builder()
            .conversationId(conversationId)
            .response("hello")
            .toolsUsed(Arrays.asList())
            .build();

    when(mockHttpClient.createChatConversation(anyString())).thenReturn(conversationId);
    when(mockHttpClient.invokeDefaultAgent("Say hi", conversationId, "PLANNER", "CHAT_MODE"))
        .thenReturn(expectedResponse);

    DefaultAgentHandle handle = new DefaultAgentHandle(mockHttpClient);
    InvokeResponse response = handle.invoke("Say hi");

    assertEquals("hello", response.getResponse());
    verify(mockHttpClient).createChatConversation("Say hi");
    verify(mockHttpClient).invokeDefaultAgent("Say hi", conversationId, "PLANNER", "CHAT_MODE");
  }

  @Test
  @DisplayName("DefaultAgentHandle reuses provided conversationId without creating a new one")
  void defaultAgentHandleReusesProvidedConversationId() {
    AISdkHttpClient mockHttpClient = mock(AISdkHttpClient.class);
    String conversationId = "existing-conv-id";
    InvokeResponse expectedResponse =
        InvokeResponse.builder().conversationId(conversationId).response("ok").build();

    when(mockHttpClient.invokeDefaultAgent(
            anyString(), eq(conversationId), anyString(), anyString()))
        .thenReturn(expectedResponse);

    DefaultAgentHandle handle = new DefaultAgentHandle(mockHttpClient);
    handle.conversationId(conversationId);
    InvokeResponse response = handle.invoke("Follow-up");

    assertEquals("ok", response.getResponse());
    verify(mockHttpClient, never()).createChatConversation(anyString());
    verify(mockHttpClient).invokeDefaultAgent("Follow-up", conversationId, "PLANNER", "CHAT_MODE");
  }

  @Test
  @DisplayName("DefaultAgentHandle truncates long message to 50 chars for conversation title")
  void defaultAgentHandleTruncatesLongTitleTo50Chars() {
    AISdkHttpClient mockHttpClient = mock(AISdkHttpClient.class);
    String longMessage = "This is a very long message that exceeds fifty characters by far";
    String expectedTitle = longMessage.substring(0, 50);

    when(mockHttpClient.createChatConversation(expectedTitle)).thenReturn("new-conv-id");
    when(mockHttpClient.invokeDefaultAgent(anyString(), anyString(), anyString(), anyString()))
        .thenReturn(InvokeResponse.builder().response("ok").build());

    DefaultAgentHandle handle = new DefaultAgentHandle(mockHttpClient);
    handle.invoke(longMessage);

    verify(mockHttpClient).createChatConversation(expectedTitle);
  }

  @Test
  @DisplayName("DefaultAgentHandle conversationId is retained across subsequent calls")
  void defaultAgentHandleRetainsConversationIdAcrossCalls() {
    AISdkHttpClient mockHttpClient = mock(AISdkHttpClient.class);
    String conversationId = "auto-created-id";

    when(mockHttpClient.createChatConversation(anyString())).thenReturn(conversationId);
    when(mockHttpClient.invokeDefaultAgent(
            anyString(), eq(conversationId), anyString(), anyString()))
        .thenReturn(InvokeResponse.builder().response("first").build())
        .thenReturn(InvokeResponse.builder().response("second").build());

    DefaultAgentHandle handle = new DefaultAgentHandle(mockHttpClient);
    handle.invoke("First message");
    handle.invoke("Second message");

    verify(mockHttpClient, times(1)).createChatConversation(anyString());
    verify(mockHttpClient, times(2))
        .invokeDefaultAgent(anyString(), eq(conversationId), anyString(), anyString());
  }
}
