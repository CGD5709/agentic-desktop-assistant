package com.agentic.execution_service.models;

import com.fasterxml.jackson.annotation.JsonInclude;

/**
 * Outbound response payload detailing the outcome of a tool execution.
 *
 * Dispatched over RabbitMQ and returned to the reasoning engine (Python) 
 * to resolve the awaiting asynchronous execution Future.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record ToolExecutionResponsePayload(
    String toolName,
    String status,
    String output,
    String errorCode
) {

    public static final String STATUS_SUCCESS = "SUCCESS";
    public static final String STATUS_ERROR = "ERROR";

    public static ToolExecutionResponsePayload success(String toolName, String output) {
        return new ToolExecutionResponsePayload(toolName, STATUS_SUCCESS, output, null);
    }

    public static ToolExecutionResponsePayload error(String toolName, String output, String errorCode) {
        return new ToolExecutionResponsePayload(toolName, STATUS_ERROR, output, errorCode);
    }
}
