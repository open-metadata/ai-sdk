package io.openmetadata.ai.exceptions;

/** Exception thrown when a persona is not found (HTTP 404). */
public class PersonaNotFoundException extends AISdkException {

  private final String personaName;

  public PersonaNotFoundException(String personaName) {
    super("Persona not found: " + personaName, 404);
    this.personaName = personaName;
  }

  /** Returns the name of the persona that was not found. */
  public String getPersonaName() {
    return personaName;
  }
}
