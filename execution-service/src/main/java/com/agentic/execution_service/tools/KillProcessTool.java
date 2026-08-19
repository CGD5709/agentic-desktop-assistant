package com.agentic.execution_service.tools;

import com.agentic.execution_service.models.ToolDefinition;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@Component
public class KillProcessTool implements AgentTool {

    // Lista negra de seguridad: procesos que NUNCA deben ser terminados
    private static final Set<String> PROTECTED_PROCESSES = Set.of(
            "docker.exe", "docker desktop.exe", "com.docker.backend.exe", "wsl.exe", "wslhost.exe",
            "erl.exe", "beam.smp.exe", "epmd.exe", "rabbitmq-server",
            "java.exe", "javaw.exe", "python.exe", "pythonw.exe",
            "system", "idle", "svchost.exe", "csrss.exe", "smss.exe", "services.exe", "lsass.exe", "wininit.exe"
    );

    @Override
    public String getName() {
        return "matar_proceso";
    }

    @Override
    public ToolDefinition getDefinition() {
        Map<String, Object> nameProperty = Map.of(
                "type", "string",
                "description", "El nombre del ejecutable del proceso que se desea cerrar (ejemplo: 'notepad.exe', 'chrome.exe', 'calc.exe'). RECOMENDADO."
        );

        Map<String, Object> pidProperty = Map.of(
                "type", "integer",
                "description", "El Process ID (PID) numérico específico del proceso, si se conoce con certeza."
        );

        Map<String, Object> parametersSchema = Map.of(
                "type", "object",
                "properties", Map.of(
                        "nombre_proceso", nameProperty,
                        "pid", pidProperty
                )
        );

        return new ToolDefinition(
                getName(),
                "Termina o cierra un proceso o aplicación en ejecución en el sistema operativo mediante su nombre de ejecutable (ej. 'notepad.exe') o su PID.",
                parametersSchema
        );
    }

    @Override
    public String execute(Map<String, Object> arguments) throws Exception {
        if (arguments == null || (!arguments.containsKey("nombre_proceso") && !arguments.containsKey("pid"))) {
            throw new IllegalArgumentException("Debes proporcionar al menos 'nombre_proceso' (ej: 'notepad.exe') o 'pid'.");
        }

        String processName = null;
        Integer pid = null;

        if (arguments.containsKey("nombre_proceso")) {
            processName = String.valueOf(arguments.get("nombre_proceso")).trim();
            if (!processName.toLowerCase().endsWith(".exe")) {
                processName += ".exe";
            }
        }

        if (arguments.containsKey("pid")) {
            Object pidObj = arguments.get("pid");
            if (pidObj instanceof Number) {
                pid = ((Number) pidObj).intValue();
            } else if (pidObj instanceof String && !((String) pidObj).isBlank()) {
                try {
                    pid = Integer.parseInt((String) pidObj);
                } catch (NumberFormatException ignored) {}
            }
        }

        // --- BARRERA DE SEGURIDAD ---
        if (processName != null && PROTECTED_PROCESSES.contains(processName.toLowerCase())) {
            return "Operación bloqueada por seguridad: '" + processName + "' es un proceso crítico de la infraestructura o del sistema operativo y no se puede cerrar.";
        }

        if (pid != null && (pid == 0 || pid == 4)) {
            return "Operación bloqueada por seguridad: El PID " + pid + " pertenece al Núcleo del Sistema y no se puede cerrar.";
        }

        ProcessBuilder pb;
        String targetDesc;

        if (processName != null) {
            targetDesc = "proceso '" + processName + "'";
            System.out.println("   💀 Matando proceso por nombre: " + processName);
            pb = new ProcessBuilder("taskkill", "/F", "/IM", processName);
        } else {
            targetDesc = "PID " + pid;
            System.out.println("   💀 Matando proceso por PID: " + pid);
            pb = new ProcessBuilder("taskkill", "/F", "/PID", String.valueOf(pid));
        }

        pb.redirectErrorStream(true);
        Process process = pb.start();

        BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
        String output = reader.lines().collect(Collectors.joining("\n"));
        int exitCode = process.waitFor();

        if (exitCode != 0) {
            return "No se pudo cerrar el " + targetDesc + ":\n" + output;
        }

        return "El " + targetDesc + " ha sido cerrado exitosamente.\nDetalles: " + output;
    }
}