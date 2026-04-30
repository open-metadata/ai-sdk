package io.openmetadata.ai.api;

import java.util.List;
import java.util.Objects;

import io.openmetadata.ai.internal.AISdkHttpClient;
import io.openmetadata.ai.models.AbilityInfo;

/** Namespace for ability operations. */
public class AbilitiesApi {

  private final AISdkHttpClient http;

  public AbilitiesApi(AISdkHttpClient http) {
    this.http = Objects.requireNonNull(http, "http cannot be null");
  }

  /** List all abilities. */
  public List<AbilityInfo> list() {
    return http.listAbilities();
  }

  /** List abilities up to limit. */
  public List<AbilityInfo> list(int limit) {
    return http.listAbilities(limit);
  }

  /** Get an ability by name. */
  public AbilityInfo get(String name) {
    Objects.requireNonNull(name, "Ability name cannot be null");
    return http.getAbilityByName(name);
  }
}
