package io.openmetadata.ai.exceptions;

/**
 * Exception thrown when an agent exists but is not API-enabled (HTTP 403).
 */
public class AgentNotEnabledException extends MetadataException {

    private final String agentName;

    public AgentNotEnabledException(String agentName) {
        super("Agent is not API-enabled: " + agentName, 403);
        this.agentName = agentName;
    }

    /**
     * Returns the name of the agent that is not API-enabled.
     */
    public String getAgentName() {
        return agentName;
    }
}
