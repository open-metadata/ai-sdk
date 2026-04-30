package io.openmetadata.ai.models;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

/** Scope where a Context Center memory applies. */
public enum MemoryScope {
  USER_GLOBAL("UserGlobal"),
  ENTITY_SCOPED("EntityScoped");

  private final String value;

  MemoryScope(String value) {
    this.value = value;
  }

  @JsonValue
  public String getValue() {
    return value;
  }

  @JsonCreator
  public static MemoryScope fromValue(String value) {
    for (MemoryScope scope : values()) {
      if (scope.value.equals(value)) {
        return scope;
      }
    }
    throw new IllegalArgumentException("Unknown MemoryScope: " + value);
  }
}
