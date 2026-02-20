package io.openmetadata.ai.models;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/** Response from a synchronous agent invocation. */
@JsonIgnoreProperties(ignoreUnknown = true)
public class InvokeResponse {

  @JsonProperty("conversationId")
  private String conversationId;

  @JsonProperty("response")
  private String response;

  @JsonProperty("toolsUsed")
  private List<String> toolsUsed;

  @JsonProperty("usage")
  private Usage usage;

  public InvokeResponse() {}

  public InvokeResponse(
      String conversationId, String response, List<String> toolsUsed, Usage usage) {
    this.conversationId = conversationId;
    this.response = response;
    this.toolsUsed = toolsUsed;
    this.usage = usage;
  }

  public String getConversationId() {
    return conversationId;
  }

  public void setConversationId(String conversationId) {
    this.conversationId = conversationId;
  }

  public String getResponse() {
    return response;
  }

  public void setResponse(String response) {
    this.response = response;
  }

  public List<String> getToolsUsed() {
    return toolsUsed;
  }

  public void setToolsUsed(List<String> toolsUsed) {
    this.toolsUsed = toolsUsed;
  }

  public Usage getUsage() {
    return usage;
  }

  public void setUsage(Usage usage) {
    this.usage = usage;
  }

  /** Creates a new builder for InvokeResponse. */
  public static Builder builder() {
    return new Builder();
  }

  public static class Builder {
    private String conversationId;
    private String response;
    private List<String> toolsUsed;
    private Usage usage;

    public Builder conversationId(String conversationId) {
      this.conversationId = conversationId;
      return this;
    }

    public Builder response(String response) {
      this.response = response;
      return this;
    }

    public Builder toolsUsed(List<String> toolsUsed) {
      this.toolsUsed = toolsUsed;
      return this;
    }

    public Builder usage(Usage usage) {
      this.usage = usage;
      return this;
    }

    public InvokeResponse build() {
      return new InvokeResponse(conversationId, response, toolsUsed, usage);
    }
  }

  @Override
  public String toString() {
    return "InvokeResponse{"
        + "conversationId='"
        + conversationId
        + '\''
        + ", response='"
        + response
        + '\''
        + ", toolsUsed="
        + toolsUsed
        + ", usage="
        + usage
        + '}';
  }
}
