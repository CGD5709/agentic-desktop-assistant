package com.agentic.execution_service.service;

import com.agentic.execution_service.config.RabbitMQConfig;
import com.agentic.execution_service.models.EventEnvelope;
import com.agentic.execution_service.models.EventMetadata;
import com.agentic.execution_service.models.EventType;
import com.agentic.execution_service.tools.AgentTool;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;

@Service
public class ExecutionListener {

    private final RabbitTemplate rabbitTemplate;
    // Mapa dinámico de herramientas: "nombre_herramienta" -> Objeto de la herramienta
    private final Map<String, AgentTool> toolRegistry;

    public ExecutionListener(RabbitTemplate rabbitTemplate, List<AgentTool> tools) {
        this.rabbitTemplate = rabbitTemplate;
        // Convertimos la lista inyectada por Spring en un Map para buscar rápido por nombre
        this.toolRegistry = tools.stream()
                .collect(Collectors.toMap(AgentTool::getName, Function.identity()));
    }

    @RabbitListener(queues = RabbitMQConfig.QUEUE_NAME)
    public void receiveToolRequest(EventEnvelope requestEnvelope) {
        System.out.println("\n📥 [RabbitMQ] ¡Petición recibida desde Python!");
        
        String correlationId = requestEnvelope.metadata().correlationId();
        String toolName = (String) requestEnvelope.payload().get("toolName");
        
        System.out.println("   -> Herramienta solicitada: " + toolName);

        String output;
        String status = "SUCCESS";

        try {
            AgentTool tool = toolRegistry.get(toolName);
            
            if (tool != null) {
                @SuppressWarnings("unchecked")
                Map<String, Object> arguments = (Map<String, Object>) requestEnvelope.payload().get("arguments");
                
                // Ejecutamos la herramienta directamente sin IFs
                output = tool.execute(arguments);
            } else {
                status = "ERROR";
                output = "Herramienta desconocida para el microservicio Java: " + toolName;
            }
        } catch (Exception e) {
            status = "ERROR";
            output = "Fallo crítico al ejecutar el comando en el SO: " + e.toString();
        }

        EventMetadata responseMetadata = new EventMetadata(
                UUID.randomUUID().toString(),
                correlationId,
                Instant.now().toEpochMilli(),
                "java-execution-service",
                EventType.EXECUTION_RESPONSE
        );

        Map<String, Object> responsePayload = Map.of(
                "toolName", toolName,
                "status", status,
                "output", output
        );

        EventEnvelope responseEnvelope = new EventEnvelope(responseMetadata, responsePayload);

        String routingKey = "tool.response." + toolName;
        rabbitTemplate.convertAndSend(RabbitMQConfig.EXCHANGE_NAME, routingKey, responseEnvelope);
        
        System.out.println("📤 [RabbitMQ] Respuesta enviada de vuelta.");
    }
}