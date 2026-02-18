package io.openmetadata.ai.exceptions;

/** Exception thrown when authentication fails (HTTP 401). */
public class AuthenticationException extends MetadataException {

  public AuthenticationException() {
    super("Invalid or expired token", 401);
  }

  public AuthenticationException(String message) {
    super(message, 401);
  }
}
