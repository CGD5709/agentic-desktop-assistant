package com.agentic.execution_service.tools;

import com.agentic.execution_service.models.ToolDefinition;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

/**
 * Inspects network ports and associated process owners on Windows using netstat.
 */
@Component
public class PortScannerTool implements AgentTool {

    public static final int MIN_PORT = 1;
    public static final int MAX_PORT = 65535;
    private static final long PROCESS_TIMEOUT_SECONDS = 15L;

    @Override
    public String getName() {
        return "escanear_puerto";
    }

    @Override
    public ToolDefinition getDefinition() {
        Map<String, Object> portProperty = Map.of(
                "type", "integer",
                "description", "El número del puerto de red a investigar (por ejemplo, 8080)."
        );

        Map<String, Object> parametersSchema = Map.of(
                "type", "object",
                "properties", Map.of("puerto", portProperty),
                "required", List.of("puerto")
        );

        return new ToolDefinition(
                getName(),
                "Busca en el sistema operativo qué proceso (PID) está ocupando un puerto de red específico.",
                parametersSchema
        );
    }

    @Override
    public String execute(Map<String, Object> arguments) throws Exception {
        if (arguments == null || !arguments.containsKey("puerto")) {
            throw new IllegalArgumentException("Falta el parámetro obligatorio 'puerto'.");
        }

        Object puertoObj = arguments.get("puerto");
        int puerto;
        if (puertoObj instanceof Number number) {
            puerto = number.intValue();
        } else if (puertoObj instanceof String puertoStr && !puertoStr.isBlank()) {
            try {
                puerto = Integer.parseInt(puertoStr.trim());
            } catch (NumberFormatException e) {
                throw new IllegalArgumentException("El puerto proporcionado no tiene un formato numérico válido: " + puertoObj);
            }
        } else {
            throw new IllegalArgumentException("El puerto proporcionado no tiene un formato válido: " + puertoObj);
        }

        if (puerto < MIN_PORT || puerto > MAX_PORT) {
            throw new IllegalArgumentException("El puerto debe encontrarse en el rango de " + MIN_PORT + " a " + MAX_PORT + ": " + puerto);
        }

        // TODO: Replace print with a standardized logging framework (e.g., SLF4J / Logback).
        System.out.println("[PortScannerTool] Scanning network status for port: " + puerto);

        ProcessBuilder pb = new ProcessBuilder("cmd.exe", "/c", "netstat -ano | findstr :" + puerto);
        pb.redirectErrorStream(true);
        Process process = pb.start();

        String output;
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
            output = reader.lines().collect(Collectors.joining("\n"));
        }

        boolean completed = process.waitFor(PROCESS_TIMEOUT_SECONDS, TimeUnit.SECONDS);
        if (!completed) {
            process.destroyForcibly();
            return "Operación cancelada: el escaneo de puertos superó el tiempo límite (" + PROCESS_TIMEOUT_SECONDS + "s).";
        }

        if (output.trim().isEmpty()) {
            return "No hay ningún proceso escuchando en el puerto " + puerto + ". El puerto está libre.";
        }

        return "Información de red para el puerto " + puerto + ":\n" + output + 
               "\n(Nota para la IA: El PID es el último número de la derecha en cada línea).";
    }
}