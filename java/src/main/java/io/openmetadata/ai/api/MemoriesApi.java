package io.openmetadata.ai.api;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

import io.openmetadata.ai.exceptions.AISdkException;
import io.openmetadata.ai.internal.AISdkHttpClient;
import io.openmetadata.ai.models.ContextMemory;
import io.openmetadata.ai.models.CreateContextMemoryRequest;
import io.openmetadata.ai.models.MemorySearchResults;

/**
 * Namespace for Context Center memory operations.
 *
 * <p>Uses two HTTP clients: one rooted at /api/v1/contextCenter/memories for CRUD, and one rooted
 * at /api/v1 for the hybrid NLQ search at /hybrid/nlq/search.
 */
public class MemoriesApi {

  private static final int DEFAULT_PAGE_SIZE = 100;
  private static final ObjectMapper JSON = new ObjectMapper();

  private final AISdkHttpClient http;
  private final AISdkHttpClient searchHttp;

  public MemoriesApi(AISdkHttpClient http, AISdkHttpClient searchHttp) {
    this.http = Objects.requireNonNull(http, "http cannot be null");
    this.searchHttp = Objects.requireNonNull(searchHttp, "searchHttp cannot be null");
  }

  /** List Context Center memories. */
  public List<ContextMemory> list() {
    return list(null, null);
  }

  /** List Context Center memories, capped at limit. */
  public List<ContextMemory> list(Integer limit) {
    return list(null, limit);
  }

  /** List Context Center memories filtered to a primary entity FQN. */
  public List<ContextMemory> list(String primaryEntityFqn, Integer limit) {
    List<ContextMemory> results = new ArrayList<>();
    String after = null;
    while (true) {
      Map<String, Object> params = new LinkedHashMap<>();
      params.put("limit", DEFAULT_PAGE_SIZE);
      if (primaryEntityFqn != null) {
        params.put("primaryEntityFqn", primaryEntityFqn);
      }
      if (after != null) {
        params.put("after", after);
      }
      Map<String, Object> response = http.getMap("/", params);
      Object data = response.get("data");
      if (data instanceof List) {
        for (Object item : (List<?>) data) {
          if (item instanceof Map) {
            @SuppressWarnings("unchecked")
            Map<String, Object> itemMap = (Map<String, Object>) item;
            results.add(ContextMemory.fromMap(itemMap));
            if (limit != null && results.size() >= limit) {
              return results.subList(0, Math.min(results.size(), limit));
            }
          }
        }
      }
      Object paging = response.get("paging");
      if (paging instanceof Map) {
        Object next = ((Map<?, ?>) paging).get("after");
        if (next == null) {
          break;
        }
        after = String.valueOf(next);
      } else {
        break;
      }
    }
    return results;
  }

  /** Get a memory by id. */
  public ContextMemory get(String memoryId) {
    Objects.requireNonNull(memoryId, "memoryId cannot be null");
    Map<String, Object> response = http.getMap("/" + memoryId, null);
    return ContextMemory.fromMap(response);
  }

  /** Create a new Context Center memory. */
  public ContextMemory create(CreateContextMemoryRequest request) {
    Objects.requireNonNull(request, "request cannot be null");
    Map<String, Object> response = http.postMap("/", request.toApiMap());
    return ContextMemory.fromMap(response);
  }

  /** Soft-delete a memory by id. */
  public void delete(String memoryId) {
    delete(memoryId, false);
  }

  /** Delete a memory by id, optionally hard-deleting. */
  public void delete(String memoryId, boolean hardDelete) {
    Objects.requireNonNull(memoryId, "memoryId cannot be null");
    Map<String, Object> params = new LinkedHashMap<>();
    params.put("hardDelete", hardDelete);
    http.delete("/" + memoryId, params);
  }

  /** Hybrid NLQ search over Context Center memories. */
  public MemorySearchResults search(String query) {
    return search(query, null, 15, 0);
  }

  /** Hybrid NLQ search with optional filters and pagination. */
  public MemorySearchResults search(
      String query, Map<String, List<String>> filters, int size, int from) {
    Objects.requireNonNull(query, "query cannot be null");
    Map<String, Object> params = new LinkedHashMap<>();
    params.put("q", query);
    params.put("index", "contextMemory");
    params.put("size", size);
    params.put("from", from);
    if (filters != null && !filters.isEmpty()) {
      try {
        params.put("filters", JSON.writeValueAsString(filters));
      } catch (JsonProcessingException e) {
        throw new AISdkException("Failed to serialize search filters", e);
      }
    }
    Map<String, Object> response = searchHttp.getMap("/hybrid/nlq/search", params);
    return MemorySearchResults.fromOpenSearch(response);
  }
}
