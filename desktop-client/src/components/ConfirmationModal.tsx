import React, { useEffect } from 'react';
import { ConfirmationRequest } from '../types';
import { ShieldAlert, CheckCircle2, XCircle, Terminal, AlertTriangle } from 'lucide-react';

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
  // Support keyboard shortcuts (Enter for confirm, Escape for cancel)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        onConfirm();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onCancel();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onConfirm, onCancel]);

  const isDestructive = request.toolName === 'matar_proceso' || request.severity === 'CRITICAL';
  const accentColor = isDestructive ? 'var(--red-alert)' : 'var(--amber-accent)';
  const glowColor = isDestructive ? 'rgba(255, 51, 102, 0.4)' : 'rgba(255, 183, 0, 0.4)';

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        backgroundColor: 'rgba(3, 7, 16, 0.85)',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
        padding: '20px',
        animation: 'fadeIn 0.2s ease-out',
      }}
    >
      <div
        className="hud-panel hud-corners"
        style={{
          width: '100%',
          maxWidth: '520px',
          backgroundColor: 'var(--bg-surface-elevated)',
          border: `1.5px solid ${accentColor}`,
          boxShadow: `0 0 35px ${glowColor}, inset 0 0 15px rgba(0, 0, 0, 0.6)`,
          borderRadius: 'var(--radius-lg)',
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '18px',
          position: 'relative',
          overflow: 'hidden',
          animation: 'slideUp 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
        }}
      >
        {/* Top Scanline Pulse */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: '2px',
            background: `linear-gradient(90deg, transparent, ${accentColor}, transparent)`,
            animation: 'pulse 2s infinite',
          }}
        />

        {/* 1. Header Banner */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div
            style={{
              width: '46px',
              height: '46px',
              borderRadius: 'var(--radius-md)',
              backgroundColor: isDestructive ? 'rgba(255, 51, 102, 0.15)' : 'rgba(255, 183, 0, 0.15)',
              border: `1.5px solid ${accentColor}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: `0 0 15px ${glowColor}`,
              flexShrink: 0,
            }}
          >
            {isDestructive ? (
              <ShieldAlert size={26} color="var(--red-alert)" />
            ) : (
              <AlertTriangle size={26} color="var(--amber-accent)" />
            )}
          </div>

          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '2px' }}>
              <span
                style={{
                  fontSize: '11px',
                  fontFamily: 'var(--font-hud)',
                  letterSpacing: '1px',
                  color: accentColor,
                  textTransform: 'uppercase',
                  fontWeight: 700,
                }}
              >
                AUTORIZACIÓN REQUERIDA (HITL)
              </span>
              <span
                style={{
                  fontSize: '10px',
                  padding: '1px 6px',
                  borderRadius: '10px',
                  backgroundColor: isDestructive ? 'rgba(255, 51, 102, 0.25)' : 'rgba(255, 183, 0, 0.25)',
                  color: accentColor,
                  border: `1px solid ${accentColor}`,
                  fontFamily: 'var(--font-mono)',
                  fontWeight: 600,
                }}
              >
                {request.severity || 'CRITICAL'}
              </span>
            </div>
            <h2
              style={{
                fontSize: '18px',
                fontFamily: 'var(--font-tech)',
                fontWeight: 700,
                color: 'var(--text-primary)',
                letterSpacing: '0.5px',
                margin: 0,
                lineHeight: 1.2,
              }}
            >
              {request.title || 'Confirmación de Acción Crítica'}
            </h2>
          </div>
        </div>

        {/* 2. Main Question / Message */}
        <div
          style={{
            fontSize: '15px',
            lineHeight: 1.5,
            color: 'var(--text-primary)',
            padding: '12px 14px',
            backgroundColor: 'rgba(4, 14, 28, 0.65)',
            borderLeft: `3px solid ${accentColor}`,
            borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
          }}
        >
          {request.message}
        </div>

        {/* 3. Contextual Details Box */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            backgroundColor: 'var(--bg-input)',
            border: '1px solid var(--cyan-border)',
            borderRadius: 'var(--radius-md)',
            padding: '12px 14px',
            fontFamily: 'var(--font-mono)',
            fontSize: '12px',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              color: 'var(--text-secondary)',
              borderBottom: '1px solid rgba(0, 242, 255, 0.15)',
              paddingBottom: '6px',
              marginBottom: '2px',
              fontFamily: 'var(--font-hud)',
              fontSize: '11px',
              letterSpacing: '0.8px',
            }}
          >
            <Terminal size={14} color="var(--cyan-neon)" />
            <span>METADATOS DE EJECUCIÓN</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '6px 12px', alignItems: 'baseline' }}>
            <span style={{ color: 'var(--text-muted)' }}>Herramienta:</span>
            <span style={{ color: 'var(--cyan-bright)', fontWeight: 600 }}>{request.toolName}</span>

            {request.details &&
              Object.entries(request.details).map(([key, value]) => (
                <React.Fragment key={key}>
                  <span style={{ color: 'var(--text-muted)' }}>{key}:</span>
                  <span
                    style={{
                      color: key.toLowerCase().includes('impacto') ? 'var(--red-alert)' : 'var(--text-primary)',
                      wordBreak: 'break-word',
                      fontWeight: key.toLowerCase().includes('proceso') || key.toLowerCase().includes('pid') ? 700 : 400,
                    }}
                  >
                    {String(value)}
                  </span>
                </React.Fragment>
              ))}
          </div>
        </div>

        {/* 4. Action Buttons */}
        <div
          style={{
            display: 'flex',
            gap: '12px',
            marginTop: '6px',
          }}
        >
          {/* Cancel Button */}
          <button
            onClick={onCancel}
            className="hud-button"
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              padding: '12px 16px',
              backgroundColor: 'rgba(255, 51, 102, 0.1)',
              border: '1.5px solid var(--red-alert)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-primary)',
              fontFamily: 'var(--font-tech)',
              fontSize: '14px',
              fontWeight: 700,
              letterSpacing: '0.8px',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'rgba(255, 51, 102, 0.25)';
              e.currentTarget.style.boxShadow = '0 0 15px rgba(255, 51, 102, 0.4)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'rgba(255, 51, 102, 0.1)';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            <XCircle size={18} color="var(--red-alert)" />
            <span>CANCELAR (Esc)</span>
          </button>

          {/* Confirm Button */}
          <button
            onClick={onConfirm}
            className="hud-button"
            style={{
              flex: 1.2,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              padding: '12px 16px',
              backgroundColor: 'rgba(0, 242, 255, 0.15)',
              border: '1.5px solid var(--cyan-neon)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--cyan-neon)',
              fontFamily: 'var(--font-tech)',
              fontSize: '14px',
              fontWeight: 700,
              letterSpacing: '0.8px',
              cursor: 'pointer',
              boxShadow: '0 0 12px var(--cyan-glow)',
              transition: 'all 0.15s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--cyan-neon)';
              e.currentTarget.style.color = 'var(--bg-space)';
              e.currentTarget.style.boxShadow = '0 0 22px var(--cyan-neon)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'rgba(0, 242, 255, 0.15)';
              e.currentTarget.style.color = 'var(--cyan-neon)';
              e.currentTarget.style.boxShadow = '0 0 12px var(--cyan-glow)';
            }}
          >
            <CheckCircle2 size={18} />
            <span>AUTORIZAR EJECUCIÓN (Enter)</span>
          </button>
        </div>
      </div>
    </div>
  );
};
