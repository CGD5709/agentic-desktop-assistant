package com.agentic.execution_service.models;

import java.util.Map;

/**
 * Inbound payload representing an explicit request to execute an operating system tool.
 *
 * Dispatched over RabbitMQ by the reasoning engine orchestrator (Python) 
 * upon resolving an agent action step.
 */
public record ToolExecutionRequestPayload(
    String toolName,
    Map<String, Object> arguments
) {

    public ToolExecutionRequestPayload {
        arguments = arguments != null ? Map.copyOf(arguments) : Map.of();
    }
}
