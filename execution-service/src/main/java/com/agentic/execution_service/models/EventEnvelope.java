package com.agentic.execution_service.models;

import java.util.Objects;

/**
 * Generic message envelope for inter-service communication over RabbitMQ.
 *
 * Provides a standardized structure wrapping domain payloads with consistent
 * traceability and routing metadata.
 */
public record EventEnvelope<T>(
    EventMetadata metadata,
    T payload
) {

    public EventEnvelope {
        Objects.requireNonNull(metadata, "Event metadata must not be null");
    }
}
