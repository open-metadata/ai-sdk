package io.openmetadata.ai.exceptions;

/** Exception thrown when an agent is not found (HTTP 404). */
public class AgentNotFoundException extends AISdkException {

  private final String agentName;

  public AgentNotFoundException(String agentName) {
    super("Agent not found: " + agentName, 404);
    this.agentName = agentName;
  }

  /** Returns the name of the agent that was not found. */
  public String getAgentName() {
    return agentName;
  }
}
