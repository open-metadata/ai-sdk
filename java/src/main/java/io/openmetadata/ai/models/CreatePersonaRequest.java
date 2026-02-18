package io.openmetadata.ai.models;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/** Request to create a new AI Persona. */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class CreatePersonaRequest {

  @JsonProperty("name")
  private String name;

  @JsonProperty("description")
  private String description;

  @JsonProperty("prompt")
  private String prompt;

  @JsonProperty("displayName")
  private String displayName;

  @JsonProperty("provider")
  private String provider;

  @JsonProperty("owners")
  private List<EntityReference> owners;

  public CreatePersonaRequest() {}

  public CreatePersonaRequest(
      String name,
      String description,
      String prompt,
      String displayName,
      String provider,
      List<EntityReference> owners) {
    this.name = name;
    this.description = description;
    this.prompt = prompt;
    this.displayName = displayName;
    this.provider = provider;
    this.owners = owners;
  }

  public String getName() {
    return name;
  }

  public void setName(String name) {
    this.name = name;
  }

  public String getDescription() {
    return description;
  }

  public void setDescription(String description) {
    this.description = description;
  }

  public String getPrompt() {
    return prompt;
  }

  public void setPrompt(String prompt) {
    this.prompt = prompt;
  }

  public String getDisplayName() {
    return displayName;
  }

  public void setDisplayName(String displayName) {
    this.displayName = displayName;
  }

  public String getProvider() {
    return provider;
  }

  public void setProvider(String provider) {
    this.provider = provider;
  }

  public List<EntityReference> getOwners() {
    return owners;
  }

  public void setOwners(List<EntityReference> owners) {
    this.owners = owners;
  }

  /** Creates a new builder for CreatePersonaRequest. */
  public static Builder builder() {
    return new Builder();
  }

  public static class Builder {
    private String name;
    private String description;
    private String prompt;
    private String displayName;
    private String provider = "user";
    private List<EntityReference> owners;

    public Builder name(String name) {
      this.name = name;
      return this;
    }

    public Builder description(String description) {
      this.description = description;
      return this;
    }

    public Builder prompt(String prompt) {
      this.prompt = prompt;
      return this;
    }

    public Builder displayName(String displayName) {
      this.displayName = displayName;
      return this;
    }

    public Builder provider(String provider) {
      this.provider = provider;
      return this;
    }

    public Builder owners(List<EntityReference> owners) {
      this.owners = owners;
      return this;
    }

    public CreatePersonaRequest build() {
      if (name == null || name.isEmpty()) {
        throw new IllegalArgumentException("name is required");
      }
      if (description == null || description.isEmpty()) {
        throw new IllegalArgumentException("description is required");
      }
      if (prompt == null || prompt.isEmpty()) {
        throw new IllegalArgumentException("prompt is required");
      }
      return new CreatePersonaRequest(name, description, prompt, displayName, provider, owners);
    }
  }

  @Override
  public String toString() {
    return "CreatePersonaRequest{"
        + "name='"
        + name
        + '\''
        + ", description='"
        + description
        + '\''
        + ", prompt='"
        + prompt
        + '\''
        + ", displayName='"
        + displayName
        + '\''
        + ", provider='"
        + provider
        + '\''
        + ", owners="
        + owners
        + '}';
  }
}
