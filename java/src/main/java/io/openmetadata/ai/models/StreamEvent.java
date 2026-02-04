package io.openmetadata.ai.models;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Event from a streaming agent invocation.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class StreamEvent {

    /**
     * Type of streaming event.
     */
    public enum Type {
        START,
        CONTENT,
        TOOL_USE,
        END
    }

    private Type type;

    @JsonProperty("content")
    private String content;

    @JsonProperty("toolName")
    private String toolName;

    @JsonProperty("conversationId")
    private String conversationId;

    public StreamEvent() {
    }

    public StreamEvent(Type type) {
        this.type = type;
    }

    public StreamEvent(Type type, String content, String toolName, String conversationId) {
        this.type = type;
        this.content = content;
        this.toolName = toolName;
        this.conversationId = conversationId;
    }

    public Type getType() {
        return type;
    }

    public void setType(Type type) {
        this.type = type;
    }

    public String getContent() {
        return content;
    }

    public void setContent(String content) {
        this.content = content;
    }

    public String getToolName() {
        return toolName;
    }

    public void setToolName(String toolName) {
        this.toolName = toolName;
    }

    public String getConversationId() {
        return conversationId;
    }

    public void setConversationId(String conversationId) {
        this.conversationId = conversationId;
    }

    /**
     * Creates a new builder for StreamEvent.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private Type type;
        private String content;
        private String toolName;
        private String conversationId;

        public Builder type(Type type) {
            this.type = type;
            return this;
        }

        public Builder content(String content) {
            this.content = content;
            return this;
        }

        public Builder toolName(String toolName) {
            this.toolName = toolName;
            return this;
        }

        public Builder conversationId(String conversationId) {
            this.conversationId = conversationId;
            return this;
        }

        public StreamEvent build() {
            return new StreamEvent(type, content, toolName, conversationId);
        }
    }

    @Override
    public String toString() {
        return "StreamEvent{" +
                "type=" + type +
                ", content='" + content + '\'' +
                ", toolName='" + toolName + '\'' +
                ", conversationId='" + conversationId + '\'' +
                '}';
    }
}
