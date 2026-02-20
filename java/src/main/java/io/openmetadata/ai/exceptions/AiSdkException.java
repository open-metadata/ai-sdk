package io.openmetadata.ai.exceptions;

/** Base exception for all AI SDK errors. */
public class AiSdkException extends RuntimeException {

  private final int statusCode;

  public AiSdkException(String message) {
    super(message);
    this.statusCode = 0;
  }

  public AiSdkException(String message, int statusCode) {
    super(message);
    this.statusCode = statusCode;
  }

  public AiSdkException(String message, Throwable cause) {
    super(message, cause);
    this.statusCode = 0;
  }

  public AiSdkException(String message, int statusCode, Throwable cause) {
    super(message, cause);
    this.statusCode = statusCode;
  }

  /**
   * Returns the HTTP status code associated with this error. Returns 0 if no status code is
   * applicable.
   */
  public int getStatusCode() {
    return statusCode;
  }
}
