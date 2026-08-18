package com.agentic.execution_service.models;

public record EventMetadata(
    String eventId,
    String correlationId,
    long timestamp,
    String source,
    EventType eventType
) {}