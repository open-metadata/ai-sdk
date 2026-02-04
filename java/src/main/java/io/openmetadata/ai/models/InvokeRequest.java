package io.openmetadata.ai.models;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.Map;

/**
 * Request body for agent invocation.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class InvokeRequest {

    @JsonProperty("message")
    private String message;

    @JsonProperty("conversationId")
    private String conversationId;

    @JsonProperty("parameters")
    private Map<String, Object> parameters;

    public InvokeRequest() {
    }

    public InvokeRequest(String message) {
        this.message = message;
    }

    public InvokeRequest(String message, String conversationId) {
        this.message = message;
        this.conversationId = conversationId;
    }

    public InvokeRequest(String message, String conversationId, Map<String, Object> parameters) {
        this.message = message;
        this.conversationId = conversationId;
        this.parameters = parameters;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public String getConversationId() {
        return conversationId;
    }

    public void setConversationId(String conversationId) {
        this.conversationId = conversationId;
    }

    public Map<String, Object> getParameters() {
        return parameters;
    }

    public void setParameters(Map<String, Object> parameters) {
        this.parameters = parameters;
    }

    /**
     * Creates a new builder for InvokeRequest.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String message;
        private String conversationId;
        private Map<String, Object> parameters;

        public Builder message(String message) {
            this.message = message;
            return this;
        }

        public Builder conversationId(String conversationId) {
            this.conversationId = conversationId;
            return this;
        }

        public Builder parameters(Map<String, Object> parameters) {
            this.parameters = parameters;
            return this;
        }

        public InvokeRequest build() {
            // Message is optional - if not provided, the backend will use the agent's default prompt
            return new InvokeRequest(message, conversationId, parameters);
        }
    }

    @Override
    public String toString() {
        return "InvokeRequest{" +
                "message='" + message + '\'' +
                ", conversationId='" + conversationId + '\'' +
                ", parameters=" + parameters +
                '}';
    }
}
