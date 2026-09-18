import React, { useState, useEffect } from 'react';
import { AppSettings, PttMode } from '../types';
import { Keyboard, Mic, Server, Save, RotateCcw, Check, Volume2, Play, Sparkles } from 'lucide-react';
import { speechSynthesisService } from '../services/speechSynthesis';

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
  const [availableVoices, setAvailableVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [isPlayingTestVoice, setIsPlayingTestVoice] = useState(false);

  // Cargar lista de voces disponibles en el sistema operativo
  useEffect(() => {
    const updateVoices = () => {
      const voices = speechSynthesisService.getVoices();
      setAvailableVoices(voices);
    };

    updateVoices();
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.onvoiceschanged = updateVoices;
    }
  }, []);

  // Escuchador para grabar nueva tecla de atajo
  useEffect(() => {
    if (!isRecordingKey) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      e.preventDefault();
      e.stopPropagation();

      const code = e.code;
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
      autoSpeakResponse: false,
      pttMode: 'hold',
      ttsVoiceURI: '',
      ttsRate: 1.05,
      ttsPitch: 1.0,
      soundEffects: true
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
    speechSynthesisService.speak('Sistemas vocales calibrados y listos para interactuar. ¿En qué puedo asistirle hoy?', {
      voiceURI: formData.ttsVoiceURI,
      rate: formData.ttsRate,
      pitch: formData.ttsPitch,
      onStart: () => setIsPlayingTestVoice(true),
      onEnd: () => setIsPlayingTestVoice(false),
      onError: () => setIsPlayingTestVoice(false)
    });
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
        padding: '24px 36px',
        display: 'flex',
        flexDirection: 'column',
        gap: '24px',
        maxWidth: '850px',
        margin: '0 auto',
        width: '100%'
      }}>
        {/* SECCIÓN 1: CONTROL POR VOZ Y PUSH-TO-TALK */}
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
              1. ENTRADA DE VOZ (PUSH-TO-TALK // STT)
            </h3>
          </div>

          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0 }}>
            Configura el atajo de teclado y el comportamiento del micrófono para dictar órdenes a Jarvis.
          </p>

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginTop: '4px' }}>
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

          {/* Selector de Modo PTT */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginTop: '6px' }}>
            <label
              onClick={() => setFormData({ ...formData, pttMode: 'hold' as PttMode })}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '10px 14px',
                borderRadius: '4px',
                backgroundColor: formData.pttMode === 'hold' ? 'rgba(0, 242, 255, 0.12)' : 'rgba(4, 18, 38, 0.4)',
                border: `1px solid ${formData.pttMode === 'hold' ? 'var(--cyan-neon)' : 'rgba(0, 242, 255, 0.15)'}`,
                cursor: 'pointer'
              }}
            >
              <input
                type="radio"
                name="pttMode"
                checked={formData.pttMode === 'hold'}
                onChange={() => setFormData({ ...formData, pttMode: 'hold' })}
                style={{ accentColor: 'var(--cyan-neon)' }}
              />
              <div>
                <div style={{ fontSize: '12px', fontWeight: 600, color: '#fff' }}>Mantener para hablar (Hold)</div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Habla mientras mantienes la tecla o botón</div>
              </div>
            </label>

            <label
              onClick={() => setFormData({ ...formData, pttMode: 'toggle' as PttMode })}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '10px 14px',
                borderRadius: '4px',
                backgroundColor: formData.pttMode === 'toggle' ? 'rgba(0, 242, 255, 0.12)' : 'rgba(4, 18, 38, 0.4)',
                border: `1px solid ${formData.pttMode === 'toggle' ? 'var(--cyan-neon)' : 'rgba(0, 242, 255, 0.15)'}`,
                cursor: 'pointer'
              }}
            >
              <input
                type="radio"
                name="pttMode"
                checked={formData.pttMode === 'toggle'}
                onChange={() => setFormData({ ...formData, pttMode: 'toggle' })}
                style={{ accentColor: 'var(--cyan-neon)' }}
              />
              <div>
                <div style={{ fontSize: '12px', fontWeight: 600, color: '#fff' }}>Pulsar para alternar (Toggle)</div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Pulsa una vez para iniciar y otra para enviar</div>
              </div>
            </label>
          </div>
        </div>

        {/* SECCIÓN 2: RESPUESTA POR VOZ (TEXT-TO-SPEECH // TTS) */}
        <div style={{
          padding: '18px 20px',
          borderRadius: 'var(--radius-sm)',
          backgroundColor: 'rgba(4, 16, 32, 0.5)',
          border: '1px solid var(--cyan-border)',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Volume2 size={16} color="var(--cyan-neon)" />
              <h3 style={{
                fontFamily: 'var(--font-hud)',
                fontSize: '13px',
                color: 'var(--cyan-neon)',
                margin: 0,
                letterSpacing: '1px'
              }}>
                2. SÍNTESIS Y RESPUESTA VOCAL (TTS)
              </h3>
            </div>

            <button
              type="button"
              onClick={handleTestVoice}
              className="hud-btn"
              style={{
                padding: '6px 14px',
                fontSize: '11px',
                borderColor: isPlayingTestVoice ? 'var(--amber-accent)' : 'var(--cyan-border)',
                backgroundColor: isPlayingTestVoice ? 'rgba(255, 183, 0, 0.2)' : 'rgba(0, 242, 255, 0.08)'
              }}
            >
              <Play size={12} className={isPlayingTestVoice ? 'animate-pulse-core' : ''} />
              <span>{isPlayingTestVoice ? 'DETENER PRUEBA' : 'PROBAR VOZ'}</span>
            </button>
          </div>

          {/* Toggle Auto Speak Response */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '10px 14px',
            backgroundColor: 'rgba(0, 242, 255, 0.04)',
            borderRadius: '4px',
            border: '1px solid rgba(0, 242, 255, 0.15)'
          }}>
            <div>
              <div style={{ fontSize: '13px', fontWeight: 600, color: '#fff' }}>
                Respuesta por Voz Automática
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Jarvis leerá automáticamente en voz alta sus respuestas.
              </div>
            </div>
            <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={formData.autoSpeakResponse}
                onChange={e => setFormData({ ...formData, autoSpeakResponse: e.target.checked })}
                style={{ width: '18px', height: '18px', accentColor: 'var(--cyan-neon)' }}
              />
            </label>
          </div>

          {/* Selector de Voz del Sistema Operativo */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
              VOZ DEL SISTEMA OPERATIVO:
            </label>
            <select
              value={formData.ttsVoiceURI}
              onChange={e => setFormData({ ...formData, ttsVoiceURI: e.target.value })}
              style={{
                backgroundColor: 'rgba(4, 18, 38, 0.9)',
                border: '1px solid var(--cyan-border)',
                borderRadius: '4px',
                padding: '8px 12px',
                color: '#fff',
                fontFamily: 'var(--font-sans)',
                fontSize: '13px',
                outline: 'none'
              }}
            >
              <option value="">Voz Predeterminada en Español</option>
              {availableVoices.map(voice => (
                <option key={voice.voiceURI} value={voice.voiceURI}>
                  {voice.name} ({voice.lang}) {voice.default ? '★' : ''}
                </option>
              ))}
            </select>
          </div>

          {/* Sliders de Velocidad y Tono */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                VELOCIDAD DE HABLA: {formData.ttsRate}x
              </label>
              <input
                type="range"
                min="0.75"
                max="1.4"
                step="0.05"
                value={formData.ttsRate}
                onChange={e => setFormData({ ...formData, ttsRate: parseFloat(e.target.value) })}
                style={{ accentColor: 'var(--cyan-neon)', marginTop: '4px' }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                TONO DE VOZ (PITCH): {formData.ttsPitch}
              </label>
              <input
                type="range"
                min="0.8"
                max="1.2"
                step="0.05"
                value={formData.ttsPitch}
                onChange={e => setFormData({ ...formData, ttsPitch: parseFloat(e.target.value) })}
                style={{ accentColor: 'var(--cyan-neon)', marginTop: '4px' }}
              />
            </div>
          </div>
        </div>

        {/* SECCIÓN 3: EFECTOS SONOROS Y FEEDBACK HUD */}
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
            <Sparkles size={16} color="var(--cyan-neon)" />
            <h3 style={{
              fontFamily: 'var(--font-hud)',
              fontSize: '13px',
              color: 'var(--cyan-neon)',
              margin: 0,
              letterSpacing: '1px'
            }}>
              3. FEEDBACK HUD & EFECTOS DE SONIDO
            </h3>
          </div>

          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '10px 14px',
            backgroundColor: 'rgba(0, 242, 255, 0.04)',
            borderRadius: '4px',
            border: '1px solid rgba(0, 242, 255, 0.15)'
          }}>
            <div>
              <div style={{ fontSize: '13px', fontWeight: 600, color: '#fff' }}>
                Efectos Sonoros Procedurales HUD
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Bips acústicos futuristas al abrir/cerrar micrófono y al completar acciones.
              </div>
            </div>
            <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={formData.soundEffects}
                onChange={e => setFormData({ ...formData, soundEffects: e.target.checked })}
                style={{ width: '18px', height: '18px', accentColor: 'var(--cyan-neon)' }}
              />
            </label>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                Sensibilidad de Reacción del Arc Reactor
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Ajusta la intensidad con la que los anillos holográficos pulsan con tu voz.
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

        {/* SECCIÓN 4: MOTOR DE RAZONAMIENTO */}
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
              4. CONEXIÓN AL MOTOR DE RAZONAMIENTO
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
