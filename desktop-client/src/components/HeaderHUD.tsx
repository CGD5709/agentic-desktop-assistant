import React, { useState, useEffect } from 'react';
import { TabType, VoiceState } from '../types';
import { Mic, Settings as SettingsIcon, LayoutDashboard, Cpu } from 'lucide-react';

interface HeaderHUDProps {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
  connectionStatus: 'CONNECTED' | 'DISCONNECTED' | 'CONNECTING';
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
  onToggleVoice
}) => {
  const [timeStr, setTimeStr] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(now.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const isConnected = connectionStatus === 'CONNECTED';
  const isListening = voiceState === 'LISTENING';

  return (
    <header className="hud-panel hud-corners" style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '10px 24px',
      margin: '12px 16px 8px 16px',
      borderRadius: 'var(--radius-md)',
      zIndex: 10,
      flexShrink: 0
    }}>
      {/* 1. Left Branding: J.A.R.V.I.S Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div style={{
          width: '38px',
          height: '38px',
          borderRadius: '50%',
          border: '1.5px solid var(--cyan-neon)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 0 12px var(--cyan-glow), inset 0 0 8px var(--cyan-glow)',
          position: 'relative'
        }}>
          <div style={{
            width: '14px',
            height: '14px',
            borderRadius: '50%',
            backgroundColor: isListening ? 'var(--teal-accent)' : 'var(--cyan-neon)',
            boxShadow: isListening ? '0 0 10px var(--teal-accent)' : '0 0 8px var(--cyan-neon)'
          }} className="animate-pulse-core" />
        </div>

        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 className="hud-title" style={{ fontSize: '18px', margin: 0, letterSpacing: '3px' }}>
              J.A.R.V.I.S
            </h1>
            <span style={{
              fontSize: '10px',
              fontFamily: 'var(--font-mono)',
              padding: '1px 6px',
              borderRadius: '2px',
              backgroundColor: 'rgba(0, 242, 255, 0.1)',
              border: '1px solid var(--cyan-border)',
              color: 'var(--cyan-neon)'
            }}>
              v2.5 // LOCAL
            </span>
          </div>
          <p style={{
            fontSize: '11px',
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-muted)',
            letterSpacing: '1px',
            margin: 0
          }}>
            JUST A RATHER VERY INTELLIGENT SYSTEM
          </p>
        </div>
      </div>

      {/* 2. Center: Navigation Tabs */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <button
          className={`hud-btn ${activeTab === 'home' ? 'active' : ''}`}
          onClick={() => setActiveTab('home')}
          style={{ padding: '8px 20px' }}
        >
          <LayoutDashboard size={15} color={activeTab === 'home' ? '#fff' : 'var(--cyan-neon)'} />
          <span>01 // INICIO</span>
        </button>

        <button
          className={`hud-btn ${activeTab === 'settings' ? 'active' : ''}`}
          onClick={() => setActiveTab('settings')}
          style={{ padding: '8px 20px' }}
        >
          <SettingsIcon size={15} color={activeTab === 'settings' ? '#fff' : 'var(--cyan-neon)'} />
          <span>02 // AJUSTES</span>
        </button>
      </div>

      {/* 3. Right Telemetry & Status Badges */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '18px' }}>
        {/* Tools count indicator */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontSize: '12px',
          fontFamily: 'var(--font-mono)',
          color: 'var(--text-secondary)'
        }}>
          <Cpu size={14} color="var(--cyan-neon)" />
          <span>TOOLS:</span>
          <span style={{ color: 'var(--cyan-neon)', fontWeight: 'bold' }}>{toolsCount}</span>
        </div>

        {/* Mic Toggle Button */}
        <button
          onClick={onToggleVoice}
          className="hud-btn"
          style={{
            borderColor: isListening ? 'var(--teal-accent)' : 'var(--cyan-border)',
            background: isListening ? 'rgba(0, 255, 194, 0.2)' : 'rgba(0, 242, 255, 0.08)',
            boxShadow: isListening ? '0 0 16px var(--teal-glow)' : 'none',
            padding: '6px 12px'
          }}
          title={`Activar / Desactivar Micrófono [${hotkeyDisplayName}]`}
        >
          <Mic size={14} color={isListening ? 'var(--teal-accent)' : 'var(--cyan-neon)'} className={isListening ? 'animate-pulse-core' : ''} />
          <span style={{ color: isListening ? 'var(--teal-accent)' : 'var(--text-primary)', fontSize: '11px' }}>
            {isListening ? 'VOZ: ESCUCHANDO' : `MIC [${hotkeyDisplayName}]`}
          </span>
        </button>

        {/* Connection status pill */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '7px',
          padding: '4px 10px',
          borderRadius: '4px',
          backgroundColor: isConnected ? 'rgba(0, 255, 194, 0.1)' : 'rgba(255, 51, 102, 0.1)',
          border: `1px solid ${isConnected ? 'rgba(0, 255, 194, 0.3)' : 'rgba(255, 51, 102, 0.3)'}`,
          fontSize: '11px',
          fontFamily: 'var(--font-mono)'
        }}>
          <div style={{
            width: '7px',
            height: '7px',
            borderRadius: '50%',
            backgroundColor: isConnected ? 'var(--teal-accent)' : 'var(--red-alert)',
            boxShadow: `0 0 6px ${isConnected ? 'var(--teal-accent)' : 'var(--red-alert)'}`
          }} />
          <span style={{ color: isConnected ? 'var(--teal-accent)' : '#ff99b3', fontWeight: 'bold' }}>
            {connectionStatus}
          </span>
        </div>

        {/* Digital Clock */}
        <div style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '14px',
          color: 'var(--cyan-neon)',
          letterSpacing: '2px',
          fontWeight: 600,
          textShadow: '0 0 8px var(--cyan-glow)'
        }}>
          {timeStr}
        </div>
      </div>
    </header>
  );
};
