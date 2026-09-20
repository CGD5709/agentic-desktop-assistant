package com.agentic.execution_service.tools;

import com.agentic.execution_service.models.ToolDefinition;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * Terminates running Windows processes by name or PID, enforcing critical infrastructure protection.
 */
@Component
public class KillProcessTool implements AgentTool {

    private static final Logger logger = LoggerFactory.getLogger(KillProcessTool.class);

    public static final int SYSTEM_IDLE_PID = 0;
    public static final int SYSTEM_KERNEL_PID = 4;
    private static final long PROCESS_TIMEOUT_SECONDS = 10L;
    private static final Pattern SAFE_PROCESS_NAME_PATTERN = Pattern.compile("^[a-zA-Z0-9_.-]+$");

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
    public boolean isCritical() {
        return true;
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
                parametersSchema,
                true,
                "¿Autoriza forzar el cierre del proceso '{nombre_proceso}' en el sistema operativo?"
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

            if (!SAFE_PROCESS_NAME_PATTERN.matcher(processName).matches()) {
                throw new IllegalArgumentException("El nombre del proceso contiene caracteres no permitidos: " + processName);
            }
        }

        if (arguments.containsKey("pid")) {
            Object pidObj = arguments.get("pid");
            if (pidObj instanceof Number number) {
                pid = number.intValue();
            } else if (pidObj instanceof String pidStr && !pidStr.isBlank()) {
                try {
                    pid = Integer.parseInt(pidStr.trim());
                } catch (NumberFormatException ignored) {}
            }
        }

        if (processName != null && PROTECTED_PROCESSES.contains(processName.toLowerCase())) {
            logger.warn("Blocked attempt to terminate protected system process: {}", processName);
            return "Operación bloqueada por seguridad: '" + processName + "' es un proceso crítico de la infraestructura o del sistema operativo y no se puede cerrar.";
        }

        if (pid != null && (pid == SYSTEM_IDLE_PID || pid == SYSTEM_KERNEL_PID)) {
            logger.warn("Blocked attempt to terminate kernel system PID: {}", pid);
            return "Operación bloqueada por seguridad: El PID " + pid + " pertenece al Núcleo del Sistema y no se puede cerrar.";
        }

        ProcessBuilder pb;
        String targetDesc;

        if (processName != null) {
            targetDesc = "proceso '" + processName + "'";
            logger.info("Terminating process by name: {}", processName);
            pb = new ProcessBuilder("taskkill", "/F", "/IM", processName);
        } else if (pid != null) {
            targetDesc = "PID " + pid;
            logger.info("Terminating process by PID: {}", pid);
            pb = new ProcessBuilder("taskkill", "/F", "/PID", String.valueOf(pid));
        } else {
            throw new IllegalArgumentException("No se ha podido determinar un identificador de proceso válido (nombre o PID).");
        }

        pb.redirectErrorStream(true);
        Process process = pb.start();

        String output;
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
            output = reader.lines().collect(Collectors.joining("\n"));
        }

        boolean completed = process.waitFor(PROCESS_TIMEOUT_SECONDS, TimeUnit.SECONDS);
        if (!completed) {
            process.destroyForcibly();
            return "Operación cancelada: el comando taskkill superó el tiempo límite de espera (" + PROCESS_TIMEOUT_SECONDS + "s).";
        }

        int exitCode = process.exitValue();
        if (exitCode != 0) {
            return "No se pudo cerrar el " + targetDesc + ":\n" + output;
        }

        return "El " + targetDesc + " ha sido cerrado exitosamente.\nDetalles: " + output;
    }
}