package io.openmetadata.ai.models;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

/** High-level type of a Context Center memory. */
public enum MemoryType {
  PREFERENCE("Preference"),
  USE_CASE("UseCase"),
  NOTE("Note"),
  RUNBOOK("Runbook"),
  FAQ("Faq");

  private final String value;

  MemoryType(String value) {
    this.value = value;
  }

  @JsonValue
  public String getValue() {
    return value;
  }

  @JsonCreator
  public static MemoryType fromValue(String value) {
    for (MemoryType type : values()) {
      if (type.value.equals(value)) {
        return type;
      }
    }
    throw new IllegalArgumentException("Unknown MemoryType: " + value);
  }
}
