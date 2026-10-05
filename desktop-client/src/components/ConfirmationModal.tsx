import React, { useEffect } from "react";
import { ConfirmationRequest } from "../types";
import {
  ShieldAlert,
  CheckCircle2,
  XCircle,
  Terminal,
  AlertTriangle,
} from "lucide-react";

interface ConfirmationModalProps {
  request: ConfirmationRequest;
  onConfirm: () => void;
  onCancel: () => void;
}

export const ConfirmationModal: React.FC<ConfirmationModalProps> = ({
  request,
  onConfirm,
  onCancel,
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Enter") {
        e.preventDefault();
        onConfirm();
      } else if (e.key === "Escape") {
        e.preventDefault();
        onCancel();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onConfirm, onCancel]);

  const isDestructive =
    request.toolName === "matar_proceso" || request.severity === "CRITICAL";
  const accentColor = isDestructive ? "var(--danger-color)" : "var(--warning-color)";

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0, 0, 0, 0.5)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        padding: "20px",
      }}
    >
      <div
        className="hud-panel"
        style={{
          width: "100%",
          maxWidth: "480px",
          backgroundColor: "var(--bg-surface-elevated)",
          border: `1px solid ${isDestructive ? "rgba(239, 68, 68, 0.4)" : "var(--border-color)"}`,
          boxShadow: isDestructive ? "0 4px 20px rgba(239, 68, 68, 0.15)" : "0 4px 20px rgba(0, 0, 0, 0.2)",
          padding: "24px",
          display: "flex",
          flexDirection: "column",
          gap: "20px",
        }}
      >
        {/* 1. Header */}
        <div style={{ display: "flex", alignItems: "flex-start", gap: "16px" }}>
          <div
            style={{
              width: "42px",
              height: "42px",
              borderRadius: "50%",
              backgroundColor: isDestructive ? "rgba(239, 68, 68, 0.1)" : "rgba(245, 158, 11, 0.1)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            {isDestructive ? (
              <ShieldAlert size={22} color="var(--danger-color)" />
            ) : (
              <AlertTriangle size={22} color="var(--warning-color)" />
            )}
          </div>

          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
              <span style={{ fontSize: "12px", fontWeight: 600, color: accentColor, textTransform: "uppercase" }}>
                Autorización Requerida
              </span>
              <span
                style={{
                  fontSize: "10px",
                  padding: "2px 6px",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: isDestructive ? "rgba(239, 68, 68, 0.1)" : "rgba(245, 158, 11, 0.1)",
                  color: accentColor,
                  fontWeight: 600,
                }}
              >
                {request.severity || "CRITICAL"}
              </span>
            </div>
            <h2 style={{ fontSize: "16px", fontWeight: 600, color: "var(--text-primary)", margin: 0, lineHeight: 1.4 }}>
              {request.title || "Confirmación de Acción"}
            </h2>
          </div>
        </div>

        {/* 2. Main Message */}
        <div
          style={{
            fontSize: "14px",
            lineHeight: 1.5,
            color: "var(--text-primary)",
            padding: "16px",
            backgroundColor: "var(--bg-surface)",
            borderLeft: `3px solid ${accentColor}`,
            borderRadius: "0 var(--radius-sm) var(--radius-sm) 0",
          }}
        >
          {request.message}
        </div>

        {/* 3. Details Box */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "12px",
            backgroundColor: "var(--bg-input)",
            border: "1px solid var(--border-color)",
            borderRadius: "var(--radius-sm)",
            padding: "16px",
            fontSize: "13px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--text-secondary)", fontWeight: 500, borderBottom: "1px solid var(--border-color)", paddingBottom: "8px" }}>
            <Terminal size={14} />
            <span>Detalles de Ejecución</span>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "100px 1fr", gap: "8px", alignItems: "baseline" }}>
            <span style={{ color: "var(--text-muted)" }}>Acción:</span>
            <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>
              {request.toolName}
            </span>

            {request.details &&
              Object.entries(request.details).map(([key, value]) => (
                <React.Fragment key={key}>
                  <span style={{ color: "var(--text-muted)", textTransform: "capitalize" }}>{key}:</span>
                  <span style={{ color: "var(--text-primary)", wordBreak: "break-word" }}>
                    {String(value)}
                  </span>
                </React.Fragment>
              ))}
          </div>
        </div>

        {/* 4. Action Buttons */}
        <div style={{ display: "flex", gap: "12px", marginTop: "4px" }}>
          <button
            onClick={onCancel}
            className="hud-btn"
            style={{
              flex: 1,
              padding: "10px",
              display: "flex",
              justifyContent: "center",
              gap: "8px",
            }}
          >
            <XCircle size={16} />
            <span>Cancelar (Esc)</span>
          </button>

          <button
            onClick={onConfirm}
            className={isDestructive ? "hud-btn hud-btn-danger" : "hud-btn hud-btn-primary"}
            style={{
              flex: 1,
              padding: "10px",
              display: "flex",
              justifyContent: "center",
              gap: "8px",
            }}
          >
            <CheckCircle2 size={16} />
            <span>Confirmar (Enter)</span>
          </button>
        </div>
      </div>
    </div>
  );
};
