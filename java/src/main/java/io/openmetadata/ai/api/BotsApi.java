package io.openmetadata.ai.api;

import java.util.List;
import java.util.Objects;

import io.openmetadata.ai.internal.AISdkHttpClient;
import io.openmetadata.ai.models.BotInfo;

/** Namespace for bot operations. */
public class BotsApi {

  private final AISdkHttpClient http;

  public BotsApi(AISdkHttpClient http) {
    this.http = Objects.requireNonNull(http, "http cannot be null");
  }

  /** List all bots. */
  public List<BotInfo> list() {
    return http.listBots();
  }

  /** List bots up to limit. */
  public List<BotInfo> list(int limit) {
    return http.listBots(limit);
  }

  /** Get a bot by name. */
  public BotInfo get(String name) {
    Objects.requireNonNull(name, "Bot name cannot be null");
    return http.getBotByName(name);
  }
}
