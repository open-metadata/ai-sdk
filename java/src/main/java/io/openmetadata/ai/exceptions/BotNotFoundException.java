package io.openmetadata.ai.exceptions;

/** Exception thrown when a bot is not found (HTTP 404). */
public class BotNotFoundException extends MetadataException {

  private final String botName;

  public BotNotFoundException(String botName) {
    super("Bot not found: " + botName, 404);
    this.botName = botName;
  }

  /** Returns the name of the bot that was not found. */
  public String getBotName() {
    return botName;
  }
}
