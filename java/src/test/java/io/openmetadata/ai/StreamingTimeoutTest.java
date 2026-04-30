package io.openmetadata.ai;

import static org.junit.jupiter.api.Assertions.*;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

import io.openmetadata.ai.models.StreamEvent;

/**
 * Verifies that an SSE stream is NOT cut off by the configured {@code timeout}.
 *
 * <p>Background: java.net.http.HttpClient supports two distinct timeouts:
 *
 * <ul>
 *   <li>{@code HttpClient.Builder.connectTimeout(...)} - TCP connect only.
 *   <li>{@code HttpRequest.Builder.timeout(...)} - bounds the entire response, including body read.
 * </ul>
 *
 * <p>The SDK only configures the former, so a long-running agent stream cannot be terminated by the
 * configured timeout. This test pins that contract: even with a 1-second configured timeout, a slow
 * streaming response that emits its events with delays exceeding 1 second still completes cleanly.
 */
class StreamingTimeoutTest {

  private HttpServer server;
  private int port;

  @BeforeEach
  void startServer() throws IOException {
    server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
    port = server.getAddress().getPort();
    server.start();
  }

  @AfterEach
  void stopServer() {
    if (server != null) {
      server.stop(0);
    }
  }

  /**
   * Registers a handler that emits 3 SSE message events with 700 ms gaps. Total stream duration
   * (~2.1 s) is well over the 1-second client timeout used below — if the per-request timeout were
   * applied to body reads, this test would fail with HttpTimeoutException.
   */
  private void registerSlowStreamHandler(String path) {
    HttpHandler handler =
        new HttpHandler() {
          @Override
          public void handle(HttpExchange exchange) throws IOException {
            exchange.getResponseHeaders().set("Content-Type", "text/event-stream");
            exchange.getResponseHeaders().set("Cache-Control", "no-cache");
            exchange.sendResponseHeaders(200, 0); // 0 = chunked

            try (OutputStream out = exchange.getResponseBody()) {
              for (int i = 0; i < 3; i++) {
                String chunk =
                    "event: message\n"
                        + "data: {\"type\":\"content\",\"content\":\"chunk-"
                        + i
                        + "\"}\n\n";
                out.write(chunk.getBytes());
                out.flush();
                try {
                  Thread.sleep(700L);
                } catch (InterruptedException ie) {
                  Thread.currentThread().interrupt();
                  return;
                }
              }
              String done = "event: message\n" + "data: {\"type\":\"end\"}\n\n";
              out.write(done.getBytes());
              out.flush();
            }
          }
        };
    server.createContext(path, handler);
  }

  @Test
  @DisplayName("Slow SSE stream does not time out under a short configured timeout")
  void slowStreamDoesNotTimeOutUnderShortTimeout() {
    // Streaming endpoint for a named agent: /api/v1/agents/dynamic/name/{agent}/stream
    String agentName = "slow-agent";
    String streamPath = "/api/v1/agents/dynamic/name/" + agentName + "/stream";
    registerSlowStreamHandler(streamPath);

    AISdk client =
        AISdk.builder()
            .host("http://127.0.0.1:" + port)
            .token("test-token")
            // Deliberately short — would cut the stream if applied to body reads.
            .timeout(Duration.ofSeconds(1))
            .maxRetries(0)
            .build();

    List<StreamEvent> events = new ArrayList<>();
    AtomicBoolean failed = new AtomicBoolean(false);

    try {
      client.agent(agentName).stream("hello", events::add);
    } catch (RuntimeException e) {
      failed.set(true);
      fail(
          "Stream should not throw on a 1s configured timeout for a ~2.1s SSE stream, "
              + "but got: "
              + e.getClass().getSimpleName()
              + ": "
              + e.getMessage());
    } finally {
      client.close();
    }

    assertFalse(failed.get(), "Stream call must not have thrown");
    assertFalse(events.isEmpty(), "Should have received at least one streamed event");
  }
}
