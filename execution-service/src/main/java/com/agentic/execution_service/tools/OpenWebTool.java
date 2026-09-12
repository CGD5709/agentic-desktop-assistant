package com.agentic.execution_service.tools;

import com.agentic.execution_service.models.ToolDefinition;
import org.springframework.stereotype.Component;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * Opens URLs in the default desktop browser with URI validation and shell injection defense.
 */
@Component
public class OpenWebTool implements AgentTool {

    private static final Set<String> ALLOWED_SCHEMES = Set.of("http", "https");
    private static final Pattern DISALLOWED_SHELL_CHARS = Pattern.compile("[&|<>;\"^%\r\n]");

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
        if (arguments == null || !arguments.containsKey("url")) {
            throw new IllegalArgumentException("Falta el parámetro obligatorio 'url'.");
        }

        Object urlObj = arguments.get("url");
        if (urlObj == null) {
            throw new IllegalArgumentException("El parámetro 'url' no puede ser nulo.");
        }

        String rawUrl = String.valueOf(urlObj).trim();
        if (rawUrl.isBlank()) {
            throw new IllegalArgumentException("El parámetro 'url' no puede estar vacío.");
        }

        if (DISALLOWED_SHELL_CHARS.matcher(rawUrl).find()) {
            throw new IllegalArgumentException("La URL contiene caracteres no permitidos o potencialmente inseguros.");
        }

        URI parsedUri;
        try {
            parsedUri = new URI(rawUrl);
        } catch (URISyntaxException e) {
            throw new IllegalArgumentException("La URL proporcionada no tiene una sintaxis válida: " + e.getMessage(), e);
        }

        String scheme = parsedUri.getScheme();
        if (scheme == null || !ALLOWED_SCHEMES.contains(scheme.toLowerCase())) {
            throw new IllegalArgumentException("Protocolo no permitido o URL inválida. Debe comenzar por http:// o https://");
        }

        // TODO: Replace print with a standardized logging framework (e.g., SLF4J / Logback).
        System.out.println("[OpenWebTool] Launching default browser at URL: " + rawUrl);

        ProcessBuilder pb = new ProcessBuilder("cmd.exe", "/c", "start", "\"\"", rawUrl);
        pb.start();

        return "Se ha abierto el navegador correctamente en la URL: " + rawUrl;
    }
}
