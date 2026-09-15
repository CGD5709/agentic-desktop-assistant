package com.agentic.execution_service.tools;

import com.agentic.execution_service.models.ToolDefinition;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

/**
 * Analyzes active Windows processes ordered by memory consumption via PowerShell.
 */
@Component
public class ProcessAnalyzerTool implements AgentTool {

    private static final Logger logger = LoggerFactory.getLogger(ProcessAnalyzerTool.class);

    public static final int DEFAULT_PROCESS_LIMIT = 10;
    public static final int MIN_PROCESS_LIMIT = 1;
    public static final int MAX_PROCESS_LIMIT = 100;
    private static final long PROCESS_TIMEOUT_SECONDS = 15L;

    @Override
    public String getName() {
        return "analizar_rendimiento_procesos";
    }

    @Override
    public ToolDefinition getDefinition() {
        Map<String, Object> limitProperty = Map.of(
                "type", "integer",
                "description", "Número máximo de procesos a listar (por defecto suele ser 10)."
        );

        Map<String, Object> parametersSchema = Map.of(
                "type", "object",
                "properties", Map.of("limite_procesos", limitProperty)
        );

        return new ToolDefinition(
                getName(),
                "Obtiene una lista de los procesos del sistema Windows ordenados por consumo de memoria RAM. Útil para diagnosticar qué está ralentizando el PC.",
                parametersSchema
        );
    }

    @Override
    public String execute(Map<String, Object> arguments) throws Exception {
        logger.info("Executing memory diagnostic query...");

        int limit = DEFAULT_PROCESS_LIMIT;

        if (arguments != null && arguments.containsKey("limite_procesos")) {
            Object limitObj = arguments.get("limite_procesos");
            if (limitObj instanceof Number number) {
                limit = number.intValue();
            } else if (limitObj instanceof String limitStr && !limitStr.isBlank()) {
                try {
                    limit = Integer.parseInt(limitStr.trim());
                } catch (NumberFormatException e) {
                    logger.warn("Received non-numeric process limit ('{}'). Falling back to default: {}", limitObj, DEFAULT_PROCESS_LIMIT);
                }
            }
        }

        limit = Math.max(MIN_PROCESS_LIMIT, Math.min(limit, MAX_PROCESS_LIMIT));

        String psCommand = String.format(
                "Get-Process | Sort-Object WS -Descending | Select-Object -First %d Name, Id, @{n='Memoria(MB)';e={[math]::round($_.WS/1MB,2)}} | Format-Table -AutoSize", 
                limit
        );

        ProcessBuilder pb = new ProcessBuilder("powershell.exe", "-NoProfile", "-Command", psCommand);
        pb.redirectErrorStream(true);
        Process process = pb.start();

        String output;
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
            output = reader.lines().collect(Collectors.joining("\n"));
        }

        boolean completed = process.waitFor(PROCESS_TIMEOUT_SECONDS, TimeUnit.SECONDS);
        if (!completed) {
            process.destroyForcibly();
            return "Operación cancelada: el análisis de rendimiento superó el tiempo límite (" + PROCESS_TIMEOUT_SECONDS + "s).";
        }

        int exitCode = process.exitValue();
        if (exitCode != 0) {
            throw new RuntimeException("El comando falló con código: " + exitCode + " Salida: " + output);
        }

        return "Resultado del diagnóstico de memoria:\n" + output;
    }
}