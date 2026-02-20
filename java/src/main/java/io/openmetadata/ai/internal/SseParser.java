package io.openmetadata.ai.internal;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.Iterator;
import java.util.NoSuchElementException;
import java.util.function.Consumer;
import java.util.stream.Stream;
import java.util.stream.StreamSupport;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import io.openmetadata.ai.models.StreamEvent;

/** Parser for Server-Sent Events (SSE) format. */
public class SseParser {

  private final ObjectMapper objectMapper;

  public SseParser(ObjectMapper objectMapper) {
    this.objectMapper = objectMapper;
  }

  /** Parses SSE events from an input stream and calls the consumer for each event. */
  public void parse(InputStream inputStream, Consumer<StreamEvent> eventConsumer)
      throws IOException {
    try (BufferedReader reader =
        new BufferedReader(new InputStreamReader(inputStream, StandardCharsets.UTF_8))) {

      String eventType = null;
      StringBuilder dataBuilder = new StringBuilder();

      String line;
      while ((line = reader.readLine()) != null) {
        if (line.isEmpty()) {
          // Empty line indicates end of event
          if (eventType != null && dataBuilder.length() > 0) {
            StreamEvent event = parseEvent(eventType, dataBuilder.toString());
            if (event != null) {
              eventConsumer.accept(event);
            }
          }
          eventType = null;
          dataBuilder.setLength(0);
        } else if (line.startsWith("event:")) {
          eventType = line.substring(6).trim();
        } else if (line.startsWith("data:")) {
          if (dataBuilder.length() > 0) {
            dataBuilder.append("\n");
          }
          dataBuilder.append(line.substring(5).trim());
        }
        // Ignore comments (lines starting with ':') and other fields
      }

      // Handle any remaining event
      if (eventType != null && dataBuilder.length() > 0) {
        StreamEvent event = parseEvent(eventType, dataBuilder.toString());
        if (event != null) {
          eventConsumer.accept(event);
        }
      }
    }
  }

  /**
   * Creates a Stream iterator for SSE events from an input stream. The returned Stream must be
   * closed when done.
   */
  public Stream<StreamEvent> parseAsStream(InputStream inputStream) {
    SseIterator iterator = new SseIterator(inputStream);
    Iterable<StreamEvent> iterable = () -> iterator;
    return StreamSupport.stream(iterable.spliterator(), false).onClose(iterator::close);
  }

  private StreamEvent parseEvent(String eventType, String data) {
    try {
      StreamEvent.Type type = parseEventType(eventType);
      if (type == null) {
        return null;
      }

      JsonNode jsonNode = objectMapper.readTree(data);
      StreamEvent.Builder builder = StreamEvent.builder().type(type);

      if (type == StreamEvent.Type.ERROR) {
        if (jsonNode.has("message")) {
          builder.error(jsonNode.get("message").asText());
        } else if (jsonNode.has("error")) {
          builder.error(jsonNode.get("error").asText());
        } else {
          builder.error(data);
        }
        return builder.build();
      }

      // Handle nested API response structure:
      // {"data": {"message": {"content": [{"textMessage": {"message": "..."}, "tools": [...]}]}}}
      JsonNode dataNode = jsonNode.has("data") ? jsonNode.get("data") : jsonNode;
      JsonNode messageNode = dataNode.has("message") ? dataNode.get("message") : null;

      if (messageNode != null
          && messageNode.has("content")
          && messageNode.get("content").isArray()) {
        JsonNode contentArray = messageNode.get("content");
        StringBuilder textContent = new StringBuilder();
        String toolName = null;

        for (JsonNode contentItem : contentArray) {
          // Extract textMessage
          if (contentItem.has("textMessage")) {
            JsonNode textMessage = contentItem.get("textMessage");
            if (textMessage.has("message")) {
              String msg = textMessage.get("message").asText();
              if (msg != null && !msg.isEmpty()) {
                textContent.append(msg);
              }
            }
          }

          // Extract tool name from tools array
          if (contentItem.has("tools") && contentItem.get("tools").isArray()) {
            for (JsonNode tool : contentItem.get("tools")) {
              if (tool.has("name")) {
                toolName = tool.get("name").asText();
                break; // Take first tool name
              }
            }
          }
        }

        if (textContent.length() > 0) {
          builder.content(textContent.toString());
        }
        if (toolName != null) {
          builder.toolName(toolName);
        }
      } else {
        // Fallback to flat structure for backward compatibility
        if (jsonNode.has("content")) {
          builder.content(jsonNode.get("content").asText());
        }
        if (jsonNode.has("toolName")) {
          builder.toolName(jsonNode.get("toolName").asText());
        }
      }

      // Extract conversationId from response
      if (dataNode != null && dataNode.has("conversationId")) {
        builder.conversationId(dataNode.get("conversationId").asText());
      } else if (jsonNode.has("conversationId")) {
        builder.conversationId(jsonNode.get("conversationId").asText());
      }

      return builder.build();
    } catch (com.fasterxml.jackson.core.JsonProcessingException e) {
      return null;
    }
  }

  private StreamEvent.Type parseEventType(String eventType) {
    if (eventType == null) {
      return null;
    }
    switch (eventType.toLowerCase().replace("-", "_")) {
      case "stream_start":
      case "start":
        return StreamEvent.Type.START;
      case "message":
      case "content":
        return StreamEvent.Type.CONTENT;
      case "tool_use":
        return StreamEvent.Type.TOOL_USE;
      case "stream_completed":
      case "end":
        return StreamEvent.Type.END;
      case "error":
      case "fatal_error":
        return StreamEvent.Type.ERROR;
      default:
        return null;
    }
  }

  /** Iterator for SSE events that supports closing the underlying stream. */
  private class SseIterator implements Iterator<StreamEvent>, AutoCloseable {
    private final BufferedReader reader;
    private StreamEvent nextEvent;
    private boolean closed = false;
    private String currentEventType = null;
    private StringBuilder currentDataBuilder = new StringBuilder();

    SseIterator(InputStream inputStream) {
      this.reader = new BufferedReader(new InputStreamReader(inputStream, StandardCharsets.UTF_8));
      advance();
    }

    @Override
    public boolean hasNext() {
      return nextEvent != null;
    }

    @Override
    public StreamEvent next() {
      if (nextEvent == null) {
        throw new NoSuchElementException();
      }
      StreamEvent event = nextEvent;
      advance();
      return event;
    }

    private void advance() {
      nextEvent = null;
      if (closed) {
        return;
      }

      try {
        String line;
        while ((line = reader.readLine()) != null) {
          if (line.isEmpty()) {
            // Empty line indicates end of event
            if (currentEventType != null && currentDataBuilder.length() > 0) {
              StreamEvent event = parseEvent(currentEventType, currentDataBuilder.toString());
              currentEventType = null;
              currentDataBuilder.setLength(0);
              if (event != null) {
                nextEvent = event;
                return;
              }
            }
            currentEventType = null;
            currentDataBuilder.setLength(0);
          } else if (line.startsWith("event:")) {
            currentEventType = line.substring(6).trim();
          } else if (line.startsWith("data:")) {
            if (currentDataBuilder.length() > 0) {
              currentDataBuilder.append("\n");
            }
            currentDataBuilder.append(line.substring(5).trim());
          }
        }

        // Handle any remaining event
        if (currentEventType != null && currentDataBuilder.length() > 0) {
          StreamEvent event = parseEvent(currentEventType, currentDataBuilder.toString());
          currentEventType = null;
          currentDataBuilder.setLength(0);
          if (event != null) {
            nextEvent = event;
          }
        }
      } catch (IOException e) {
        close();
      }
    }

    @Override
    public void close() {
      if (!closed) {
        closed = true;
        try {
          reader.close();
        } catch (IOException e) {
          // Ignore
        }
      }
    }
  }
}
