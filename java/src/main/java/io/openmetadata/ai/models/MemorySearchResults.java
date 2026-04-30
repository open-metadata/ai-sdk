package io.openmetadata.ai.models;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

/** Results from a hybrid memory search. */
public class MemorySearchResults {

  private final int total;
  private final List<MemorySearchHit> hits;

  public MemorySearchResults(int total, List<MemorySearchHit> hits) {
    this.total = total;
    this.hits = hits != null ? hits : Collections.emptyList();
  }

  public int getTotal() {
    return total;
  }

  public List<MemorySearchHit> getHits() {
    return hits;
  }

  /** Parse an OpenSearch response shape into MemorySearchResults. */
  @SuppressWarnings("unchecked")
  public static MemorySearchResults fromOpenSearch(Map<String, Object> data) {
    if (data == null) {
      return new MemorySearchResults(0, Collections.emptyList());
    }
    Object hitsBlockObj = data.get("hits");
    Map<String, Object> hitsBlock =
        hitsBlockObj instanceof Map ? (Map<String, Object>) hitsBlockObj : Collections.emptyMap();

    int total = 0;
    Object totalObj = hitsBlock.get("total");
    if (totalObj instanceof Map) {
      Object value = ((Map<String, Object>) totalObj).get("value");
      if (value instanceof Number) {
        total = ((Number) value).intValue();
      }
    } else if (totalObj instanceof Number) {
      total = ((Number) totalObj).intValue();
    }

    Object rawHitsObj = hitsBlock.get("hits");
    List<MemorySearchHit> parsedHits = new ArrayList<>();
    if (rawHitsObj instanceof List) {
      for (Object item : (List<Object>) rawHitsObj) {
        if (item instanceof Map) {
          parsedHits.add(MemorySearchHit.fromMap((Map<String, Object>) item));
        }
      }
    }
    return new MemorySearchResults(total, parsedHits);
  }
}
