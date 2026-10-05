import React from "react";
import { VoiceState } from "../types";
import { Activity, Mic, Volume2 } from "lucide-react";

interface ArcReactorHUDProps {
  voiceState: VoiceState;
  audioLevel: number;
  toolsCount: number;
}

export const ArcReactorHUD: React.FC<ArcReactorHUDProps> = ({
  voiceState,
  audioLevel,
  toolsCount,
}) => {
  const isListening = voiceState === "LISTENING";
  const isThinking = voiceState === "THINKING";
  const isSpeaking = voiceState === "SPEAKING";

  const statusColor = isListening
    ? "var(--success-color)"
    : isThinking
      ? "var(--warning-color)"
      : isSpeaking
        ? "var(--primary-accent)"
        : "var(--text-muted)";

  const statusText = isListening
    ? "Escuchando"
    : isThinking
      ? "Procesando"
      : isSpeaking
        ? "Hablando"
        : "Asistente Preparado";

  // Subtle visualizer scale based on audio
  const visualizerScale = isListening ? 1 + audioLevel * 0.3 : isSpeaking ? 1.1 : 1;

  return (
    <div
      className="hud-panel"
      style={{
        flex: 1,
        height: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "32px",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Top Left Status */}
      <div style={{ position: "absolute", top: "24px", left: "24px", display: "flex", flexDirection: "column", gap: "4px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px", fontWeight: 500 }}>
          <Activity size={14} color="var(--success-color)" />
          <span style={{ color: "var(--text-primary)" }}>Sistema en línea</span>
        </div>
        <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
          {toolsCount} herramientas disponibles
        </div>
      </div>

      {/* Top Right Status */}
      <div style={{ position: "absolute", top: "24px", right: "24px", textAlign: "right", display: "flex", flexDirection: "column", gap: "4px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: "8px", fontSize: "12px", fontWeight: 500 }}>
          {isSpeaking ? (
            <Volume2 size={14} color="var(--primary-accent)" />
          ) : (
            <Mic size={14} color={isListening ? "var(--success-color)" : "var(--text-muted)"} />
          )}
          <span style={{ color: statusColor }}>{statusText}</span>
        </div>
        <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
          Modo Local
        </div>
      </div>

      {/* Central Visualizer */}
      <div
        style={{
          width: "180px",
          height: "180px",
          borderRadius: "50%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "var(--bg-surface-elevated)",
          border: `2px solid ${isListening ? "var(--success-color)" : isSpeaking ? "var(--primary-accent)" : "var(--border-color)"}`,
          boxShadow: (isListening || isSpeaking || isThinking) ? `0 0 40px ${statusColor}40` : "none",
          transform: `scale(${visualizerScale})`,
          transition: "transform 0.1s ease-out, box-shadow 0.3s ease, border-color 0.3s ease",
          position: "relative",
        }}
        className={isThinking ? "animate-pulse-core" : ""}
      >
        <div
          style={{
            width: "60px",
            height: "60px",
            borderRadius: "50%",
            backgroundColor: statusColor,
            opacity: 0.15,
            position: "absolute",
            transform: `scale(${isListening ? 1 + audioLevel * 1.5 : 1})`,
            transition: "transform 0.1s ease-out",
          }}
        />
        {isListening ? (
          <Mic size={48} color={statusColor} />
        ) : isSpeaking ? (
          <Volume2 size={48} color={statusColor} />
        ) : isThinking ? (
          <Activity size={48} color={statusColor} />
        ) : (
          <Mic size={48} color="var(--text-muted)" />
        )}
      </div>

      <div style={{ marginTop: "40px", textAlign: "center", display: "flex", flexDirection: "column", gap: "8px" }}>
        <h2 style={{ fontSize: "20px", fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>
          {statusText}
        </h2>
        <p style={{ fontSize: "14px", color: "var(--text-muted)", margin: 0, maxWidth: "300px" }}>
          {isListening
            ? "Hable ahora. El sistema está capturando su voz."
            : isThinking
              ? "Procesando su consulta y ejecutando herramientas."
              : isSpeaking
                ? "El asistente está respondiendo."
                : "Pulse el atajo de teclado configurado para hablar."}
        </p>
      </div>
    </div>
  );
};

export default ArcReactorHUD;
