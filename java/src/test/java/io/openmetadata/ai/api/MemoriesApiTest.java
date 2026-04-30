package io.openmetadata.ai.api;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import io.openmetadata.ai.internal.AISdkHttpClient;
import io.openmetadata.ai.models.ContextMemory;
import io.openmetadata.ai.models.CreateContextMemoryRequest;
import io.openmetadata.ai.models.MemoryScope;
import io.openmetadata.ai.models.MemorySearchResults;
import io.openmetadata.ai.models.MemoryType;
import io.openmetadata.ai.models.MemoryVisibility;

/** Unit tests for {@link MemoriesApi} request shapes and response parsing. */
class MemoriesApiTest {

  private AISdkHttpClient http;
  private AISdkHttpClient searchHttp;
  private MemoriesApi memories;

  @BeforeEach
  void setUp() {
    http = org.mockito.Mockito.mock(AISdkHttpClient.class);
    searchHttp = org.mockito.Mockito.mock(AISdkHttpClient.class);
    memories = new MemoriesApi(http, searchHttp);
  }

  @Test
  @DisplayName("list paginates through all pages")
  void listPaginatesThroughAllPages() {
    Map<String, Object> page1 = new LinkedHashMap<>();
    page1.put("data", Arrays.asList(memoryMap("m-1", "first"), memoryMap("m-2", "second")));
    Map<String, Object> paging1 = new LinkedHashMap<>();
    paging1.put("after", "cursor-1");
    page1.put("paging", paging1);

    Map<String, Object> page2 = new LinkedHashMap<>();
    page2.put("data", Collections.singletonList(memoryMap("m-3", "third")));
    page2.put("paging", new LinkedHashMap<>());

    when(http.getMap(eq("/"), any())).thenReturn(page1, page2);

    List<ContextMemory> all = memories.list();

    assertEquals(3, all.size());
    assertEquals("m-1", all.get(0).getId());
    assertEquals("m-2", all.get(1).getId());
    assertEquals("m-3", all.get(2).getId());
    verify(http, times(2)).getMap(eq("/"), any());
  }

  @Test
  @DisplayName("list applies primaryEntityFqn filter param")
  void listPassesPrimaryEntityFqn() {
    Map<String, Object> empty = new LinkedHashMap<>();
    empty.put("data", new ArrayList<>());
    empty.put("paging", new LinkedHashMap<>());
    when(http.getMap(eq("/"), any())).thenReturn(empty);

    memories.list("orders.fqn", null);

    @SuppressWarnings("unchecked")
    ArgumentCaptor<Map<String, Object>> captor = ArgumentCaptor.forClass(Map.class);
    verify(http).getMap(eq("/"), captor.capture());
    assertEquals("orders.fqn", captor.getValue().get("primaryEntityFqn"));
  }

  @Test
  @DisplayName("list respects limit and stops paginating")
  void listRespectsLimit() {
    Map<String, Object> page1 = new LinkedHashMap<>();
    page1.put("data", Arrays.asList(memoryMap("m-1", "one"), memoryMap("m-2", "two")));
    Map<String, Object> paging1 = new LinkedHashMap<>();
    paging1.put("after", "cursor-1");
    page1.put("paging", paging1);
    when(http.getMap(eq("/"), any())).thenReturn(page1);

    List<ContextMemory> capped = memories.list(null, 1);

    assertEquals(1, capped.size());
    assertEquals("m-1", capped.get(0).getId());
    verify(http, times(1)).getMap(eq("/"), any());
  }

  @Test
  @DisplayName("get fetches /{id} and parses ContextMemory")
  void getFetchesByIdAndParses() {
    when(http.getMap(eq("/abc-123"), any())).thenReturn(memoryMap("abc-123", "got it"));

    ContextMemory cm = memories.get("abc-123");

    assertEquals("abc-123", cm.getId());
    assertEquals("got it", cm.getName());
    verify(http).getMap(eq("/abc-123"), any());
  }

  @Test
  @DisplayName("create posts the toApiMap payload and parses response")
  void createPostsApiMapAndParses() {
    CreateContextMemoryRequest request =
        CreateContextMemoryRequest.builder()
            .name("pref-tone")
            .question("Preferred tone?")
            .answer("Concise.")
            .memoryType(MemoryType.PREFERENCE)
            .memoryScope(MemoryScope.USER_GLOBAL)
            .visibility(MemoryVisibility.SHARED)
            .tags(Arrays.asList("PII.Sensitive"))
            .build();

    when(http.postMap(eq("/"), any())).thenReturn(memoryMap("new-id", "pref-tone"));

    ContextMemory created = memories.create(request);

    assertEquals("new-id", created.getId());
    @SuppressWarnings("unchecked")
    ArgumentCaptor<Map<String, Object>> captor = ArgumentCaptor.forClass(Map.class);
    verify(http).postMap(eq("/"), captor.capture());

    Map<String, Object> body = captor.getValue();
    assertEquals("pref-tone", body.get("name"));
    assertEquals("Preference", body.get("memoryType"));
    assertEquals("UserGlobal", body.get("memoryScope"));
    @SuppressWarnings("unchecked")
    Map<String, Object> shareConfig = (Map<String, Object>) body.get("shareConfig");
    assertNotNull(shareConfig);
    assertEquals("Shared", shareConfig.get("visibility"));
    assertNull(body.get("visibility"));

    @SuppressWarnings("unchecked")
    List<Map<String, Object>> tagLabels = (List<Map<String, Object>>) body.get("tags");
    assertEquals(1, tagLabels.size());
    Map<String, Object> tag = tagLabels.get(0);
    assertEquals("PII.Sensitive", tag.get("tagFQN"));
    assertEquals("Manual", tag.get("labelType"));
    assertEquals("Confirmed", tag.get("state"));
    assertEquals("Classification", tag.get("source"));
  }

  @Test
  @DisplayName("delete passes hardDelete=false by default")
  void deleteDefaultsToSoftDelete() {
    memories.delete("mem-x");

    @SuppressWarnings("unchecked")
    ArgumentCaptor<Map<String, Object>> captor = ArgumentCaptor.forClass(Map.class);
    verify(http).delete(eq("/mem-x"), captor.capture());
    assertEquals(Boolean.FALSE, captor.getValue().get("hardDelete"));
  }

  @Test
  @DisplayName("delete passes hardDelete=true when requested")
  void deleteHonoursHardDelete() {
    memories.delete("mem-x", true);

    @SuppressWarnings("unchecked")
    ArgumentCaptor<Map<String, Object>> captor = ArgumentCaptor.forClass(Map.class);
    verify(http).delete(eq("/mem-x"), captor.capture());
    assertEquals(Boolean.TRUE, captor.getValue().get("hardDelete"));
  }

  @Test
  @DisplayName("search GETs /hybrid/nlq/search with q, index and pagination")
  void searchSendsExpectedParams() {
    when(searchHttp.getMap(eq("/hybrid/nlq/search"), any())).thenReturn(emptySearchResponse());

    memories.search("show me orders", null, 25, 5);

    @SuppressWarnings("unchecked")
    ArgumentCaptor<Map<String, Object>> captor = ArgumentCaptor.forClass(Map.class);
    verify(searchHttp).getMap(eq("/hybrid/nlq/search"), captor.capture());
    Map<String, Object> params = captor.getValue();
    assertEquals("show me orders", params.get("q"));
    assertEquals("contextMemory", params.get("index"));
    assertEquals(25, params.get("size"));
    assertEquals(5, params.get("from"));
    assertFalse(params.containsKey("filters"));
  }

  @Test
  @DisplayName("search serializes filters as JSON when provided")
  void searchSerializesFilters() {
    when(searchHttp.getMap(eq("/hybrid/nlq/search"), any())).thenReturn(emptySearchResponse());
    Map<String, List<String>> filters = new LinkedHashMap<>();
    filters.put("primaryEntityId", Arrays.asList("abc"));
    filters.put("visibility", Arrays.asList("Shared"));

    memories.search("query", filters, 10, 0);

    @SuppressWarnings("unchecked")
    ArgumentCaptor<Map<String, Object>> captor = ArgumentCaptor.forClass(Map.class);
    verify(searchHttp).getMap(anyString(), captor.capture());
    Object filtersParam = captor.getValue().get("filters");
    assertNotNull(filtersParam);
    String filtersJson = String.valueOf(filtersParam);
    assertTrue(filtersJson.contains("primaryEntityId"));
    assertTrue(filtersJson.contains("Shared"));
  }

  @Test
  @DisplayName("search parses OpenSearch response into MemorySearchResults")
  void searchParsesOpenSearchResponse() {
    Map<String, Object> hit = new LinkedHashMap<>();
    hit.put("_score", 0.91);
    hit.put("_source", memoryMap("m-1", "matched"));

    Map<String, Object> total = new LinkedHashMap<>();
    total.put("value", 7);

    Map<String, Object> hitsBlock = new LinkedHashMap<>();
    hitsBlock.put("total", total);
    hitsBlock.put("hits", Collections.singletonList(hit));

    Map<String, Object> response = new LinkedHashMap<>();
    response.put("hits", hitsBlock);

    when(searchHttp.getMap(eq("/hybrid/nlq/search"), any())).thenReturn(response);

    MemorySearchResults results = memories.search("orders");

    assertEquals(7, results.getTotal());
    assertEquals(1, results.getHits().size());
    assertEquals("m-1", results.getHits().get(0).getMemory().getId());
    assertEquals(0.91, results.getHits().get(0).getScore(), 1e-9);
    verify(http, never()).getMap(anyString(), any());
  }

  @Test
  @DisplayName("ContextMemory.fromMap flattens shareConfig.visibility")
  void contextMemoryFromMapFlattensVisibility() {
    Map<String, Object> data = memoryMap("id-1", "name-1");
    Map<String, Object> shareConfig = new LinkedHashMap<>();
    shareConfig.put("visibility", "Shared");
    data.put("shareConfig", shareConfig);

    ContextMemory cm = ContextMemory.fromMap(data);

    assertEquals(MemoryVisibility.SHARED, cm.getVisibility());
  }

  // ---------- helpers ----------

  private static Map<String, Object> memoryMap(String id, String name) {
    Map<String, Object> m = new LinkedHashMap<>();
    m.put("id", id);
    m.put("name", name);
    m.put("question", "q?");
    m.put("answer", "a.");
    m.put("memoryType", "Note");
    m.put("memoryScope", "EntityScoped");
    Map<String, Object> share = new LinkedHashMap<>();
    share.put("visibility", "Private");
    m.put("shareConfig", share);
    return m;
  }

  private static Map<String, Object> emptySearchResponse() {
    Map<String, Object> total = new LinkedHashMap<>();
    total.put("value", 0);
    Map<String, Object> hits = new LinkedHashMap<>();
    hits.put("total", total);
    hits.put("hits", new ArrayList<>());
    Map<String, Object> response = new LinkedHashMap<>();
    response.put("hits", hits);
    return response;
  }
}
