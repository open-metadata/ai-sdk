package io.openmetadata.ai.models;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/** Information about an AI Persona. */
@JsonIgnoreProperties(ignoreUnknown = true)
public class PersonaInfo {

  @JsonProperty("id")
  private String id;

  @JsonProperty("name")
  private String name;

  @JsonProperty("displayName")
  private String displayName;

  @JsonProperty("description")
  private String description;

  @JsonProperty("prompt")
  private String prompt;

  @JsonProperty("provider")
  private String provider;

  public PersonaInfo() {}

  public PersonaInfo(
      String id,
      String name,
      String displayName,
      String description,
      String prompt,
      String provider) {
    this.id = id;
    this.name = name;
    this.displayName = displayName;
    this.description = description;
    this.prompt = prompt;
    this.provider = provider;
  }

  public String getId() {
    return id;
  }

  public void setId(String id) {
    this.id = id;
  }

  public String getName() {
    return name;
  }

  public void setName(String name) {
    this.name = name;
  }

  public String getDisplayName() {
    return displayName;
  }

  public void setDisplayName(String displayName) {
    this.displayName = displayName;
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

  public String getProvider() {
    return provider;
  }

  public void setProvider(String provider) {
    this.provider = provider;
  }

  @Override
  public String toString() {
    return "PersonaInfo{"
        + "id='"
        + id
        + '\''
        + ", name='"
        + name
        + '\''
        + ", displayName='"
        + displayName
        + '\''
        + ", description='"
        + description
        + '\''
        + ", prompt='"
        + prompt
        + '\''
        + ", provider='"
        + provider
        + '\''
        + '}';
  }
}
