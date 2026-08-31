package com.agentic.execution_service.service;

import com.agentic.execution_service.config.RabbitMQConfig;
import com.agentic.execution_service.models.EventEnvelope;
import com.agentic.execution_service.models.EventMetadata;
import com.agentic.execution_service.models.EventType;
import com.agentic.execution_service.models.ToolDefinition;
import com.agentic.execution_service.tools.AgentTool;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

@Component
public class ToolRegistryBroadcaster {

    private final RabbitTemplate rabbitTemplate;
    private final List<AgentTool> availableTools; // Spring inyecta aquí todas las herramientas

    public ToolRegistryBroadcaster(RabbitTemplate rabbitTemplate, List<AgentTool> availableTools) {
        this.rabbitTemplate = rabbitTemplate;
        this.availableTools = availableTools;
    }

    @EventListener(ApplicationReadyEvent.class)
    public void broadcastTools() {
        System.out.println("\n📢 [System Discovery] Anunciando herramientas disponibles en la red...");

        // Extraemos las definiciones llamando al método getDefinition() de cada herramienta
        List<ToolDefinition> toolDefinitions = availableTools.stream()
                .map(AgentTool::getDefinition)
                .collect(Collectors.toList());

        EventMetadata metadata = new EventMetadata(
                UUID.randomUUID().toString(),
                "system-startup",
                Instant.now().toEpochMilli(),
                "execution-service",
                EventType.TOOL_REGISTRY_BROADCAST
        );

        Map<String, Object> payload = Map.of("tools", toolDefinitions);
        EventEnvelope envelope = new EventEnvelope(metadata, payload);

        String routingKey = "system.discovery.execution_service";
        rabbitTemplate.convertAndSend(RabbitMQConfig.EXCHANGE_NAME, routingKey, envelope);
        
        List<String> toolNames = availableTools.stream().map(AgentTool::getName).collect(Collectors.toList());
        System.out.println("   -> ✅ Manifiesto publicado: " + toolNames);
    }
}