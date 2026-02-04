package io.openmetadata.ai.exceptions;

import java.util.Optional;

/** Exception thrown when rate limit is exceeded (HTTP 429). */
public class RateLimitException extends MetadataException {

  private final Integer retryAfter;

  public RateLimitException(String message) {
    super(message, 429);
    this.retryAfter = null;
  }

  public RateLimitException(String message, Integer retryAfter) {
    super(message, 429);
    this.retryAfter = retryAfter;
  }

  /** Returns the number of seconds to wait before retrying, if provided by the server. */
  public Optional<Integer> getRetryAfter() {
    return Optional.ofNullable(retryAfter);
  }
}
