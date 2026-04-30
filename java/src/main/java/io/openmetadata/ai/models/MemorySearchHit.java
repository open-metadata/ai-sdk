package io.openmetadata.ai.models;

import java.util.Collections;
import java.util.Map;

/** A single hit from a hybrid memory search. */
public class MemorySearchHit {

  private final ContextMemory memory;
  private final double score;

  public MemorySearchHit(ContextMemory memory, double score) {
    this.memory = memory;
    this.score = score;
  }

  public ContextMemory getMemory() {
    return memory;
  }

  public double getScore() {
    return score;
  }

  /** Build a MemorySearchHit from an OpenSearch hit map. */
  @SuppressWarnings("unchecked")
  public static MemorySearchHit fromMap(Map<String, Object> data) {
    Map<String, Object> source =
        data.get("_source") instanceof Map
            ? (Map<String, Object>) data.get("_source")
            : Collections.emptyMap();
    Object scoreVal = data.get("_score");
    double score = scoreVal instanceof Number ? ((Number) scoreVal).doubleValue() : 0.0;
    return new MemorySearchHit(ContextMemory.fromMap(source), score);
  }
}
