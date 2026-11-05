package io.openmetadata.cookbook;

import io.openmetadata.ai.AISdk;
import io.openmetadata.ai.models.AgentInfo;
import io.openmetadata.ai.models.InvokeResponse;

public final class JavaSdkExample {
  public static void main(String[] args) {
    if (args.length == 0) {
      try (AISdk sdk = AISdk.builder().host("https://example.invalid").token("unused").build()) {
        System.out.println(
            "Loaded "
                + sdk.getClass().getSimpleName()
                + " and its dependencies. No API calls were made.");
      }
      return;
    }

    if (args.length != 1 || !"live".equals(args[0])) {
      throw new IllegalArgumentException("Usage: ./run.sh [live]");
    }

    try (AISdk sdk =
        AISdk.builder()
            .host(requiredEnv("AI_SDK_HOST"))
            .token(requiredEnv("AI_SDK_TOKEN"))
            .build()) {
      System.out.println("API-enabled agents:");
      for (AgentInfo agent : sdk.agents().list()) {
        System.out.println("- " + agent.getName());
      }

      String question =
          System.getenv().getOrDefault("AI_SDK_QUESTION", "What data assets are available?");
      String agentName = System.getenv("AI_SDK_TEST_AGENT");
      InvokeResponse response =
          agentName == null || agentName.isBlank()
              ? sdk.agent().invoke(question)
              : sdk.agent(agentName).invoke(question);
      System.out.println("Response: " + response.getResponse());
      System.out.println("Conversation: " + response.getConversationId());
    }
  }

  private static String requiredEnv(String name) {
    String value = System.getenv(name);
    if (value == null || value.isBlank()) {
      throw new IllegalArgumentException("Set " + name + " before running ./run.sh live");
    }
    return value;
  }
}
