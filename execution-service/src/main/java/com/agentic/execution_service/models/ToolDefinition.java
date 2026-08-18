package com.agentic.execution_service.models;

import java.util.Map;

public record ToolDefinition(
    String name,
    String description,
    // Usamos Map para poder representar el JSON Schema de los argumentos
    Map<String, Object> parameters 
) {}
