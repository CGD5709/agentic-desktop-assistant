package com.agentic.execution_service.tools;

import com.agentic.execution_service.models.ToolDefinition;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Component
public class PortScannerTool implements AgentTool {

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

        // --- PARSEO DEFENSIVO ---
        Object puertoObj = arguments.get("puerto");
        int puerto;
        if (puertoObj instanceof Number) {
            puerto = ((Number) puertoObj).intValue();
        } else if (puertoObj instanceof String) {
            puerto = Integer.parseInt((String) puertoObj);
        } else {
            throw new IllegalArgumentException("El puerto proporcionado no tiene un formato válido: " + puertoObj);
        }
        // ------------------------

        System.out.println("   🔍 Escaneando puerto: " + puerto);

        ProcessBuilder pb = new ProcessBuilder("cmd.exe", "/c", "netstat -ano | findstr :" + puerto);
        pb.redirectErrorStream(true);
        Process process = pb.start();

        BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
        String output = reader.lines().collect(Collectors.joining("\n"));
        process.waitFor();

        if (output.trim().isEmpty()) {
            return "No hay ningún proceso escuchando en el puerto " + puerto + ". El puerto está libre.";
        }

        return "Información de red para el puerto " + puerto + ":\n" + output + 
               "\n(Nota para la IA: El PID es el último número de la derecha en cada línea).";
    }
}