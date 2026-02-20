package io.openmetadata.ai.models;

import java.util.ArrayList;
import java.util.List;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonSetter;
import com.fasterxml.jackson.databind.JsonNode;

/** Information about an AI agent. */
@JsonIgnoreProperties(ignoreUnknown = true)
public class AgentInfo {

  @JsonProperty("name")
  private String name;

  @JsonProperty("displayName")
  private String displayName;

  @JsonProperty("description")
  private String description;

  private List<String> abilities;

  @JsonProperty("apiEnabled")
  private boolean apiEnabled;

  public AgentInfo() {}

  public AgentInfo(
      String name,
      String displayName,
      String description,
      List<String> abilities,
      boolean apiEnabled) {
    this.name = name;
    this.displayName = displayName;
    this.description = description;
    this.abilities = abilities;
    this.apiEnabled = apiEnabled;
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

  public List<String> getAbilities() {
    return abilities;
  }

  public void setAbilities(List<String> abilities) {
    this.abilities = abilities;
  }

  /**
   * Custom setter to handle abilities returned as either strings or EntityReferences. The API
   * returns EntityReferences, but we want to expose just the names.
   */
  @JsonSetter("abilities")
  public void setAbilitiesFromJson(List<JsonNode> abilitiesJson) {
    if (abilitiesJson == null) {
      this.abilities = null;
      return;
    }
    this.abilities = new ArrayList<>();
    for (JsonNode node : abilitiesJson) {
      if (node.isTextual()) {
        // It's a string
        this.abilities.add(node.asText());
      } else if (node.isObject() && node.has("name")) {
        // It's an EntityReference, extract the name
        this.abilities.add(node.get("name").asText());
      }
    }
  }

  public boolean isApiEnabled() {
    return apiEnabled;
  }

  public void setApiEnabled(boolean apiEnabled) {
    this.apiEnabled = apiEnabled;
  }

  @Override
  public String toString() {
    return "AgentInfo{"
        + "name='"
        + name
        + '\''
        + ", displayName='"
        + displayName
        + '\''
        + ", description='"
        + description
        + '\''
        + ", abilities="
        + abilities
        + ", apiEnabled="
        + apiEnabled
        + '}';
  }
}
