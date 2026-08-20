import React, { useState, useEffect } from 'react';
import { AppSettings } from '../types';
import { Keyboard, Mic, Server, Save, RotateCcw, Check } from 'lucide-react';

interface SettingsViewProps {
  settings: AppSettings;
  onSaveSettings: (newSettings: AppSettings) => void;
  onClose: () => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({
  settings,
  onSaveSettings,
  onClose
}) => {
  const [formData, setFormData] = useState<AppSettings>({ ...settings });
  const [isRecordingKey, setIsRecordingKey] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Escuchador para grabar nueva tecla de atajo
  useEffect(() => {
    if (!isRecordingKey) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      e.preventDefault();
      e.stopPropagation();

      const code = e.code; // ej: 'Numpad3', 'KeyV', 'Space'
      let displayName = code;

      if (code.startsWith('Numpad')) {
        displayName = `NUMPAD ${code.replace('Numpad', '')}`;
      } else if (code.startsWith('Key')) {
        displayName = code.replace('Key', '');
      } else if (code.startsWith('Digit')) {
        displayName = code.replace('Digit', '');
      }

      setFormData((prev: AppSettings) => ({
        ...prev,
        globalHotkey: code,
        hotkeyDisplayName: displayName
      }));
      setIsRecordingKey(false);
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
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
      wsUrl: 'ws://localhost:8000/ws',
      globalHotkey: 'Numpad3',
      hotkeyDisplayName: 'NUMPAD 3',
      modelName: 'qwen2.5:7b',
      temperature: 0.2,
      audioSensitivity: 80,
      autoSpeakResponse: false
    };
    setFormData(defaults);
  };

  return (
    <div className="hud-panel hud-corners" style={{
      flex: 1,
      height: '100%',
      margin: '0 16px 12px 16px',
      borderRadius: 'var(--radius-md)',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden'
    }}>
      {/* Header de Ajustes */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '16px 24px',
        borderBottom: '1px solid var(--cyan-border)',
        backgroundColor: 'rgba(4, 14, 28, 0.6)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Keyboard size={18} color="var(--cyan-neon)" />
          <h2 className="hud-title" style={{ fontSize: '15px', margin: 0 }}>
            CONFIGURACIÓN DEL SISTEMA // AJUSTES
          </h2>
        </div>

        <button
          onClick={onClose}
          className="hud-btn"
          style={{ padding: '6px 14px', fontSize: '11px' }}
        >
          VOLVER AL HUD
        </button>
      </div>

      {/* Formulario de Configuración */}
      <form onSubmit={handleSubmit} style={{
        flex: 1,
        overflowY: 'auto',
        padding: '28px 36px',
        display: 'flex',
        flexDirection: 'column',
        gap: '28px',
        maxWidth: '850px',
        margin: '0 auto',
        width: '100%'
      }}>
        {/* SECCIÓN 1: ATAJO DE TECLADO GLOBAL */}
        <div style={{
          padding: '18px 20px',
          borderRadius: 'var(--radius-sm)',
          backgroundColor: 'rgba(4, 16, 32, 0.5)',
          border: '1px solid var(--cyan-border)',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Keyboard size={16} color="var(--cyan-neon)" />
            <h3 style={{
              fontFamily: 'var(--font-hud)',
              fontSize: '13px',
              color: 'var(--cyan-neon)',
              margin: 0,
              letterSpacing: '1px'
            }}>
              1. ATAJO GLOBAL DE VOZ (MICROFONO)
            </h3>
          </div>

          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0 }}>
            Pulsa este atajo para activar el micrófono y hablar con Jarvis en cualquier momento.
          </p>

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginTop: '6px' }}>
            <div style={{
              padding: '10px 24px',
              borderRadius: '4px',
              backgroundColor: isRecordingKey ? 'rgba(255, 183, 0, 0.15)' : 'rgba(0, 242, 255, 0.12)',
              border: `1.5px solid ${isRecordingKey ? 'var(--amber-accent)' : 'var(--cyan-neon)'}`,
              boxShadow: isRecordingKey ? '0 0 14px var(--amber-accent)' : '0 0 10px var(--cyan-glow)',
              fontFamily: 'var(--font-mono)',
              fontSize: '16px',
              fontWeight: 'bold',
              color: isRecordingKey ? 'var(--amber-accent)' : '#fff',
              letterSpacing: '2px',
              minWidth: '160px',
              textAlign: 'center'
            }}>
              {isRecordingKey ? 'PULSA UNA TECLA...' : formData.hotkeyDisplayName}
            </div>

            <button
              type="button"
              onClick={() => setIsRecordingKey(true)}
              className="hud-btn"
              style={{
                borderColor: isRecordingKey ? 'var(--amber-accent)' : 'var(--cyan-border)',
                backgroundColor: isRecordingKey ? 'rgba(255, 183, 0, 0.2)' : 'rgba(0, 242, 255, 0.08)'
              }}
            >
              {isRecordingKey ? 'CANCELAR' : 'GRABAR NUEVO ATAJO'}
            </button>
          </div>
        </div>

        {/* SECCIÓN 2: WEBSOCKET & LLM */}
        <div style={{
          padding: '18px 20px',
          borderRadius: 'var(--radius-sm)',
          backgroundColor: 'rgba(4, 16, 32, 0.5)',
          border: '1px solid var(--cyan-border)',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Server size={16} color="var(--cyan-neon)" />
            <h3 style={{
              fontFamily: 'var(--font-hud)',
              fontSize: '13px',
              color: 'var(--cyan-neon)',
              margin: 0,
              letterSpacing: '1px'
            }}>
              2. CONEXIÓN AL MOTOR DE RAZONAMIENTO
            </h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
              DIRECCIÓN WEBSOCKET:
            </label>
            <input
              type="text"
              value={formData.wsUrl}
              onChange={e => setFormData({ ...formData, wsUrl: e.target.value })}
              style={{
                backgroundColor: 'rgba(0, 242, 255, 0.04)',
                border: '1px solid var(--cyan-border)',
                borderRadius: '4px',
                padding: '8px 12px',
                color: '#fff',
                fontFamily: 'var(--font-mono)',
                fontSize: '13px',
                outline: 'none'
              }}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                MODELO OLLAMA:
              </label>
              <input
                type="text"
                value={formData.modelName}
                onChange={e => setFormData({ ...formData, modelName: e.target.value })}
                style={{
                  backgroundColor: 'rgba(0, 242, 255, 0.04)',
                  border: '1px solid var(--cyan-border)',
                  borderRadius: '4px',
                  padding: '8px 12px',
                  color: '#fff',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '13px',
                  outline: 'none'
                }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                TEMPERATURA: {formData.temperature}
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={formData.temperature}
                onChange={e => setFormData({ ...formData, temperature: parseFloat(e.target.value) })}
                style={{ accentColor: 'var(--cyan-neon)', marginTop: '8px' }}
              />
            </div>
          </div>
        </div>

        {/* SECCIÓN 3: VOZ & AUDIO */}
        <div style={{
          padding: '18px 20px',
          borderRadius: 'var(--radius-sm)',
          backgroundColor: 'rgba(4, 16, 32, 0.5)',
          border: '1px solid var(--cyan-border)',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Mic size={16} color="var(--cyan-neon)" />
            <h3 style={{
              fontFamily: 'var(--font-hud)',
              fontSize: '13px',
              color: 'var(--cyan-neon)',
              margin: 0,
              letterSpacing: '1px'
            }}>
              3. PARÁMETROS DE AUDIO (STT / TTS)
            </h3>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                Sensibilidad de Reacción del Arc Reactor
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Ajusta cuánto pulsan los anillos holográficos con el volumen de tu voz.
              </div>
            </div>
            <input
              type="range"
              min="20"
              max="150"
              value={formData.audioSensitivity}
              onChange={e => setFormData({ ...formData, audioSensitivity: parseInt(e.target.value) })}
              style={{ accentColor: 'var(--teal-accent)', width: '160px' }}
            />
          </div>
        </div>

        {/* Botones de Acción Footer */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '14px', marginTop: '10px' }}>
          <button
            type="button"
            onClick={handleResetDefaults}
            className="hud-btn"
            style={{ padding: '10px 18px', fontSize: '11px' }}
          >
            <RotateCcw size={14} />
            <span>RESTAURAR DEFECTO</span>
          </button>

          <button
            type="submit"
            className="hud-btn"
            style={{
              padding: '10px 24px',
              fontSize: '12px',
              backgroundColor: saveSuccess ? 'rgba(0, 255, 194, 0.3)' : 'rgba(0, 242, 255, 0.25)',
              borderColor: saveSuccess ? 'var(--teal-accent)' : 'var(--cyan-neon)',
              boxShadow: saveSuccess ? '0 0 16px var(--teal-glow)' : '0 0 14px var(--cyan-glow)'
            }}
          >
            {saveSuccess ? (
              <>
                <Check size={15} color="var(--teal-accent)" />
                <span style={{ color: 'var(--teal-accent)' }}>GUARDADO // OK</span>
              </>
            ) : (
              <>
                <Save size={15} />
                <span>GUARDAR AJUSTES</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
