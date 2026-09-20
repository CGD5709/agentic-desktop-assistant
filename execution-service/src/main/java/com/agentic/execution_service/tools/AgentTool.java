package com.agentic.execution_service.tools;

import com.agentic.execution_service.models.ToolDefinition;
import java.util.Map;

/**
 * Common interface for operating system automation tools.
 */
public interface AgentTool {

    String getName();

    ToolDefinition getDefinition();

    String execute(Map<String, Object> arguments) throws Exception;

    /**
     * Indicates whether this tool performs potentially destructive or sensitive operations
     * requiring explicit user authorization (Human-in-the-Loop) prior to execution.
     */
    default boolean isCritical() {
        return false;
    }
}