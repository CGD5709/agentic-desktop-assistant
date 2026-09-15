package com.agentic.execution_service.service;

import com.agentic.execution_service.config.RabbitMQConfig;
import com.agentic.execution_service.models.EventEnvelope;
import com.agentic.execution_service.models.EventMetadata;
import com.agentic.execution_service.models.EventType;
import com.agentic.execution_service.models.ToolDefinition;
import com.agentic.execution_service.models.ToolRegistryPayload;
import com.agentic.execution_service.tools.AgentTool;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.AmqpException;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Objects;
import java.util.stream.Collectors;

/**
 * Broadcasts available OS tools upon application startup for dynamic discovery by the reasoning engine.
 */
@Component
public class ToolRegistryBroadcaster {

    private static final Logger logger = LoggerFactory.getLogger(ToolRegistryBroadcaster.class);

    public static final String ROUTING_KEY_DISCOVERY = "system.discovery.execution_service";
    public static final String CORRELATION_STARTUP = "system-startup";
    public static final String SOURCE_SERVICE_NAME = "execution-service";

    private final RabbitTemplate rabbitTemplate;
    private final List<AgentTool> availableTools;

    public ToolRegistryBroadcaster(RabbitTemplate rabbitTemplate, List<AgentTool> availableTools) {
        this.rabbitTemplate = Objects.requireNonNull(rabbitTemplate, "RabbitTemplate must not be null");
        this.availableTools = availableTools != null ? List.copyOf(availableTools) : List.of();
    }

    @EventListener(ApplicationReadyEvent.class)
    public void broadcastTools() {
        logger.info("Announcing available execution tools to the network...");

        List<ToolDefinition> toolDefinitions = availableTools.stream()
                .map(AgentTool::getDefinition)
                .collect(Collectors.toList());

        EventMetadata metadata = EventMetadata.now(
                CORRELATION_STARTUP,
                SOURCE_SERVICE_NAME,
                EventType.TOOL_REGISTRY_BROADCAST
        );

        ToolRegistryPayload payload = new ToolRegistryPayload(toolDefinitions);
        EventEnvelope<ToolRegistryPayload> envelope = new EventEnvelope<>(metadata, payload);

        List<String> toolNames = availableTools.stream()
                .map(AgentTool::getName)
                .toList();

        try {
            rabbitTemplate.convertAndSend(RabbitMQConfig.EXCHANGE_NAME, ROUTING_KEY_DISCOVERY, envelope);
            logger.info("Tool manifest published successfully: {}", toolNames);
        } catch (AmqpException ex) {
            logger.warn("Failed to broadcast tool registry on startup: {}", ex.getMessage(), ex);
        }
    }
}