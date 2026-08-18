package com.agentic.execution_service.models;

import java.util.Map;

public record EventEnvelope(
    EventMetadata metadata,
    Map<String, Object> payload
) {}
