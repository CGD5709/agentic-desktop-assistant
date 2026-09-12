package com.agentic.execution_service.models;

import java.util.Map;

/**
 * Metadata descriptor broadcasted across RabbitMQ for dynamic tool discovery.
 *
 * NOTE: This payload is consumed directly by the LLM's function calling layer.
 * Therefore, the 'description' must be optimized as a prompt for the AI, and 
 * the 'parameters' map must strictly adhere to the JSON Schema specification.
 */
public record ToolDefinition(
    String name,
    String description,
    Map<String, Object> parameters 
) {

    public ToolDefinition {
        parameters = parameters != null ? Map.copyOf(parameters) : Map.of();
    }
}
