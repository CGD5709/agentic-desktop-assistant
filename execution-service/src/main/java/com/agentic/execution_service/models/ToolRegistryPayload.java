package com.agentic.execution_service.models;

import java.util.List;

/**
 * Manifest payload declaring active tools for zero-configuration discovery by the reasoning engine.
 */
public record ToolRegistryPayload(
    List<ToolDefinition> tools
) {

    public ToolRegistryPayload {
        tools = tools != null ? List.copyOf(tools) : List.of();
    }
}
