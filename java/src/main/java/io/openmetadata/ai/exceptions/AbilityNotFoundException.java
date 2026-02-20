package io.openmetadata.ai.exceptions;

/** Exception thrown when an ability is not found (HTTP 404). */
public class AbilityNotFoundException extends AiSdkException {

  private final String abilityName;

  public AbilityNotFoundException(String abilityName) {
    super("Ability not found: " + abilityName, 404);
    this.abilityName = abilityName;
  }

  /** Returns the name of the ability that was not found. */
  public String getAbilityName() {
    return abilityName;
  }
}
