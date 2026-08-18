package com.agentic.execution_service.tools;

import com.agentic.execution_service.models.ToolDefinition;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

// ¡Clave! @Component le dice a Spring que registre esta herramienta automáticamente
@Component
public class OpenWebTool implements AgentTool {

    @Override
    public String getName() {
        return "abrir_sitio_web";
    }

    @Override
    public ToolDefinition getDefinition() {
        Map<String, Object> websiteProperties = Map.of(
                "url", Map.of(
                        "type", "string",
                        "description", "La URL completa de la página web a visitar, incluyendo https://"
                )
        );

        Map<String, Object> parametersSchema = Map.of(
                "type", "object",
                "properties", websiteProperties,
                "required", List.of("url")
        );

        return new ToolDefinition(
                getName(),
                "Abre el navegador web por defecto del ordenador en la URL especificada.",
                parametersSchema
        );
    }

    @Override
    public String execute(Map<String, Object> arguments) throws Exception {
        String url = (String) arguments.get("url");
        System.out.println("   🌐 Abriendo navegador en: " + url);
        
        ProcessBuilder pb = new ProcessBuilder("cmd.exe", "/c", "start", url);
        pb.start();
        
        return "Se ha abierto el navegador correctamente en la URL: " + url;
    }
}
