package com.agentic.execution_service.models;

import java.time.Instant;
import java.util.UUID;

/**
 * Standard metadata header for inter-service communication events.
 *
 *
 * @param correlationId Correlation identifier matching the caller's
 *                      asynchronous future or task.
 * @param timestamp     Epoch timestamp in milliseconds when the event was
 *                      produced.
 * @param source        Originating service name (e.g., "execution-service").
 */
public record EventMetadata(
        String eventId,
        String correlationId,
        long timestamp,
        String source,
        EventType eventType) {

    public static EventMetadata now(String correlationId, String source, EventType eventType) {
        return new EventMetadata(
                UUID.randomUUID().toString(),
                correlationId,
                Instant.now().toEpochMilli(),
                source,
                eventType);
    }
}