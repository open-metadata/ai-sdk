package io.openmetadata.ai.models;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/** Token usage statistics for an agent invocation. */
@JsonIgnoreProperties(ignoreUnknown = true)
public class Usage {

  @JsonProperty("promptTokens")
  private int promptTokens;

  @JsonProperty("completionTokens")
  private int completionTokens;

  @JsonProperty("totalTokens")
  private int totalTokens;

  public Usage() {}

  public Usage(int promptTokens, int completionTokens, int totalTokens) {
    this.promptTokens = promptTokens;
    this.completionTokens = completionTokens;
    this.totalTokens = totalTokens;
  }

  public int getPromptTokens() {
    return promptTokens;
  }

  public void setPromptTokens(int promptTokens) {
    this.promptTokens = promptTokens;
  }

  public int getCompletionTokens() {
    return completionTokens;
  }

  public void setCompletionTokens(int completionTokens) {
    this.completionTokens = completionTokens;
  }

  public int getTotalTokens() {
    return totalTokens;
  }

  public void setTotalTokens(int totalTokens) {
    this.totalTokens = totalTokens;
  }

  @Override
  public String toString() {
    return "Usage{"
        + "promptTokens="
        + promptTokens
        + ", completionTokens="
        + completionTokens
        + ", totalTokens="
        + totalTokens
        + '}';
  }
}
