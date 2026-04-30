package io.openmetadata.ai.models;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

/** Visibility level for a Context Center memory. */
public enum MemoryVisibility {
  PRIVATE("Private"),
  ENTITY("Entity"),
  SHARED("Shared");

  private final String value;

  MemoryVisibility(String value) {
    this.value = value;
  }

  @JsonValue
  public String getValue() {
    return value;
  }

  @JsonCreator
  public static MemoryVisibility fromValue(String value) {
    for (MemoryVisibility visibility : values()) {
      if (visibility.value.equals(value)) {
        return visibility;
      }
    }
    throw new IllegalArgumentException("Unknown MemoryVisibility: " + value);
  }
}
