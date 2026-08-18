package com.agentic.execution_service.tools;

import com.agentic.execution_service.models.ToolDefinition;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Component
public class ProcessAnalyzerTool implements AgentTool {

    @Override
    public String getName() {
        return "analizar_rendimiento_procesos";
    }

    @Override
    public ToolDefinition getDefinition() {
        // Definimos un parámetro opcional para que la IA decida cuántos procesos quiere ver
        Map<String, Object> limitProperty = Map.of(
                "type", "integer",
                "description", "Número máximo de procesos a listar (por defecto suele ser 10)."
        );

        Map<String, Object> parametersSchema = Map.of(
                "type", "object",
                "properties", Map.of("limite_procesos", limitProperty)
                // No lo ponemos en "required", así es opcional para la IA
        );

        return new ToolDefinition(
                getName(),
                "Obtiene una lista de los procesos del sistema Windows ordenados por consumo de memoria RAM. Útil para diagnosticar qué está ralentizando el PC.",
                parametersSchema
        );
    }

   @Override
    public String execute(Map<String, Object> arguments) throws Exception {
        System.out.println("   📊 Ejecutando diagnóstico de RAM...");

        int limite = 10;
        
        // --- PARSEO DEFENSIVO ---
        if (arguments != null && arguments.containsKey("limite_procesos")) {
            Object limiteObj = arguments.get("limite_procesos");
            if (limiteObj instanceof Number) {
                limite = ((Number) limiteObj).intValue();
            } else if (limiteObj instanceof String) {
                try {
                    limite = Integer.parseInt((String) limiteObj);
                } catch (NumberFormatException e) {
                    System.out.println("   ⚠️ Aviso: La IA envió un límite no numérico ('" + limiteObj + "'). Usando 10 por defecto.");
                }
            }
        }
        // -------------------------

        String psCommand = String.format(
                "Get-Process | Sort-Object WS -Descending | Select-Object -First %d Name, Id, @{n='Memoria(MB)';e={[math]::round($_.WS/1MB,2)}} | Format-Table -AutoSize", 
                limite
        );

        ProcessBuilder pb = new ProcessBuilder("powershell.exe", "-NoProfile", "-Command", psCommand);
        pb.redirectErrorStream(true);
        Process process = pb.start();

        BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
        String output = reader.lines().collect(Collectors.joining("\n"));
        
        int exitCode = process.waitFor();
        if (exitCode != 0) {
            throw new RuntimeException("El comando falló con código: " + exitCode + " Salida: " + output);
        }

        return "Resultado del diagnóstico de memoria:\n" + output;
    }
}