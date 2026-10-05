import React, { useState, useEffect } from "react";
import { AppSettings } from "../types";
import {
  Keyboard,
  Mic,
  Save,
  RotateCcw,
  Check,
  Volume2,
  Play,
} from "lucide-react";
import { speechSynthesisService } from "../services/speechSynthesis";

interface SettingsViewProps {
  settings: AppSettings;
  onSaveSettings: (newSettings: AppSettings) => void;
  onClose: () => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({
  settings,
  onSaveSettings,
  onClose,
}) => {
  const [formData, setFormData] = useState<AppSettings>({ ...settings });
  const [isRecordingKey, setIsRecordingKey] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [availableVoices, setAvailableVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [isPlayingTestVoice, setIsPlayingTestVoice] = useState(false);

  useEffect(() => {
    const updateVoices = () => {
      const voices = speechSynthesisService.getVoices();
      setAvailableVoices(voices);
    };

    updateVoices();
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.onvoiceschanged = updateVoices;
    }
  }, []);

  useEffect(() => {
    if (!isRecordingKey) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      e.preventDefault();
      e.stopPropagation();

      const code = e.code;
      let displayName = code;

      if (code.startsWith("Numpad")) {
        displayName = `NUMPAD ${code.replace("Numpad", "")}`;
      } else if (code.startsWith("Key")) {
        displayName = code.replace("Key", "");
      } else if (code.startsWith("Digit")) {
        displayName = code.replace("Digit", "");
      }

      setFormData((prev: AppSettings) => ({
        ...prev,
        globalHotkey: code,
        hotkeyDisplayName: displayName,
      }));
      setIsRecordingKey(false);
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isRecordingKey]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSaveSettings(formData);
    setSaveSuccess(true);
    setTimeout(() => {
      setSaveSuccess(false);
      onClose();
    }, 800);
  };

  const handleResetDefaults = () => {
    const defaults: AppSettings = {
      ...formData,
      globalHotkey: "Numpad3",
      hotkeyDisplayName: "NUMPAD 3",
      autoSpeakResponse: false,
      pttMode: "hold",
      ttsVoiceURI: "",
      ttsRate: 1.05,
      ttsPitch: 1.0,
    };
    setFormData(defaults);
  };

  const handleTestVoice = () => {
    if (isPlayingTestVoice) {
      speechSynthesisService.cancelSpeech();
      setIsPlayingTestVoice(false);
      return;
    }

    setIsPlayingTestVoice(true);
    speechSynthesisService.speak(
      "Sistemas vocales calibrados y listos para interactuar. ¿En qué puedo asistirle hoy?",
      {
        voiceURI: formData.ttsVoiceURI,
        rate: formData.ttsRate,
        pitch: formData.ttsPitch,
        onStart: () => setIsPlayingTestVoice(true),
        onEnd: () => setIsPlayingTestVoice(false),
        onError: () => setIsPlayingTestVoice(false),
      },
    );
  };

  return (
    <div
      className="hud-panel"
      style={{
        flex: 1,
        height: "100%",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "16px 24px",
          borderBottom: "1px solid var(--border-color)",
          backgroundColor: "var(--bg-surface-elevated)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <SettingsIcon size={18} className="text-muted" />
          <h2 className="title-primary" style={{ margin: 0 }}>
            Configuración del Asistente
          </h2>
        </div>

        <button onClick={onClose} className="hud-btn">
          Volver
        </button>
      </div>

      <form
        onSubmit={handleSubmit}
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "32px",
          display: "flex",
          flexDirection: "column",
          gap: "24px",
          maxWidth: "700px",
          margin: "0 auto",
          width: "100%",
        }}
      >
        {/* SECTION 1: VOICE INPUT */}
        <div
          style={{
            padding: "20px",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-color)",
            backgroundColor: "var(--bg-surface-elevated)",
            display: "flex",
            flexDirection: "column",
            gap: "16px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Mic size={18} className="text-muted" />
            <h3 style={{ fontSize: "14px", margin: 0 }}>Entrada de Voz</h3>
          </div>

          <p style={{ fontSize: "13px", color: "var(--text-muted)", margin: 0 }}>
            Configura el atajo de teclado y el comportamiento del micrófono.
          </p>

          <div style={{ display: "flex", alignItems: "center", gap: "16px", marginTop: "8px" }}>
            <div
              style={{
                padding: "8px 16px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: isRecordingKey ? "var(--primary-glow)" : "var(--bg-input)",
                border: `1px solid ${isRecordingKey ? "var(--primary-accent)" : "var(--border-color)"}`,
                fontFamily: "var(--font-mono)",
                fontSize: "14px",
                fontWeight: "500",
                color: isRecordingKey ? "var(--primary-accent)" : "var(--text-primary)",
                minWidth: "160px",
                textAlign: "center",
              }}
            >
              {isRecordingKey ? "Pulsa una tecla..." : formData.hotkeyDisplayName}
            </div>

            <button
              type="button"
              onClick={() => setIsRecordingKey(true)}
              className="hud-btn"
            >
              {isRecordingKey ? "Cancelar" : "Cambiar Atajo"}
            </button>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginTop: "8px" }}>
            <label
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: "10px",
                padding: "12px",
                borderRadius: "var(--radius-sm)",
                border: `1px solid ${formData.pttMode === "hold" ? "var(--primary-accent)" : "var(--border-color)"}`,
                backgroundColor: formData.pttMode === "hold" ? "var(--primary-glow)" : "var(--bg-input)",
                cursor: "pointer",
              }}
            >
              <input
                type="radio"
                name="pttMode"
                checked={formData.pttMode === "hold"}
                onChange={() => setFormData({ ...formData, pttMode: "hold" })}
                style={{ marginTop: "2px" }}
              />
              <div>
                <div style={{ fontSize: "13px", fontWeight: 500, color: "var(--text-primary)" }}>
                  Mantener para hablar
                </div>
                <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
                  Habla mientras mantienes la tecla pulsada
                </div>
              </div>
            </label>

            <label
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: "10px",
                padding: "12px",
                borderRadius: "var(--radius-sm)",
                border: `1px solid ${formData.pttMode === "toggle" ? "var(--primary-accent)" : "var(--border-color)"}`,
                backgroundColor: formData.pttMode === "toggle" ? "var(--primary-glow)" : "var(--bg-input)",
                cursor: "pointer",
              }}
            >
              <input
                type="radio"
                name="pttMode"
                checked={formData.pttMode === "toggle"}
                onChange={() => setFormData({ ...formData, pttMode: "toggle" })}
                style={{ marginTop: "2px" }}
              />
              <div>
                <div style={{ fontSize: "13px", fontWeight: 500, color: "var(--text-primary)" }}>
                  Pulsar para alternar
                </div>
                <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
                  Pulsa una vez para iniciar y otra para detener
                </div>
              </div>
            </label>
          </div>
        </div>

        {/* SECTION 2: TTS */}
        <div
          style={{
            padding: "20px",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-color)",
            backgroundColor: "var(--bg-surface-elevated)",
            display: "flex",
            flexDirection: "column",
            gap: "16px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Volume2 size={18} className="text-muted" />
              <h3 style={{ fontSize: "14px", margin: 0 }}>Síntesis de Voz (TTS)</h3>
            </div>

            <button
              type="button"
              onClick={handleTestVoice}
              className="hud-btn"
            >
              <Play size={14} className={isPlayingTestVoice ? "animate-pulse-core" : ""} />
              <span>{isPlayingTestVoice ? "Detener" : "Probar Voz"}</span>
            </button>
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "12px",
              backgroundColor: "var(--bg-input)",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-color)",
            }}
          >
            <div>
              <div style={{ fontSize: "13px", fontWeight: 500 }}>Respuesta por voz automática</div>
              <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                El asistente leerá automáticamente sus respuestas.
              </div>
            </div>
            <label style={{ display: "flex", alignItems: "center", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={formData.autoSpeakResponse}
                onChange={(e) => setFormData({ ...formData, autoSpeakResponse: e.target.checked })}
                style={{ width: "16px", height: "16px" }}
              />
            </label>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "8px" }}>
            <label style={{ fontSize: "13px", color: "var(--text-secondary)", fontWeight: 500 }}>
              Voz del Sistema:
            </label>
            <select
              value={formData.ttsVoiceURI}
              onChange={(e) => setFormData({ ...formData, ttsVoiceURI: e.target.value })}
            >
              <option value="">Voz Predeterminada</option>
              {availableVoices.map((voice) => (
                <option key={voice.voiceURI} value={voice.voiceURI}>
                  {voice.name} ({voice.lang}) {voice.default ? "(Predeterminada)" : ""}
                </option>
              ))}
            </select>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginTop: "12px" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              <label style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                Velocidad: {formData.ttsRate.toFixed(2)}x
              </label>
              <input
                type="range"
                min="0.75"
                max="1.4"
                step="0.05"
                value={formData.ttsRate}
                onChange={(e) => setFormData({ ...formData, ttsRate: parseFloat(e.target.value) })}
              />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              <label style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                Tono (Pitch): {formData.ttsPitch.toFixed(2)}
              </label>
              <input
                type="range"
                min="0.8"
                max="1.2"
                step="0.05"
                value={formData.ttsPitch}
                onChange={(e) => setFormData({ ...formData, ttsPitch: parseFloat(e.target.value) })}
              />
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: "12px", marginTop: "16px" }}>
          <button type="button" onClick={handleResetDefaults} className="hud-btn">
            <RotateCcw size={14} />
            <span>Restaurar Defecto</span>
          </button>

          <button type="submit" className="hud-btn hud-btn-primary">
            {saveSuccess ? (
              <>
                <Check size={14} />
                <span>Guardado</span>
              </>
            ) : (
              <>
                <Save size={14} />
                <span>Guardar Ajustes</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

// Define an internal alias for the missing SettingsIcon since we replaced the import in lucide
const SettingsIcon = Keyboard;

export default SettingsView;
