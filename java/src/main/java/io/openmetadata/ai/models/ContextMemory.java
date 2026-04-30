package io.openmetadata.ai.models;

import java.util.Map;

/** A Context Center memory. */
public class ContextMemory {

  private String id;
  private String name;
  private String fullyQualifiedName;
  private String title;
  private String question;
  private String answer;
  private String summary;
  private MemoryType memoryType;
  private MemoryScope memoryScope;
  private MemoryVisibility visibility;
  private EntityReference primaryEntity;
  private int usageCount;
  private Long lastUsedAt;
  private boolean deleted;

  public ContextMemory() {}

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

  public String getFullyQualifiedName() {
    return fullyQualifiedName;
  }

  public void setFullyQualifiedName(String fullyQualifiedName) {
    this.fullyQualifiedName = fullyQualifiedName;
  }

  public String getTitle() {
    return title;
  }

  public void setTitle(String title) {
    this.title = title;
  }

  public String getQuestion() {
    return question;
  }

  public void setQuestion(String question) {
    this.question = question;
  }

  public String getAnswer() {
    return answer;
  }

  public void setAnswer(String answer) {
    this.answer = answer;
  }

  public String getSummary() {
    return summary;
  }

  public void setSummary(String summary) {
    this.summary = summary;
  }

  public MemoryType getMemoryType() {
    return memoryType;
  }

  public void setMemoryType(MemoryType memoryType) {
    this.memoryType = memoryType;
  }

  public MemoryScope getMemoryScope() {
    return memoryScope;
  }

  public void setMemoryScope(MemoryScope memoryScope) {
    this.memoryScope = memoryScope;
  }

  public MemoryVisibility getVisibility() {
    return visibility;
  }

  public void setVisibility(MemoryVisibility visibility) {
    this.visibility = visibility;
  }

  public EntityReference getPrimaryEntity() {
    return primaryEntity;
  }

  public void setPrimaryEntity(EntityReference primaryEntity) {
    this.primaryEntity = primaryEntity;
  }

  public int getUsageCount() {
    return usageCount;
  }

  public void setUsageCount(int usageCount) {
    this.usageCount = usageCount;
  }

  public Long getLastUsedAt() {
    return lastUsedAt;
  }

  public void setLastUsedAt(Long lastUsedAt) {
    this.lastUsedAt = lastUsedAt;
  }

  public boolean isDeleted() {
    return deleted;
  }

  public void setDeleted(boolean deleted) {
    this.deleted = deleted;
  }

  /**
   * Build a ContextMemory from a parsed JSON map. Flattens shareConfig.visibility back to a
   * top-level visibility field.
   */
  @SuppressWarnings("unchecked")
  public static ContextMemory fromMap(Map<String, Object> data) {
    ContextMemory m = new ContextMemory();
    if (data == null) {
      return m;
    }
    if (data.get("id") != null) {
      m.id = String.valueOf(data.get("id"));
    }
    if (data.get("name") != null) {
      m.name = String.valueOf(data.get("name"));
    }
    if (data.get("fullyQualifiedName") != null) {
      m.fullyQualifiedName = String.valueOf(data.get("fullyQualifiedName"));
    }
    if (data.get("title") != null) {
      m.title = String.valueOf(data.get("title"));
    }
    m.question = data.get("question") != null ? String.valueOf(data.get("question")) : "";
    m.answer = data.get("answer") != null ? String.valueOf(data.get("answer")) : "";
    if (data.get("summary") != null) {
      m.summary = String.valueOf(data.get("summary"));
    }
    String memoryTypeStr =
        data.get("memoryType") != null ? String.valueOf(data.get("memoryType")) : "Note";
    m.memoryType = MemoryType.fromValue(memoryTypeStr);
    String memoryScopeStr =
        data.get("memoryScope") != null ? String.valueOf(data.get("memoryScope")) : "EntityScoped";
    m.memoryScope = MemoryScope.fromValue(memoryScopeStr);

    String visibilityStr = "Private";
    Object shareConfig = data.get("shareConfig");
    if (shareConfig instanceof Map) {
      Object v = ((Map<String, Object>) shareConfig).get("visibility");
      if (v != null) {
        visibilityStr = String.valueOf(v);
      }
    }
    m.visibility = MemoryVisibility.fromValue(visibilityStr);

    Object pe = data.get("primaryEntity");
    if (pe instanceof Map) {
      Map<String, Object> peMap = (Map<String, Object>) pe;
      m.primaryEntity =
          new EntityReference(
              peMap.get("id") != null ? String.valueOf(peMap.get("id")) : null,
              peMap.get("type") != null ? String.valueOf(peMap.get("type")) : null,
              peMap.get("name") != null ? String.valueOf(peMap.get("name")) : null,
              peMap.get("displayName") != null ? String.valueOf(peMap.get("displayName")) : null);
    }
    Object usage = data.get("usageCount");
    if (usage instanceof Number) {
      m.usageCount = ((Number) usage).intValue();
    }
    Object lastUsed = data.get("lastUsedAt");
    if (lastUsed instanceof Number) {
      m.lastUsedAt = ((Number) lastUsed).longValue();
    }
    Object deletedVal = data.get("deleted");
    if (deletedVal instanceof Boolean) {
      m.deleted = (Boolean) deletedVal;
    }
    return m;
  }
}
