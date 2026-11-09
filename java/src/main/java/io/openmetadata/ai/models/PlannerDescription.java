package io.openmetadata.ai.models;

import com.fasterxml.jackson.annotation.JsonInclude;

/** Capabilities and instructions of a planner-dispatched worker. */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class PlannerDescription {
  public String description;
  public String input;
  public String output;
  public String prompt;

  public PlannerDescription() {}

  public PlannerDescription(String description, String input, String output, String prompt) {
    this.description = description;
    this.input = input;
    this.output = output;
    this.prompt = prompt;
  }
}
