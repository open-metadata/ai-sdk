package io.openmetadata.ai.api;

import java.util.List;
import java.util.Objects;

import io.openmetadata.ai.internal.AISdkHttpClient;
import io.openmetadata.ai.models.SkillInfo;

/** Namespace for skill operations. */
public class SkillsApi {

  private final AISdkHttpClient http;

  public SkillsApi(AISdkHttpClient http) {
    this.http = Objects.requireNonNull(http, "http cannot be null");
  }

  /** List all skills. */
  public List<SkillInfo> list() {
    return http.listSkills();
  }

  /** List skills up to limit. */
  public List<SkillInfo> list(int limit) {
    return http.listSkills(limit);
  }

  /** Get a skill by name. */
  public SkillInfo get(String name) {
    Objects.requireNonNull(name, "Skill name cannot be null");
    return http.getSkillByName(name);
  }
}
