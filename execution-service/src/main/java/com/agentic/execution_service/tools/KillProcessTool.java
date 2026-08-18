package com.agentic.execution_service.tools;

import com.agentic.execution_service.models.ToolDefinition;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Component
public class KillProcessTool implements AgentTool {

    @Override
    public String getName() {
        return "matar_proceso";
    }

    @Override
    public ToolDefinition getDefinition() {
        Map<String, Object> pidProperty = Map.of(
                "type", "integer",
                "description", "El Process ID (PID) numérico del proceso que se desea forzar a cerrar."
        );

        Map<String, Object> parametersSchema = Map.of(
                "type", "object",
                "properties", Map.of("pid", pidProperty),
                "required", List.of("pid")
        );

        return new ToolDefinition(
                getName(),
                "Termina/mata de forma forzosa un proceso en ejecución en el sistema operativo usando su PID.",
                parametersSchema
        );
    }

   @Override
    public String execute(Map<String, Object> arguments) throws Exception {
        if (arguments == null || !arguments.containsKey("pid")) {
            throw new IllegalArgumentException("Falta el parámetro obligatorio 'pid'.");
        }

        // --- PARSEO DEFENSIVO ---
        Object pidObj = arguments.get("pid");
        int pid;
        if (pidObj instanceof Number) {
            pid = ((Number) pidObj).intValue();
        } else if (pidObj instanceof String) {
            pid = Integer.parseInt((String) pidObj);
        } else {
            throw new IllegalArgumentException("El PID proporcionado no tiene un formato numérico válido: " + pidObj);
        }
        // ------------------------

        System.out.println("   💀 Matando proceso con PID: " + pid);

        ProcessBuilder pb = new ProcessBuilder("taskkill", "/F", "/PID", String.valueOf(pid));
        pb.redirectErrorStream(true);
        Process process = pb.start();

        BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
        String output = reader.lines().collect(Collectors.joining("\n"));
        int exitCode = process.waitFor();

        if (exitCode != 0) {
            return "Error al intentar matar el proceso " + pid + ":\n" + output;
        }

        return "El proceso con PID " + pid + " ha sido terminado exitosamente.\nDetalles: " + output;
    }
}