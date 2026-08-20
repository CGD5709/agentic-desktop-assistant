import React from 'react';
import { VoiceState } from '../types';
import { Activity, Radio } from 'lucide-react';

interface ArcReactorHUDProps {
  voiceState: VoiceState;
  audioLevel: number;
  toolsCount: number;
}

export const ArcReactorHUD: React.FC<ArcReactorHUDProps> = ({
  voiceState,
  audioLevel,
  toolsCount
}) => {
  const isListening = voiceState === 'LISTENING';
  const isThinking = voiceState === 'THINKING';

  // El nivel de audio escala dinámicamente el pulso y los anillos
  const dynamicScale = isListening ? 1 + audioLevel * 0.45 : 1;
  const coreGlowIntensity = isListening 
    ? `0 0 ${25 + audioLevel * 60}px rgba(0, 255, 194, 0.9)`
    : isThinking 
    ? '0 0 35px rgba(255, 183, 0, 0.8)'
    : '0 0 25px rgba(0, 242, 255, 0.6)';

  const coreColor = isListening ? 'var(--teal-accent)' : isThinking ? 'var(--amber-accent)' : 'var(--cyan-neon)';

  return (
    <div
      className="hud-panel hud-corners"
      style={{
        flex: 1,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        borderRadius: 'var(--radius-md)',
        overflow: 'hidden',
        padding: '24px'
      }}
    >
      {/* HUD Telemetry Top Left Corner */}
      <div style={{
        position: 'absolute',
        top: '16px',
        left: '20px',
        fontFamily: 'var(--font-mono)',
        fontSize: '11px',
        color: 'var(--text-muted)',
        display: 'flex',
        flexDirection: 'column',
        gap: '4px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Activity size={13} color="var(--cyan-neon)" />
          <span style={{ color: 'var(--cyan-neon)' }}>SYS.STATUS:</span>
          <span>ONLINE // NORMAL</span>
        </div>
        <div>QUANTUM CORE: STABLE (99.8%)</div>
        <div>ACTIVE MODULES: {toolsCount + 4} LOADED</div>
      </div>

      {/* HUD Telemetry Top Right Corner */}
      <div style={{
        position: 'absolute',
        top: '16px',
        right: '20px',
        fontFamily: 'var(--font-mono)',
        fontSize: '11px',
        color: 'var(--text-muted)',
        textAlign: 'right',
        display: 'flex',
        flexDirection: 'column',
        gap: '4px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '6px' }}>
          <Radio size={13} color={isListening ? 'var(--teal-accent)' : 'var(--cyan-neon)'} />
          <span style={{ color: isListening ? 'var(--teal-accent)' : 'var(--cyan-neon)' }}>
            VOICE FREQ: {isListening ? `${Math.round(audioLevel * 100)}%` : 'STANDBY'}
          </span>
        </div>
        <div>LATENCY: &lt; 12ms // LOCAL ENGINE</div>
        <div>SECURITY: SHIELD ACTIVE</div>
      </div>

      {/* ARC REACTOR CENTRAL SVG VISUALIZER */}
      <div style={{
        position: 'relative',
        width: '320px',
        height: '320px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        transform: `scale(${dynamicScale})`,
        transition: 'transform 0.08s ease-out'
      }}>
        <svg
          viewBox="0 0 300 300"
          width="100%"
          height="100%"
          style={{ position: 'absolute', top: 0, left: 0 }}
        >
          {/* Anillo exterior dentado */}
          <g className="animate-spin-slow" style={{ transformOrigin: '150px 150px' }}>
            <circle
              cx="150"
              cy="150"
              r="135"
              fill="none"
              stroke="rgba(0, 242, 255, 0.2)"
              strokeWidth="2"
              strokeDasharray="4 8"
            />
          </g>

          {/* Anillo exterior graduado con ticks */}
          <g className="animate-spin-reverse" style={{ transformOrigin: '150px 150px' }}>
            <circle
              cx="150"
              cy="150"
              r="122"
              fill="none"
              stroke="var(--cyan-neon)"
              strokeWidth="3"
              strokeDasharray="2 12"
              opacity="0.6"
            />
          </g>

          {/* Anillo concéntrico 2 estático */}
          <circle
            cx="150"
            cy="150"
            r="105"
            fill="none"
            stroke="rgba(0, 242, 255, 0.4)"
            strokeWidth="1.5"
            strokeDasharray="16 6 4 6"
          />

          {/* Arco sectorial rotatorio */}
          <g className="animate-spin-fast" style={{ transformOrigin: '150px 150px' }}>
            <circle
              cx="150"
              cy="150"
              r="92"
              fill="none"
              stroke={isListening ? 'var(--teal-accent)' : 'var(--cyan-bright)'}
              strokeWidth="4"
              strokeDasharray="90 180"
              strokeLinecap="round"
              style={{ filter: `drop-shadow(0 0 8px ${isListening ? 'var(--teal-accent)' : 'var(--cyan-neon)'})` }}
            />
          </g>

          {/* Anillo interior sectorizado */}
          <g className="animate-spin-reverse" style={{ transformOrigin: '150px 150px' }}>
            <circle
              cx="150"
              cy="150"
              r="75"
              fill="none"
              stroke="rgba(0, 242, 255, 0.5)"
              strokeWidth="2.5"
              strokeDasharray="8 8"
            />
          </g>

          {/* Anillo circular del reactor */}
          <circle
            cx="150"
            cy="150"
            r="55"
            fill="rgba(4, 18, 38, 0.7)"
            stroke="var(--cyan-neon)"
            strokeWidth="2"
          />

          {/* Rayos radiales de energía */}
          {[0, 45, 90, 135, 180, 225, 270, 315].map((deg) => (
            <line
              key={deg}
              x1="150"
              y1="150"
              x2={150 + 50 * Math.cos((deg * Math.PI) / 180)}
              y2={150 + 50 * Math.sin((deg * Math.PI) / 180)}
              stroke="rgba(0, 242, 255, 0.3)"
              strokeWidth="1.5"
            />
          ))}
        </svg>

        {/* NÚCLEO LUMINOSO CENTRAL (PULSE CORE) */}
        <div
          style={{
            width: '60px',
            height: '60px',
            borderRadius: '50%',
            backgroundColor: coreColor,
            boxShadow: coreGlowIntensity,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 5,
            transition: 'all 0.15s ease'
          }}
          className={isThinking ? 'animate-spin-fast' : 'animate-pulse-core'}
        >
          <div style={{
            width: '24px',
            height: '24px',
            borderRadius: '50%',
            backgroundColor: '#ffffff',
            boxShadow: '0 0 14px #ffffff'
          }} />
        </div>
      </div>

      {/* Subtítulos HUD y estado de Jarvis */}
      <div style={{
        marginTop: '20px',
        textAlign: 'center',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '6px'
      }}>
        <h2 style={{
          fontFamily: 'var(--font-hud)',
          fontSize: '18px',
          letterSpacing: '4px',
          color: coreColor,
          textShadow: `0 0 12px ${coreColor}`,
          margin: 0
        }}>
          {isListening ? 'LISTENING // AUDIO INPUT ACTIVE' : isThinking ? 'PROCESSING QUERY...' : 'J.A.R.V.I.S // ONLINE'}
        </h2>

        <p style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '12px',
          color: 'var(--text-secondary)',
          letterSpacing: '1.5px',
          margin: 0
        }}>
          {isListening 
            ? 'HABLA AL MICRÓFONO... ESCUCHANDO TU ORDEN' 
            : isThinking
            ? 'CONSULTANDO MODELO LOCAL Y HERRAMIENTAS'
            : 'SISTEMA DE ASISTENCIA Y EJECUCIÓN PREPARADO'}
        </p>

        {/* Action Button Badge */}
        <div style={{
          marginTop: '10px',
          padding: '4px 14px',
          borderRadius: '12px',
          backgroundColor: 'rgba(0, 242, 255, 0.08)',
          border: '1px solid var(--cyan-border)',
          fontFamily: 'var(--font-mono)',
          fontSize: '11px',
          color: 'var(--cyan-neon)'
        }}>
          CANVAS LIBRE PARA ARTEFACTOS & WIDGETS
        </div>
      </div>
    </div>
  );
};
