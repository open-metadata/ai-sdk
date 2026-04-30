package io.openmetadata.ai.api;

import java.util.List;
import java.util.Objects;

import io.openmetadata.ai.internal.AISdkHttpClient;
import io.openmetadata.ai.models.CreatePersonaRequest;
import io.openmetadata.ai.models.PersonaInfo;

/** Namespace for persona operations. */
public class PersonasApi {

  private final AISdkHttpClient http;

  public PersonasApi(AISdkHttpClient http) {
    this.http = Objects.requireNonNull(http, "http cannot be null");
  }

  /** List all personas. */
  public List<PersonaInfo> list() {
    return http.listPersonas();
  }

  /** List personas up to limit. */
  public List<PersonaInfo> list(int limit) {
    return http.listPersonas(limit);
  }

  /** Get a persona by name. */
  public PersonaInfo get(String name) {
    Objects.requireNonNull(name, "Persona name cannot be null");
    return http.getPersonaByName(name);
  }

  /** Create a new persona. */
  public PersonaInfo create(CreatePersonaRequest request) {
    Objects.requireNonNull(request, "CreatePersonaRequest cannot be null");
    return http.createPersona(request);
  }
}
