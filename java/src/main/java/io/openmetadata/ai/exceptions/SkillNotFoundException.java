package io.openmetadata.ai.exceptions;

/** Exception thrown when a skill is not found (HTTP 404). */
public class SkillNotFoundException extends AISdkException {

  private final String skillName;

  public SkillNotFoundException(String skillName) {
    super("Skill not found: " + skillName, 404);
    this.skillName = skillName;
  }

  /** Returns the name of the skill that was not found. */
  public String getSkillName() {
    return skillName;
  }
}
