package com.agentic.execution_service.tools;

import com.agentic.execution_service.models.ToolDefinition;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

/**
 * Manages Windows system audio levels and mute state via native CoreAudio COM interfaces through PowerShell.
 */
@Component
public class SystemAudioTool implements AgentTool {

    private static final Logger logger = LoggerFactory.getLogger(SystemAudioTool.class);
    private static final long TIMEOUT_SECONDS = 8L;

    @Override
    public String getName() {
        return "control_audio_sistema";
    }

    @Override
    public ToolDefinition getDefinition() {
        Map<String, Object> accionProperty = Map.of(
                "type", "string",
                "enum", List.of("get_volume", "set_volume", "mute", "unmute"),
                "description", "Acción a realizar: 'get_volume' (consultar), 'set_volume' (fijar nivel), 'mute' (silenciar), 'unmute' (reactivar sonido)."
        );

        Map<String, Object> nivelProperty = Map.of(
                "type", "integer",
                "minimum", 0,
                "maximum", 100,
                "description", "Nivel de volumen numérico entre 0 y 100 (requerido únicamente si la acción es 'set_volume')."
        );

        Map<String, Object> parametersSchema = Map.of(
                "type", "object",
                "properties", Map.of(
                        "accion", accionProperty,
                        "nivel", nivelProperty
                ),
                "required", List.of("accion")
        );

        return new ToolDefinition(
                getName(),
                "Controla el sistema de audio del ordenador: consulta o ajusta el volumen maestro (0-100%) y silencia/reactiva el sonido.",
                parametersSchema
        );
    }

    @Override
    public String execute(Map<String, Object> arguments) throws Exception {
        if (arguments == null || !arguments.containsKey("accion")) {
            throw new IllegalArgumentException("Falta el parámetro obligatorio 'accion'.");
        }

        String accion = String.valueOf(arguments.get("accion")).trim().toLowerCase();
        Integer nivel = null;

        if (arguments.containsKey("nivel")) {
            Object nivelObj = arguments.get("nivel");
            if (nivelObj instanceof Number num) {
                nivel = num.intValue();
            } else if (nivelObj instanceof String s && !s.isBlank()) {
                try {
                    nivel = Integer.parseInt(s.trim());
                } catch (NumberFormatException ignored) {}
            }
        }

        if ("set_volume".equals(accion)) {
            if (nivel == null || nivel < 0 || nivel > 100) {
                throw new IllegalArgumentException("Para 'set_volume' debes indicar un parámetro 'nivel' entero entre 0 y 100.");
            }
        }

        String psScript;
        if ("get_volume".equals(accion)) {
            psScript = buildPowerShellScript("GetVolume()");
        } else if ("set_volume".equals(accion)) {
            psScript = buildPowerShellScript("SetVolume(" + nivel + ")");
        } else if ("mute".equals(accion)) {
            psScript = buildPowerShellScript("SetMute($true)");
        } else if ("unmute".equals(accion)) {
            psScript = buildPowerShellScript("SetMute($false)");
        } else {
            throw new IllegalArgumentException("Acción de audio no reconocida: " + accion);
        }

        logger.info("Executing system audio command: action={}, level={}", accion, nivel);

        ProcessBuilder pb = new ProcessBuilder(
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy", "Bypass",
                "-Command", psScript
        );
        pb.redirectErrorStream(true);

        Process process = pb.start();
        String output;
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
            output = reader.lines().collect(Collectors.joining("\n")).trim();
        }

        boolean finished = process.waitFor(TIMEOUT_SECONDS, TimeUnit.SECONDS);
        if (!finished) {
            process.destroyForcibly();
            return "Error: La operación de audio superó el tiempo límite de espera (" + TIMEOUT_SECONDS + "s).";
        }

        if (process.exitValue() != 0) {
            logger.warn("Audio PowerShell command exited with code {}: {}", process.exitValue(), output);
            return "No se pudo modificar el audio del sistema: " + output;
        }

        return switch (accion) {
            case "set_volume" -> "El volumen del sistema se ha ajustado correctamente al " + nivel + "%.";
            case "get_volume" -> "Información de audio del sistema: " + output;
            case "mute" -> "El audio del sistema ha sido silenciado (Mute).";
            case "unmute" -> "El audio del sistema ha sido reactivado.";
            default -> "Operación completada: " + output;
        };
    }

    private String buildPowerShellScript(String methodCall) {
        return """
            $code = @'
            using System;
            using System.Runtime.InteropServices;

            [Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
            interface IAudioEndpointVolume {
                int f(); int g(); int h(); int i();
                int SetMasterVolumeLevelScalar(float fLevel, System.Guid pguidEventContext);
                int j();
                int GetMasterVolumeLevelScalar(out float pfLevel);
                int SetMute([MarshalAs(UnmanagedType.Bool)] bool bMute, System.Guid pguidEventContext);
                int GetMute(out bool pbMute);
            }
            [Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
            interface IMMDevice {
                int Activate(ref System.Guid id, int clsCtx, int activationParams, out IAudioEndpointVolume aev);
            }
            [Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
            interface IMMDeviceEnumerator {
                int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice endpoint);
            }
            [ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] class MMDeviceEnumeratorComObject { }

            public class AudioHelper {
                public static IAudioEndpointVolume GetVolumeObject() {
                    var enumerator = (IMMDeviceEnumerator)(new MMDeviceEnumeratorComObject());
                    IMMDevice dev = null;
                    enumerator.GetDefaultAudioEndpoint(0, 1, out dev);
                    var IID_IAudioEndpointVolume = typeof(IAudioEndpointVolume).GUID;
                    IAudioEndpointVolume epv = null;
                    dev.Activate(ref IID_IAudioEndpointVolume, 23, 0, out epv);
                    return epv;
                }
                public static int GetVolume() {
                    float vol = 0;
                    GetVolumeObject().GetMasterVolumeLevelScalar(out vol);
                    return (int)Math.Round(vol * 100);
                }
                public static void SetVolume(float level) {
                    float val = Math.Max(0f, Math.Min(100f, level)) / 100f;
                    GetVolumeObject().SetMasterVolumeLevelScalar(val, System.Guid.Empty);
                }
                public static bool GetMute() {
                    bool mute = false;
                    GetVolumeObject().GetMute(out mute);
                    return mute;
                }
                public static void SetMute(bool mute) {
                    GetVolumeObject().SetMute(mute, System.Guid.Empty);
                }
            }
            '@
            if (-not ([System.Management.Automation.PSTypeName]'AudioHelper').Type) {
                Add-Type -TypeDefinition $code -Language CSharp
            }
            """ + " [AudioHelper]::" + methodCall;
    }
}
