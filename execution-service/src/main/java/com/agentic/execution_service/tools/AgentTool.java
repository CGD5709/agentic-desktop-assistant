package com.agentic.execution_service.tools;

import com.agentic.execution_service.models.ToolDefinition;
import java.util.Map;

public interface AgentTool {
    // Devuelve el nombre de la herramienta (el identificador que usará Llama)
    String getName();
    
    // Devuelve el esquema JSON para el System Discovery
    ToolDefinition getDefinition();
    
    // Ejecuta la acción real en el ordenador
    String execute(Map<String, Object> arguments) throws Exception;
}