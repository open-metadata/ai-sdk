package io.openmetadata.ai.models;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/** Information about a bot entity. */
@JsonIgnoreProperties(ignoreUnknown = true)
public class BotInfo {

  @JsonProperty("id")
  private String id;

  @JsonProperty("name")
  private String name;

  @JsonProperty("displayName")
  private String displayName;

  @JsonProperty("description")
  private String description;

  @JsonProperty("botUser")
  private EntityReference botUser;

  public BotInfo() {}

  public BotInfo(
      String id, String name, String displayName, String description, EntityReference botUser) {
    this.id = id;
    this.name = name;
    this.displayName = displayName;
    this.description = description;
    this.botUser = botUser;
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

  public EntityReference getBotUser() {
    return botUser;
  }

  public void setBotUser(EntityReference botUser) {
    this.botUser = botUser;
  }

  @Override
  public String toString() {
    return "BotInfo{"
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
        + ", botUser="
        + botUser
        + '}';
  }
}
