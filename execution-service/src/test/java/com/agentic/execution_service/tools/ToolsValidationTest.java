package com.agentic.execution_service.tools;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ToolsValidationTest {

    private final KillProcessTool killProcessTool = new KillProcessTool();
    private final OpenWebTool openWebTool = new OpenWebTool();
    private final PortScannerTool portScannerTool = new PortScannerTool();
    private final ProcessAnalyzerTool processAnalyzerTool = new ProcessAnalyzerTool();

    @Test
    @DisplayName("KillProcessTool should block termination of protected processes")
    void killProcessToolShouldBlockProtectedProcesses() throws Exception {
        String result = killProcessTool.execute(Map.of("nombre_proceso", "docker.exe"));
        assertThat(result).contains("Operación bloqueada por seguridad");

        String resultJvm = killProcessTool.execute(Map.of("nombre_proceso", "java"));
        assertThat(resultJvm).contains("Operación bloqueada por seguridad");
    }

    @Test
    @DisplayName("KillProcessTool should block termination of System Kernel PIDs")
    void killProcessToolShouldBlockKernelPids() throws Exception {
        String resultIdle = killProcessTool.execute(Map.of("pid", 0));
        assertThat(resultIdle).contains("Operación bloqueada por seguridad");

        String resultKernel = killProcessTool.execute(Map.of("pid", 4));
        assertThat(resultKernel).contains("Operación bloqueada por seguridad");
    }

    @Test
    @DisplayName("KillProcessTool should reject unsafe process names with shell characters")
    void killProcessToolShouldRejectUnsafeNames() {
        assertThatThrownBy(() -> killProcessTool.execute(Map.of("nombre_proceso", "notepad.exe & whoami")))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("caracteres no permitidos");
    }

    @Test
    @DisplayName("OpenWebTool should reject non-HTTP/HTTPS URI schemes")
    void openWebToolShouldRejectNonHttpSchemes() {
        assertThatThrownBy(() -> openWebTool.execute(Map.of("url", "ftp://malicious.com/file")))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Protocolo no permitido");

        assertThatThrownBy(() -> openWebTool.execute(Map.of("url", "file:///C:/Windows/System32/cmd.exe")))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Protocolo no permitido");
    }

    @Test
    @DisplayName("OpenWebTool should reject shell injection characters")
    void openWebToolShouldRejectShellInjection() {
        assertThatThrownBy(() -> openWebTool.execute(Map.of("url", "https://google.com & calc.exe")))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("potencialmente inseguros");
    }

    @Test
    @DisplayName("PortScannerTool should reject invalid port numbers")
    void portScannerToolShouldRejectInvalidPorts() {
        assertThatThrownBy(() -> portScannerTool.execute(Map.of("puerto", 0)))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("rango de 1 a 65535");

        assertThatThrownBy(() -> portScannerTool.execute(Map.of("puerto", 70000)))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("rango de 1 a 65535");

        assertThatThrownBy(() -> portScannerTool.execute(Map.of("puerto", "not-a-port")))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("formato numérico válido");
    }

    @Test
    @DisplayName("ProcessAnalyzerTool should declare valid tool schema")
    void processAnalyzerToolShouldDeclareValidSchema() {
        var definition = processAnalyzerTool.getDefinition();
        assertThat(definition.name()).isEqualTo("analizar_rendimiento_procesos");
        assertThat(definition.parameters()).containsKey("properties");
    }
}
