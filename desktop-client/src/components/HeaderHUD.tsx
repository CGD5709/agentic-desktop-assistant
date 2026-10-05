import React, { useState, useEffect } from "react";
import { TabType, VoiceState } from "../types";
import {
  Mic,
  Settings as SettingsIcon,
  LayoutDashboard,
  Cpu,
} from "lucide-react";

interface HeaderHUDProps {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
  connectionStatus: "CONNECTED" | "DISCONNECTED" | "CONNECTING";
  voiceState: VoiceState;
  hotkeyDisplayName: string;
  toolsCount: number;
  onToggleVoice: () => void;
}

export const HeaderHUD: React.FC<HeaderHUDProps> = ({
  activeTab,
  setActiveTab,
  connectionStatus,
  voiceState,
  hotkeyDisplayName,
  toolsCount,
  onToggleVoice,
}) => {
  const [timeStr, setTimeStr] = useState<string>("");

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(
        now.toLocaleTimeString("es-ES", {
          hour: "2-digit",
          minute: "2-digit",
        }),
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const isConnected = connectionStatus === "CONNECTED";
  const isListening = voiceState === "LISTENING";

  return (
    <header
      className="hud-panel"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "12px 24px",
        margin: "16px 16px 12px 16px",
        zIndex: 10,
        flexShrink: 0,
      }}
    >
      {/* 1. Left Branding */}
      <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
        <div
          style={{
            width: "36px",
            height: "36px",
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--primary-accent)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#fff",
            fontWeight: 700,
            fontSize: "18px",
          }}
        >
          A
        </div>

        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <h1 className="title-primary" style={{ margin: 0 }}>
              Agentic Assistant
            </h1>
            <span
              style={{
                fontSize: "11px",
                padding: "2px 6px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--bg-surface-elevated)",
                border: "1px solid var(--border-color)",
                color: "var(--text-muted)",
              }}
            >
              Local
            </span>
          </div>
          <p style={{ fontSize: "12px", color: "var(--text-muted)", margin: 0 }}>
            Workspace Inteligente
          </p>
        </div>
      </div>

      {/* 2. Center: Navigation Tabs */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <button
          className={`hud-btn ${activeTab === "home" ? "active" : ""}`}
          onClick={() => setActiveTab("home")}
          style={{ padding: "8px 16px" }}
        >
          <LayoutDashboard size={16} />
          <span>Dashboard</span>
        </button>

        <button
          className={`hud-btn ${activeTab === "settings" ? "active" : ""}`}
          onClick={() => setActiveTab("settings")}
          style={{ padding: "8px 16px" }}
        >
          <SettingsIcon size={16} />
          <span>Ajustes</span>
        </button>
      </div>

      {/* 3. Right Telemetry & Status Badges */}
      <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
        {/* Tools count indicator */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            fontSize: "13px",
            color: "var(--text-muted)",
          }}
        >
          <Cpu size={15} />
          <span>{toolsCount} herramientas</span>
        </div>

        {/* Mic Toggle Button */}
        <button
          onClick={onToggleVoice}
          className={`hud-btn ${isListening ? "hud-btn-primary" : ""}`}
          style={{
            padding: "8px 16px",
          }}
          title={`Micrófono [${hotkeyDisplayName}]`}
        >
          <Mic size={15} />
          <span>{isListening ? "Escuchando" : "Micro"}</span>
        </button>

        {/* Connection status pill */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "6px 12px",
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--bg-surface-elevated)",
            border: "1px solid var(--border-color)",
            fontSize: "12px",
            fontWeight: 500,
          }}
        >
          <div
            style={{
              width: "8px",
              height: "8px",
              borderRadius: "50%",
              backgroundColor: isConnected
                ? "var(--success-color)"
                : "var(--danger-color)",
            }}
          />
          <span style={{ color: "var(--text-primary)" }}>
            {connectionStatus === "CONNECTED" ? "Conectado" : "Desconectado"}
          </span>
        </div>

        {/* Digital Clock */}
        <div
          style={{
            fontSize: "14px",
            color: "var(--text-primary)",
            fontWeight: 500,
            fontVariantNumeric: "tabular-nums",
          }}
        >
          {timeStr}
        </div>
      </div>
    </header>
  );
};
