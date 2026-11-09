package io.openmetadata.ai.models;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

/** Lifecycle stage of a Context Center memory. */
public enum MemoryStatus {
  DRAFT("Draft"),
  APPROVED("Approved"),
  ARCHIVED("Archived"),
  SUPERSEDED("Superseded"),
  INVALIDATED("Invalidated"),
  UNPROCESSED("Unprocessed"),
  DEPRECATED("Deprecated"),
  REJECTED("Rejected");

  private final String value;

  MemoryStatus(String value) {
    this.value = value;
  }

  @JsonValue
  public String getValue() {
    return value;
  }

  @JsonCreator
  public static MemoryStatus fromValue(String value) {
    for (MemoryStatus type : values()) {
      if (type.value.equals(value)) {
        return type;
      }
    }
    throw new IllegalArgumentException("Unknown MemoryStatus: " + value);
  }
}
