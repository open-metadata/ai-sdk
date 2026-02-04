package io.openmetadata.ai.exceptions;

/**
 * Base exception for all Metadata AI SDK errors.
 */
public class MetadataException extends RuntimeException {

    private final int statusCode;

    public MetadataException(String message) {
        super(message);
        this.statusCode = 0;
    }

    public MetadataException(String message, int statusCode) {
        super(message);
        this.statusCode = statusCode;
    }

    public MetadataException(String message, Throwable cause) {
        super(message, cause);
        this.statusCode = 0;
    }

    public MetadataException(String message, int statusCode, Throwable cause) {
        super(message, cause);
        this.statusCode = statusCode;
    }

    /**
     * Returns the HTTP status code associated with this error.
     * Returns 0 if no status code is applicable.
     */
    public int getStatusCode() {
        return statusCode;
    }
}
