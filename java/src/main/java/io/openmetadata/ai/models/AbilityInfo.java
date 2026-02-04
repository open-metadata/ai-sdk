package io.openmetadata.ai.models;

import java.util.Collections;
import java.util.List;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/** Information about an Ability. */
@JsonIgnoreProperties(ignoreUnknown = true)
public class AbilityInfo {

  @JsonProperty("id")
  private String id;

  @JsonProperty("name")
  private String name;

  @JsonProperty("displayName")
  private String displayName;

  @JsonProperty("description")
  private String description;

  @JsonProperty("provider")
  private String provider;

  @JsonProperty("fullyQualifiedName")
  private String fullyQualifiedName;

  @JsonProperty("tools")
  private List<String> tools;

  public AbilityInfo() {
    this.tools = Collections.emptyList();
  }

  public AbilityInfo(
      String id,
      String name,
      String displayName,
      String description,
      String provider,
      String fullyQualifiedName,
      List<String> tools) {
    this.id = id;
    this.name = name;
    this.displayName = displayName;
    this.description = description;
    this.provider = provider;
    this.fullyQualifiedName = fullyQualifiedName;
    this.tools = tools != null ? tools : Collections.emptyList();
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

  public String getProvider() {
    return provider;
  }

  public void setProvider(String provider) {
    this.provider = provider;
  }

  public String getFullyQualifiedName() {
    return fullyQualifiedName;
  }

  public void setFullyQualifiedName(String fullyQualifiedName) {
    this.fullyQualifiedName = fullyQualifiedName;
  }

  public List<String> getTools() {
    return tools;
  }

  public void setTools(List<String> tools) {
    this.tools = tools != null ? tools : Collections.emptyList();
  }

  @Override
  public String toString() {
    return "AbilityInfo{"
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
        + ", provider='"
        + provider
        + '\''
        + ", fullyQualifiedName='"
        + fullyQualifiedName
        + '\''
        + ", tools="
        + tools
        + '}';
  }
}
