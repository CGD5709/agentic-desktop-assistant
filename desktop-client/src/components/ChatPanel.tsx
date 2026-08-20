import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage, VoiceState } from '../types';
import { Send, Mic, Trash2, Bot, User, Sparkles, Terminal } from 'lucide-react';

interface ChatPanelProps {
  messages: ChatMessage[];
  onSendMessage: (content: string) => void;
  onClearMessages: () => void;
  assistantStatus: 'THINKING' | 'IDLE';
  voiceState: VoiceState;
  onToggleVoice: () => void;
  hotkeyDisplayName: string;
  width: number;
  onWidthChange: (newWidth: number) => void;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({
  messages,
  onSendMessage,
  onClearMessages,
  assistantStatus,
  voiceState,
  onToggleVoice,
  hotkeyDisplayName,
  width,
  onWidthChange
}) => {
  const [inputText, setInputText] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll al final de la conversación
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, assistantStatus]);

  // Manejo de redimensionado arrastrando el borde derecho
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
      // Ancho mínimo 280px, máximo 650px
      const newWidth = Math.min(Math.max(280, e.clientX - 16), 650);
      onWidthChange(newWidth);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, onWidthChange]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || assistantStatus === 'THINKING') return;
    onSendMessage(inputText);
    setInputText('');
  };

  const isListening = voiceState === 'LISTENING';

  return (
    <div
      className="hud-panel hud-corners"
      style={{
        width: `${width}px`,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        borderRadius: 'var(--radius-md)',
        flexShrink: 0,
        overflow: 'hidden'
      }}
    >
      {/* 1. Header del panel */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 16px',
        borderBottom: '1px solid var(--cyan-border)',
        backgroundColor: 'rgba(4, 14, 28, 0.6)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Terminal size={16} color="var(--cyan-neon)" />
          <span style={{
            fontFamily: 'var(--font-hud)',
            fontSize: '13px',
            color: 'var(--cyan-neon)',
            letterSpacing: '1.5px',
            fontWeight: 700
          }}>
            COMM LOG // CHAT
          </span>
        </div>

        <button
          onClick={onClearMessages}
          className="hud-btn hud-btn-danger"
          style={{ padding: '4px 8px', fontSize: '10px' }}
          title="Limpiar registro de chat"
        >
          <Trash2 size={12} />
          <span>CLEAR</span>
        </button>
      </div>

      {/* 2. Feed de Mensajes */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '14px'
      }}>
        {messages.length === 0 ? (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            color: 'var(--text-muted)',
            textAlign: 'center',
            gap: '12px',
            fontFamily: 'var(--font-mono)',
            fontSize: '12px'
          }}>
            <Bot size={32} color="var(--cyan-border)" className="animate-pulse-core" />
            <p>SISTEMA LISTO // ESPERANDO COMANDO</p>
            <p style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
              Escribe un mensaje o pulsa [{hotkeyDisplayName}] para hablar por voz.
            </p>
          </div>
        ) : (
          messages.map((msg) => {
            const isUser = msg.sender === 'user';
            return (
              <div
                key={msg.id}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: isUser ? 'flex-end' : 'flex-start',
                  gap: '4px'
                }}
              >
                {/* Cabecera del mensaje */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '10px',
                  fontFamily: 'var(--font-mono)',
                  color: isUser ? 'var(--cyan-neon)' : 'var(--teal-accent)'
                }}>
                  {isUser ? (
                    <>
                      <span>{msg.timestamp}</span>
                      <span style={{ fontWeight: 'bold' }}>USUARIO</span>
                      <User size={11} />
                    </>
                  ) : (
                    <>
                      <Bot size={11} />
                      <span style={{ fontWeight: 'bold' }}>J.A.R.V.I.S</span>
                      <span>{msg.timestamp}</span>
                    </>
                  )}
                </div>

                {/* Burbuja del mensaje */}
                <div
                  style={{
                    maxWidth: '90%',
                    padding: '10px 14px',
                    borderRadius: isUser ? '10px 2px 10px 10px' : '2px 10px 10px 10px',
                    backgroundColor: isUser ? 'rgba(0, 242, 255, 0.12)' : 'rgba(4, 18, 36, 0.85)',
                    border: `1px solid ${isUser ? 'rgba(0, 242, 255, 0.35)' : 'rgba(0, 255, 194, 0.25)'}`,
                    boxShadow: isUser ? '0 2px 12px rgba(0, 242, 255, 0.1)' : '0 2px 12px rgba(0, 0, 0, 0.3)',
                    color: 'var(--text-primary)',
                    fontSize: '13.5px',
                    lineHeight: '1.5',
                    wordBreak: 'break-word',
                    whiteSpace: 'pre-wrap',
                    fontFamily: isUser ? 'var(--font-sans)' : 'var(--font-sans)'
                  }}
                >
                  {msg.content}
                </div>
              </div>
            );
          })
        )}

        {/* Indicador de pensamiento de Jarvis */}
        {assistantStatus === 'THINKING' && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 12px',
            borderRadius: '6px',
            backgroundColor: 'rgba(0, 242, 255, 0.08)',
            border: '1px solid var(--cyan-border)',
            fontSize: '12px',
            fontFamily: 'var(--font-mono)',
            color: 'var(--cyan-neon)'
          }}>
            <Sparkles size={14} className="animate-spin-fast" />
            <span>J.A.R.V.I.S procesando razonamiento...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 3. Input Bar */}
      <form onSubmit={handleSend} style={{
        padding: '12px',
        borderTop: '1px solid var(--cyan-border)',
        backgroundColor: 'var(--bg-input)',
        display: 'flex',
        alignItems: 'center',
        gap: '8px'
      }}>
        <button
          type="button"
          onClick={onToggleVoice}
          className="hud-btn"
          style={{
            padding: '8px',
            borderColor: isListening ? 'var(--teal-accent)' : 'var(--cyan-border)',
            backgroundColor: isListening ? 'rgba(0, 255, 194, 0.25)' : 'transparent',
            boxShadow: isListening ? '0 0 12px var(--teal-glow)' : 'none'
          }}
          title={`Activar entrada por voz [${hotkeyDisplayName}]`}
        >
          <Mic size={16} color={isListening ? 'var(--teal-accent)' : 'var(--cyan-neon)'} className={isListening ? 'animate-pulse-core' : ''} />
        </button>

        <input
          ref={inputRef}
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Escribe una orden o pregunta..."
          disabled={assistantStatus === 'THINKING'}
          style={{
            flex: 1,
            backgroundColor: 'rgba(0, 242, 255, 0.04)',
            border: '1px solid var(--cyan-border)',
            borderRadius: 'var(--radius-sm)',
            padding: '9px 12px',
            color: '#fff',
            fontFamily: 'var(--font-sans)',
            fontSize: '13.5px',
            outline: 'none',
            transition: 'border-color 0.2s, box-shadow 0.2s'
          }}
          onFocus={(e) => {
            e.target.style.borderColor = 'var(--cyan-neon)';
            e.target.style.boxShadow = '0 0 10px var(--cyan-glow)';
          }}
          onBlur={(e) => {
            e.target.style.borderColor = 'var(--cyan-border)';
            e.target.style.boxShadow = 'none';
          }}
        />

        <button
          type="submit"
          className="hud-btn"
          disabled={!inputText.trim() || assistantStatus === 'THINKING'}
          style={{
            padding: '8px 14px',
            opacity: (!inputText.trim() || assistantStatus === 'THINKING') ? 0.4 : 1,
            cursor: (!inputText.trim() || assistantStatus === 'THINKING') ? 'not-allowed' : 'pointer'
          }}
        >
          <Send size={15} />
        </button>
      </form>

      {/* 4. Barra de arrastre para redimensionar el panel */}
      <div
        onMouseDown={() => setIsDragging(true)}
        style={{
          position: 'absolute',
          top: 0,
          right: 0,
          width: '5px',
          height: '100%',
          cursor: 'col-resize',
          backgroundColor: isDragging ? 'var(--cyan-neon)' : 'transparent',
          transition: 'background-color 0.2s',
          zIndex: 100
        }}
        onMouseEnter={(e) => {
          (e.target as HTMLElement).style.backgroundColor = 'rgba(0, 242, 255, 0.4)';
        }}
        onMouseLeave={(e) => {
          if (!isDragging) {
            (e.target as HTMLElement).style.backgroundColor = 'transparent';
          }
        }}
      />
    </div>
  );
};
