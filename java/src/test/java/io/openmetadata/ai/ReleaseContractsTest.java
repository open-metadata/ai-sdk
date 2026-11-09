package io.openmetadata.ai;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;

import com.fasterxml.jackson.databind.ObjectMapper;

import io.openmetadata.ai.internal.SseParser;
import io.openmetadata.ai.models.ContextMemory;
import io.openmetadata.ai.models.CreateAgentRequest;
import io.openmetadata.ai.models.CreateContextMemoryRequest;
import io.openmetadata.ai.models.InvokeRequest;
import io.openmetadata.ai.models.InvokeResponse;
import io.openmetadata.ai.models.MemoryStatus;
import io.openmetadata.ai.models.MemoryType;
import io.openmetadata.ai.models.MemoryVisibility;
import io.openmetadata.ai.models.PlannerDescription;
import io.openmetadata.ai.models.StreamEvent;

class ReleaseContractsTest {
  @Test
  void workerInstructionsAreRequiredAndOptionalPromptsAreOmitted() {
    assertThrows(
        IllegalArgumentException.class,
        () ->
            CreateAgentRequest.builder()
                .name("worker")
                .description("d")
                .persona("p")
                .mode("worker")
                .build());
    PlannerDescription description = new PlannerDescription("d", "i", "o", null);
    assertFalse(new ObjectMapper().valueToTree(description).has("prompt"));
  }

  @Test
  void currentMemoryValuesAndLifecycleAreReadable() {
    ContextMemory memory =
        ContextMemory.fromMap(
            Map.of(
                "id",
                "m1",
                "name",
                "learning",
                "memoryType",
                "Learning",
                "shareConfig",
                Map.of("visibility", "Public"),
                "entityStatus",
                "Unprocessed",
                "statusReason",
                "Awaiting review"));
    assertEquals(MemoryType.LEARNING, memory.getMemoryType());
    assertEquals(MemoryVisibility.PUBLIC, memory.getVisibility());
    assertEquals(MemoryStatus.UNPROCESSED, memory.getEntityStatus());
    assertEquals("Awaiting review", memory.getStatusReason());
    assertEquals(
        "Approved",
        CreateContextMemoryRequest.builder()
            .name("note")
            .question("q")
            .answer("a")
            .entityStatus(MemoryStatus.APPROVED)
            .build()
            .toApiMap()
            .get("entityStatus"));
  }

  @Test
  void promptOnlyInvocationSendsMessageAndStructuredOutputIsRetained() throws Exception {
    ObjectMapper mapper = new ObjectMapper();
    assertEquals(
        "",
        mapper.readTree(mapper.writeValueAsString(new InvokeRequest())).get("message").asText());
    InvokeResponse response =
        mapper.readValue(
            "{\"conversationId\":\"c1\",\"response\":\"\",\"components\":[{\"type\":\"chart\",\"content\":{\"title\":\"Revenue\"}}]}",
            InvokeResponse.class);
    assertEquals("chart", response.getComponents().get(0).get("type"));
  }

  @Test
  void terminalStreamingErrorsAreObservable() throws Exception {
    List<StreamEvent> events = new ArrayList<>();
    String body =
        "event: stream-error\ndata: {\"message\":\"run failed\",\"severity\":\"fatal\"}\n\n";
    new SseParser(new ObjectMapper())
        .parse(new ByteArrayInputStream(body.getBytes(StandardCharsets.UTF_8)), events::add);
    assertEquals(1, events.size());
    assertEquals(StreamEvent.Type.ERROR, events.get(0).getType());
    assertEquals("run failed", events.get(0).getError());
  }
}
