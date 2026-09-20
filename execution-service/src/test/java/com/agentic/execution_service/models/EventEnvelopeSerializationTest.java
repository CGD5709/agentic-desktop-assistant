package com.agentic.execution_service.models;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class EventEnvelopeSerializationTest {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    void shouldDeserializeExecutionRequestFromPython() throws Exception {
        String jsonFromPython = """
                {
                    "metadata": {
                        "eventId": "test-event-1",
                        "correlationId": "corr-uuid-123",
                        "timestamp": 1726150000000,
                        "source": "reasoning-engine",
                        "eventType": "EXECUTION_REQUEST"
                    },
                    "payload": {
                        "toolName": "escanear_puerto",
                        "arguments": {
                            "puerto": 8080
                        }
                    }
                }
                """;

        EventEnvelope<ToolExecutionRequestPayload> envelope = objectMapper.readValue(
                jsonFromPython,
                new TypeReference<EventEnvelope<ToolExecutionRequestPayload>>() {}
        );

        assertThat(envelope).isNotNull();
        assertThat(envelope.metadata()).isNotNull();
        assertThat(envelope.metadata().eventId()).isEqualTo("test-event-1");
        assertThat(envelope.metadata().correlationId()).isEqualTo("corr-uuid-123");
        assertThat(envelope.metadata().eventType()).isEqualTo(EventType.EXECUTION_REQUEST);

        assertThat(envelope.payload()).isNotNull();
        assertThat(envelope.payload().toolName()).isEqualTo("escanear_puerto");
        assertThat(envelope.payload().arguments()).containsEntry("puerto", 8080);
    }

    @Test
    void shouldSerializeExecutionResponseMatchingPythonContract() throws Exception {
        EventMetadata metadata = new EventMetadata(
                "resp-event-1",
                "corr-uuid-123",
                1726150001000L,
                "execution-service",
                EventType.EXECUTION_RESPONSE
        );

        ToolExecutionResponsePayload payload = ToolExecutionResponsePayload.success(
                "escanear_puerto",
                "Puerto 8080 está libre."
        );

        EventEnvelope<ToolExecutionResponsePayload> envelope = new EventEnvelope<>(metadata, payload);
        String json = objectMapper.writeValueAsString(envelope);

        assertThat(json).contains("\"toolName\":\"escanear_puerto\"");
        assertThat(json).contains("\"status\":\"SUCCESS\"");
        assertThat(json).contains("\"output\":\"Puerto 8080 está libre.\"");
        assertThat(json).doesNotContain("errorCode"); // Non-null inclusion rule
    }

    @Test
    void shouldSerializeExecutionErrorWithErrorCode() throws Exception {
        ToolExecutionResponsePayload payload = ToolExecutionResponsePayload.error(
                "desconocido",
                "Herramienta no encontrada",
                "TOOL_NOT_FOUND"
        );

        String json = objectMapper.writeValueAsString(payload);

        assertThat(json).contains("\"status\":\"ERROR\"");
        assertThat(json).contains("\"errorCode\":\"TOOL_NOT_FOUND\"");
    }

    @Test
    void shouldSerializeToolRegistryPayloadMatchingDiscoveryContract() throws Exception {
        ToolDefinition definition = new ToolDefinition(
                "abrir_sitio_web",
                "Abre una web",
                Map.of("type", "object")
        );

        ToolDefinition criticalDef = new ToolDefinition(
                "matar_proceso",
                "Mata un proceso",
                Map.of("type", "object"),
                true
        );

        ToolRegistryPayload registryPayload = new ToolRegistryPayload(List.of(definition, criticalDef));
        String json = objectMapper.writeValueAsString(registryPayload);

        assertThat(json).contains("\"tools\":[");
        assertThat(json).contains("\"name\":\"abrir_sitio_web\"");
        assertThat(json).contains("\"critical\":false");
        assertThat(json).contains("\"name\":\"matar_proceso\"");
        assertThat(json).contains("\"critical\":true");
    }
}
