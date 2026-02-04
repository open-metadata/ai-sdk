package io.openmetadata.ai.models;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/** Defines what data an agent can access. */
@JsonIgnoreProperties(ignoreUnknown = true)
public class KnowledgeScope {

  @JsonProperty("entityTypes")
  private List<String> entityTypes;

  @JsonProperty("services")
  private List<EntityReference> services;

  public KnowledgeScope() {}

  public KnowledgeScope(List<String> entityTypes, List<EntityReference> services) {
    this.entityTypes = entityTypes;
    this.services = services;
  }

  public List<String> getEntityTypes() {
    return entityTypes;
  }

  public void setEntityTypes(List<String> entityTypes) {
    this.entityTypes = entityTypes;
  }

  public List<EntityReference> getServices() {
    return services;
  }

  public void setServices(List<EntityReference> services) {
    this.services = services;
  }

  /** Creates a new builder for KnowledgeScope. */
  public static Builder builder() {
    return new Builder();
  }

  public static class Builder {
    private List<String> entityTypes;
    private List<EntityReference> services;

    public Builder entityTypes(List<String> entityTypes) {
      this.entityTypes = entityTypes;
      return this;
    }

    public Builder services(List<EntityReference> services) {
      this.services = services;
      return this;
    }

    public KnowledgeScope build() {
      return new KnowledgeScope(entityTypes, services);
    }
  }

  @Override
  public String toString() {
    return "KnowledgeScope{" + "entityTypes=" + entityTypes + ", services=" + services + '}';
  }
}
