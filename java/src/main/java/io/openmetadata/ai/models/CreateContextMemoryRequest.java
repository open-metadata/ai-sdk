package io.openmetadata.ai.models;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Request to create a Context Center memory. */
public class CreateContextMemoryRequest {

  private final String name;
  private final String question;
  private final String answer;
  private final String title;
  private final String description;
  private final MemoryType memoryType;
  private final MemoryScope memoryScope;
  private final MemoryVisibility visibility;
  private final EntityReference primaryEntity;
  private final List<EntityReference> relatedEntities;
  private final List<String> tags;

  private CreateContextMemoryRequest(Builder b) {
    this.name = b.name;
    this.question = b.question;
    this.answer = b.answer;
    this.title = b.title;
    this.description = b.description;
    this.memoryType = b.memoryType;
    this.memoryScope = b.memoryScope;
    this.visibility = b.visibility;
    this.primaryEntity = b.primaryEntity;
    this.relatedEntities = b.relatedEntities;
    this.tags = b.tags;
  }

  public String getName() {
    return name;
  }

  public String getQuestion() {
    return question;
  }

  public String getAnswer() {
    return answer;
  }

  public String getTitle() {
    return title;
  }

  public String getDescription() {
    return description;
  }

  public MemoryType getMemoryType() {
    return memoryType;
  }

  public MemoryScope getMemoryScope() {
    return memoryScope;
  }

  public MemoryVisibility getVisibility() {
    return visibility;
  }

  public EntityReference getPrimaryEntity() {
    return primaryEntity;
  }

  public List<EntityReference> getRelatedEntities() {
    return relatedEntities;
  }

  public List<String> getTags() {
    return tags;
  }

  /** Convert to API request format (camelCase keys, shareConfig wrapping, tag wrapping). */
  public Map<String, Object> toApiMap() {
    Map<String, Object> d = new LinkedHashMap<>();
    d.put("name", name);
    d.put("question", question);
    d.put("answer", answer);
    d.put("memoryType", memoryType.getValue());
    d.put("memoryScope", memoryScope.getValue());
    Map<String, Object> shareConfig = new LinkedHashMap<>();
    shareConfig.put("visibility", visibility.getValue());
    d.put("shareConfig", shareConfig);
    if (title != null) {
      d.put("title", title);
    }
    if (description != null) {
      d.put("description", description);
    }
    if (primaryEntity != null) {
      d.put("primaryEntity", entityReferenceToMap(primaryEntity));
    }
    if (relatedEntities != null) {
      List<Map<String, Object>> refs = new ArrayList<>();
      for (EntityReference ref : relatedEntities) {
        refs.add(entityReferenceToMap(ref));
      }
      d.put("relatedEntities", refs);
    }
    if (tags != null) {
      List<Map<String, Object>> tagLabels = new ArrayList<>();
      for (String t : tags) {
        Map<String, Object> tagLabel = new LinkedHashMap<>();
        tagLabel.put("tagFQN", t);
        tagLabel.put("labelType", "Manual");
        tagLabel.put("state", "Confirmed");
        tagLabel.put("source", "Classification");
        tagLabels.add(tagLabel);
      }
      d.put("tags", tagLabels);
    }
    return d;
  }

  private static Map<String, Object> entityReferenceToMap(EntityReference ref) {
    Map<String, Object> m = new LinkedHashMap<>();
    if (ref.getId() != null) {
      m.put("id", ref.getId());
    }
    if (ref.getType() != null) {
      m.put("type", ref.getType());
    }
    if (ref.getName() != null) {
      m.put("name", ref.getName());
    }
    if (ref.getDisplayName() != null) {
      m.put("displayName", ref.getDisplayName());
    }
    return m;
  }

  public static Builder builder() {
    return new Builder();
  }

  public static class Builder {
    private String name;
    private String question;
    private String answer;
    private String title;
    private String description;
    private MemoryType memoryType = MemoryType.NOTE;
    private MemoryScope memoryScope = MemoryScope.ENTITY_SCOPED;
    private MemoryVisibility visibility = MemoryVisibility.PRIVATE;
    private EntityReference primaryEntity;
    private List<EntityReference> relatedEntities;
    private List<String> tags;

    public Builder name(String name) {
      this.name = name;
      return this;
    }

    public Builder question(String question) {
      this.question = question;
      return this;
    }

    public Builder answer(String answer) {
      this.answer = answer;
      return this;
    }

    public Builder title(String title) {
      this.title = title;
      return this;
    }

    public Builder description(String description) {
      this.description = description;
      return this;
    }

    public Builder memoryType(MemoryType memoryType) {
      this.memoryType = memoryType;
      return this;
    }

    public Builder memoryScope(MemoryScope memoryScope) {
      this.memoryScope = memoryScope;
      return this;
    }

    public Builder visibility(MemoryVisibility visibility) {
      this.visibility = visibility;
      return this;
    }

    public Builder primaryEntity(EntityReference primaryEntity) {
      this.primaryEntity = primaryEntity;
      return this;
    }

    public Builder relatedEntities(List<EntityReference> relatedEntities) {
      this.relatedEntities = relatedEntities;
      return this;
    }

    public Builder tags(List<String> tags) {
      this.tags = tags;
      return this;
    }

    public CreateContextMemoryRequest build() {
      if (name == null || name.isEmpty()) {
        throw new IllegalArgumentException("name is required");
      }
      if (question == null || question.isEmpty()) {
        throw new IllegalArgumentException("question is required");
      }
      if (answer == null || answer.isEmpty()) {
        throw new IllegalArgumentException("answer is required");
      }
      if (memoryType == null) {
        throw new IllegalArgumentException("memoryType cannot be null");
      }
      if (memoryScope == null) {
        throw new IllegalArgumentException("memoryScope cannot be null");
      }
      if (visibility == null) {
        throw new IllegalArgumentException("visibility cannot be null");
      }
      return new CreateContextMemoryRequest(this);
    }
  }
}
