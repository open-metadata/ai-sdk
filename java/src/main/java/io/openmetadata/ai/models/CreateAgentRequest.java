package io.openmetadata.ai.models;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/** Request to create a new dynamic agent. */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class CreateAgentRequest {

  @JsonProperty("name")
  private String name;

  @JsonProperty("description")
  private String description;

  @JsonProperty("persona")
  private EntityReference persona;

  @JsonProperty("type")
  private String type = "external";

  @JsonProperty("plannerDescription")
  private PlannerDescription plannerDescription;

  @JsonProperty("mode")
  private String mode;

  @JsonProperty("displayName")
  private String displayName;

  @JsonProperty("icon")
  private String icon;

  @JsonProperty("botName")
  private String botName;

  @JsonProperty("skills")
  private List<EntityReference> skills;

  @JsonProperty("knowledge")
  private KnowledgeScope knowledge;

  @JsonProperty("prompt")
  private String prompt;

  @JsonProperty("apiEnabled")
  private boolean apiEnabled;

  @JsonProperty("provider")
  private String provider;

  public CreateAgentRequest() {}

  public CreateAgentRequest(
      String name,
      String description,
      EntityReference persona,
      String mode,
      String displayName,
      String icon,
      String botName,
      List<EntityReference> skills,
      KnowledgeScope knowledge,
      String prompt,
      boolean apiEnabled,
      String provider) {
    this.name = name;
    this.description = description;
    this.persona = persona;
    this.mode = mode;
    this.displayName = displayName;
    this.icon = icon;
    this.botName = botName;
    this.skills = skills;
    this.knowledge = knowledge;
    this.prompt = prompt;
    this.apiEnabled = apiEnabled;
    this.provider = provider;
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

  public EntityReference getPersona() {
    return persona;
  }

  public void setPersona(EntityReference persona) {
    this.persona = persona;
  }

  public String getType() {
    return type;
  }

  public void setType(String type) {
    this.type = type;
  }

  public PlannerDescription getPlannerDescription() {
    return plannerDescription;
  }

  public void setPlannerDescription(PlannerDescription plannerDescription) {
    this.plannerDescription = plannerDescription;
  }

  public String getMode() {
    return mode;
  }

  public void setMode(String mode) {
    this.mode = mode;
  }

  public String getDisplayName() {
    return displayName;
  }

  public void setDisplayName(String displayName) {
    this.displayName = displayName;
  }

  public String getIcon() {
    return icon;
  }

  public void setIcon(String icon) {
    this.icon = icon;
  }

  public String getBotName() {
    return botName;
  }

  public void setBotName(String botName) {
    this.botName = botName;
  }

  public List<EntityReference> getSkills() {
    return skills;
  }

  public void setSkills(List<EntityReference> skills) {
    this.skills = skills;
  }

  public KnowledgeScope getKnowledge() {
    return knowledge;
  }

  public void setKnowledge(KnowledgeScope knowledge) {
    this.knowledge = knowledge;
  }

  public String getPrompt() {
    return prompt;
  }

  public void setPrompt(String prompt) {
    this.prompt = prompt;
  }

  public boolean isApiEnabled() {
    return apiEnabled;
  }

  public void setApiEnabled(boolean apiEnabled) {
    this.apiEnabled = apiEnabled;
  }

  public String getProvider() {
    return provider;
  }

  public void setProvider(String provider) {
    this.provider = provider;
  }

  /** Creates a new builder for CreateAgentRequest. */
  public static Builder builder() {
    return new Builder();
  }

  public static class Builder {
    private String name;
    private String description;
    private String personaName;
    private String mode;
    private String type = "external";
    private PlannerDescription plannerDescription;
    private String displayName;
    private String icon;
    private String botName;
    private List<String> skillNames;
    private KnowledgeScope knowledge;
    private String prompt;
    private boolean apiEnabled = false;
    private String provider = "user";

    public Builder name(String name) {
      this.name = name;
      return this;
    }

    public Builder description(String description) {
      this.description = description;
      return this;
    }

    /** Sets the persona by name. Will be resolved to ID when agent is created. */
    public Builder persona(String persona) {
      this.personaName = persona;
      return this;
    }

    public Builder type(String type) {
      this.type = type;
      return this;
    }

    public Builder plannerDescription(PlannerDescription plannerDescription) {
      this.plannerDescription = plannerDescription;
      return this;
    }

    public Builder mode(String mode) {
      this.mode = mode;
      return this;
    }

    public Builder displayName(String displayName) {
      this.displayName = displayName;
      return this;
    }

    public Builder icon(String icon) {
      this.icon = icon;
      return this;
    }

    public Builder botName(String botName) {
      this.botName = botName;
      return this;
    }

    /** Sets the skills by name. Will be resolved to IDs when agent is created. */
    public Builder skills(List<String> skills) {
      this.skillNames = skills;
      return this;
    }

    public Builder knowledge(KnowledgeScope knowledge) {
      this.knowledge = knowledge;
      return this;
    }

    public Builder prompt(String prompt) {
      this.prompt = prompt;
      return this;
    }

    public Builder apiEnabled(boolean apiEnabled) {
      this.apiEnabled = apiEnabled;
      return this;
    }

    public Builder provider(String provider) {
      this.provider = provider;
      return this;
    }

    public String getPersonaName() {
      return personaName;
    }

    public List<String> getSkillNames() {
      return skillNames;
    }

    public CreateAgentRequest build() {
      if (name == null || name.isEmpty()) {
        throw new IllegalArgumentException("name is required");
      }
      if (description == null || description.isEmpty()) {
        throw new IllegalArgumentException("description is required");
      }
      if (personaName == null || personaName.isEmpty()) {
        throw new IllegalArgumentException("persona is required");
      }
      if (mode == null || mode.isEmpty()) {
        throw new IllegalArgumentException("mode is required");
      }
      if (!mode.equals("standalone") && !mode.equals("worker")) {
        throw new IllegalArgumentException("mode must be one of: standalone, worker");
      }
      if (mode.equals("worker")
          && (plannerDescription == null
              || plannerDescription.prompt == null
              || plannerDescription.prompt.isBlank())) {
        throw new IllegalArgumentException("worker agents require plannerDescription.prompt");
      }
      // Create request with null references - they will be resolved by AISdk.createAgent()
      CreateAgentRequest request =
          new CreateAgentRequest(
              name,
              description,
              null,
              mode,
              displayName,
              icon,
              botName,
              null,
              knowledge,
              prompt,
              apiEnabled,
              provider);
      request.setType(type);
      request.setPlannerDescription(plannerDescription);
      return request;
    }

    /**
     * Build the request with resolved entity references. Used internally by AISdk.createAgent().
     */
    public CreateAgentRequest build(EntityReference persona, List<EntityReference> skills) {
      if (name == null || name.isEmpty()) {
        throw new IllegalArgumentException("name is required");
      }
      if (description == null || description.isEmpty()) {
        throw new IllegalArgumentException("description is required");
      }
      if (persona == null) {
        throw new IllegalArgumentException("persona is required");
      }
      if (mode == null || mode.isEmpty()) {
        throw new IllegalArgumentException("mode is required");
      }
      if (!mode.equals("standalone") && !mode.equals("worker")) {
        throw new IllegalArgumentException("mode must be one of: standalone, worker");
      }
      if (mode.equals("worker")
          && (plannerDescription == null
              || plannerDescription.prompt == null
              || plannerDescription.prompt.isBlank())) {
        throw new IllegalArgumentException("worker agents require plannerDescription.prompt");
      }
      CreateAgentRequest request =
          new CreateAgentRequest(
              name,
              description,
              persona,
              mode,
              displayName,
              icon,
              botName,
              skills,
              knowledge,
              prompt,
              apiEnabled,
              provider);
      request.setType(type);
      request.setPlannerDescription(plannerDescription);
      return request;
    }
  }

  @Override
  public String toString() {
    return "CreateAgentRequest{"
        + "name='"
        + name
        + '\''
        + ", description='"
        + description
        + '\''
        + ", persona="
        + persona
        + ", mode='"
        + mode
        + '\''
        + ", displayName='"
        + displayName
        + '\''
        + ", icon='"
        + icon
        + '\''
        + ", botName='"
        + botName
        + '\''
        + ", skills="
        + skills
        + ", knowledge="
        + knowledge
        + ", prompt='"
        + prompt
        + '\''
        + ", apiEnabled="
        + apiEnabled
        + ", provider='"
        + provider
        + '\''
        + '}';
  }
}
