package io.openmetadata.ai.api;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

import io.openmetadata.ai.AISdk;
import io.openmetadata.ai.internal.AISdkHttpClient;
import io.openmetadata.ai.models.AgentInfo;
import io.openmetadata.ai.models.CreateAgentRequest;
import io.openmetadata.ai.models.EntityReference;
import io.openmetadata.ai.models.PersonaInfo;
import io.openmetadata.ai.models.SkillInfo;

/**
 * Namespace for dynamic agent CRUD operations.
 *
 * <p>Holds a back-reference to the parent {@link AISdk} so that {@link
 * #create(CreateAgentRequest.Builder)} can resolve persona / skill names to entity references via
 * the personas / skills namespaces.
 */
public class AgentsApi {

  private final AISdkHttpClient http;
  private final AISdk client;

  public AgentsApi(AISdkHttpClient http, AISdk client) {
    this.http = Objects.requireNonNull(http, "http cannot be null");
    this.client = Objects.requireNonNull(client, "client cannot be null");
  }

  /** List all API-enabled dynamic agents. */
  public List<AgentInfo> list() {
    return http.listAgents();
  }

  /** List API-enabled dynamic agents up to limit. */
  public List<AgentInfo> list(int limit) {
    return http.listAgents(limit);
  }

  /**
   * Create a new dynamic agent. Persona and skill names on the builder are resolved to entity
   * references via the personas and skills namespaces.
   */
  public AgentInfo create(CreateAgentRequest.Builder builder) {
    Objects.requireNonNull(builder, "Builder cannot be null");

    String personaName = builder.getPersonaName();
    if (personaName == null || personaName.isEmpty()) {
      throw new IllegalArgumentException("persona is required");
    }
    PersonaInfo personaInfo = client.personas().get(personaName);
    EntityReference personaRef =
        EntityReference.builder().id(personaInfo.getId()).type("persona").build();

    List<EntityReference> skillRefs = null;
    List<String> skillNames = builder.getSkillNames();
    if (skillNames != null && !skillNames.isEmpty()) {
      skillRefs = new ArrayList<>();
      for (String skillName : skillNames) {
        SkillInfo skillInfo = client.skills().get(skillName);
        skillRefs.add(EntityReference.builder().id(skillInfo.getId()).type("skill").build());
      }
    }

    CreateAgentRequest request = builder.build(personaRef, skillRefs);
    return http.createAgent(request);
  }
}
