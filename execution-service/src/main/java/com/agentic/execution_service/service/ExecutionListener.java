package com.agentic.execution_service.service;

import com.agentic.execution_service.config.RabbitMQConfig;
import com.agentic.execution_service.models.EventEnvelope;
import com.agentic.execution_service.models.EventMetadata;
import com.agentic.execution_service.models.EventType;
import com.agentic.execution_service.models.ToolExecutionRequestPayload;
import com.agentic.execution_service.models.ToolExecutionResponsePayload;
import com.agentic.execution_service.tools.AgentTool;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * AMQP consumer listening for tool execution requests and dispatching results back to RabbitMQ.
 */
@Service
public class ExecutionListener {

    private static final Logger logger = LoggerFactory.getLogger(ExecutionListener.class);
    private static final String MDC_CORRELATION_ID = "correlationId";

    public static final String ROUTING_KEY_RESPONSE_PREFIX = "tool.response.";
    public static final String SOURCE_SERVICE_NAME = "execution-service";
    public static final String ERROR_INVALID_REQUEST = "INVALID_REQUEST";
    public static final String ERROR_TOOL_NOT_FOUND = "TOOL_NOT_FOUND";
    public static final String ERROR_EXECUTION_FAILURE = "EXECUTION_ERROR";

    private final RabbitTemplate rabbitTemplate;
    private final Map<String, AgentTool> toolRegistry;

    public ExecutionListener(RabbitTemplate rabbitTemplate, List<AgentTool> tools) {
        this.rabbitTemplate = Objects.requireNonNull(rabbitTemplate, "RabbitTemplate must not be null");
        this.toolRegistry = tools.stream()
                .collect(Collectors.toUnmodifiableMap(AgentTool::getName, Function.identity()));
    }

    /**
     * Executes the requested tool and returns the result, preserving correlationId for caller Future resolution.
     */
    @RabbitListener(queues = RabbitMQConfig.QUEUE_NAME)
    public void receiveToolRequest(EventEnvelope<ToolExecutionRequestPayload> requestEnvelope) {
        logger.info("Received tool execution request from RabbitMQ");

        if (requestEnvelope == null || requestEnvelope.metadata() == null) {
            logger.warn("Dropping malformed message: envelope or metadata is null.");
            return;
        }

        String correlationId = requestEnvelope.metadata().correlationId();
        if (correlationId == null || correlationId.isBlank()) {
            logger.warn("Missing correlationId in incoming request. Upstream caller future resolution may fail.");
        } else {
            MDC.put(MDC_CORRELATION_ID, correlationId);
        }

        try {
            ToolExecutionRequestPayload requestPayload = requestEnvelope.payload();
            String toolName = requestPayload != null ? requestPayload.toolName() : null;

            logger.info("Processing execution for tool: {}", toolName);

            String output;
            String status = ToolExecutionResponsePayload.STATUS_SUCCESS;
            String errorCode = null;

            try {
                if (toolName == null || toolName.isBlank()) {
                    status = ToolExecutionResponsePayload.STATUS_ERROR;
                    output = "Petición inválida: 'toolName' no puede ser nulo o vacío.";
                    errorCode = ERROR_INVALID_REQUEST;
                    logger.warn("Invalid request received with null or blank toolName");
                } else {
                    AgentTool tool = toolRegistry.get(toolName);
                    if (tool != null) {
                        Map<String, Object> arguments = requestPayload.arguments() != null 
                                ? requestPayload.arguments() 
                                : Map.of();
                        output = tool.execute(arguments);
                    } else {
                        status = ToolExecutionResponsePayload.STATUS_ERROR;
                        output = "Herramienta desconocida para el execution-service: " + toolName;
                        errorCode = ERROR_TOOL_NOT_FOUND;
                        logger.warn("Requested tool not found in registry: {}", toolName);
                    }
                }
            } catch (Exception e) {
                status = ToolExecutionResponsePayload.STATUS_ERROR;
                output = "Fallo crítico al ejecutar el comando en el SO: " + e.getMessage();
                errorCode = ERROR_EXECUTION_FAILURE;
                logger.error("Tool execution threw an unhandled exception for tool '{}': {}", toolName, e.getMessage(), e);
            }

            EventMetadata responseMetadata = EventMetadata.now(
                    correlationId,
                    SOURCE_SERVICE_NAME,
                    EventType.EXECUTION_RESPONSE
            );

            ToolExecutionResponsePayload responsePayload = new ToolExecutionResponsePayload(
                    toolName,
                    status,
                    output,
                    errorCode
            );

            EventEnvelope<ToolExecutionResponsePayload> responseEnvelope = 
                    new EventEnvelope<>(responseMetadata, responsePayload);

            String routingKey = ROUTING_KEY_RESPONSE_PREFIX + (toolName != null ? toolName : "unknown");
            rabbitTemplate.convertAndSend(RabbitMQConfig.EXCHANGE_NAME, routingKey, responseEnvelope);

            logger.info("Response dispatched successfully for tool: {} (status: {})", toolName, status);
        } finally {
            MDC.remove(MDC_CORRELATION_ID);
        }
    }
}