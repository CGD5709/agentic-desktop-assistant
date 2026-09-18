import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage, VoiceState, PttMode } from '../types';
import { Send, Mic, Trash2, Bot, User, Sparkles, Terminal, Square, Volume2 } from 'lucide-react';

interface ChatPanelProps {
  messages: ChatMessage[];
  onSendMessage: (content: string) => void;
  onClearMessages: () => void;
  onStop: () => void;
  assistantStatus: 'THINKING' | 'IDLE';
  voiceState: VoiceState;
  onStartListening: () => void;
  onStopListening: () => void;
  onToggleVoice: () => void;
  interimTranscript?: string;
  hotkeyDisplayName: string;
  pttMode: PttMode;
  width: number;
  onWidthChange: (newWidth: number) => void;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({
  messages,
  onSendMessage,
  onClearMessages,
  onStop,
  assistantStatus,
  voiceState,
  onStartListening,
  onStopListening,
  onToggleVoice,
  interimTranscript = '',
  hotkeyDisplayName,
  pttMode,
  width,
  onWidthChange
}) => {
  const [inputText, setInputText] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const isBusy = assistantStatus === 'THINKING' || voiceState === 'SPEAKING';
  const isListening = voiceState === 'LISTENING';
  const isSpeaking = voiceState === 'SPEAKING';

  // Auto-scroll al final de la conversación
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, assistantStatus, interimTranscript]);

  // Manejo de redimensionado arrastrando el borde derecho
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
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
    if (isBusy) {
      onStop();
      return;
    }
    if (!inputText.trim()) return;
    onSendMessage(inputText);
    setInputText('');
  };

  // Mic Button event handlers depending on PTT mode
  const handleMicMouseDown = (e: React.MouseEvent) => {
    if (pttMode === 'hold') {
      e.preventDefault();
      onStartListening();
    }
  };

  const handleMicMouseUp = (e: React.MouseEvent) => {
    if (pttMode === 'hold') {
      e.preventDefault();
      onStopListening();
    }
  };

  const handleMicTouchStart = (e: React.TouchEvent) => {
    if (pttMode === 'hold') {
      e.preventDefault();
      onStartListening();
    }
  };

  const handleMicTouchEnd = (e: React.TouchEvent) => {
    if (pttMode === 'hold') {
      e.preventDefault();
      onStopListening();
    }
  };

  const handleMicClick = () => {
    if (pttMode === 'toggle') {
      onToggleVoice();
    }
  };

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
              Escribe un mensaje o usa [{hotkeyDisplayName}] ({pttMode === 'hold' ? 'Mantén presionado' : 'Pulsa'}) para hablar.
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
                    fontFamily: 'var(--font-sans)'
                  }}
                >
                  {msg.content}
                </div>
              </div>
            );
          })
        )}

        {/* Indicador de escucha en tiempo real */}
        {isListening && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 12px',
            borderRadius: '6px',
            backgroundColor: 'rgba(0, 255, 194, 0.1)',
            border: '1px solid var(--teal-accent)',
            fontSize: '12px',
            fontFamily: 'var(--font-mono)',
            color: 'var(--teal-accent)'
          }}>
            <Mic size={14} className="animate-pulse-core" />
            <span>Escuchando... {interimTranscript ? `"${interimTranscript}"` : '(habla ahora)'}</span>
          </div>
        )}

        {/* Indicador de pensamiento de Jarvis */}
        {assistantStatus === 'THINKING' && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 12px',
            borderRadius: '6px',
            backgroundColor: 'rgba(255, 183, 0, 0.1)',
            border: '1px solid var(--amber-accent)',
            fontSize: '12px',
            fontFamily: 'var(--font-mono)',
            color: 'var(--amber-accent)'
          }}>
            <Sparkles size={14} className="animate-spin-fast" />
            <span>J.A.R.V.I.S razonando... (pulsa el botón Stop para detener)</span>
          </div>
        )}

        {/* Indicador de habla activa de Jarvis */}
        {isSpeaking && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 12px',
            borderRadius: '6px',
            backgroundColor: 'rgba(0, 242, 255, 0.1)',
            border: '1px solid var(--cyan-neon)',
            fontSize: '12px',
            fontFamily: 'var(--font-mono)',
            color: 'var(--cyan-bright)'
          }}>
            <Volume2 size={14} className="animate-pulse-core" />
            <span>J.A.R.V.I.S hablando... (pulsa Stop o habla para interrumpir)</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 3. Input Bar con Botón Dinámico Send / Stop (Estilo Gemini) */}
      <form onSubmit={handleSend} style={{
        padding: '12px',
        borderTop: '1px solid var(--cyan-border)',
        backgroundColor: 'var(--bg-input)',
        display: 'flex',
        alignItems: 'center',
        gap: '8px'
      }}>
        {/* Botón de Micrófono con soporte PTT */}
        <button
          type="button"
          onMouseDown={handleMicMouseDown}
          onMouseUp={handleMicMouseUp}
          onTouchStart={handleMicTouchStart}
          onTouchEnd={handleMicTouchEnd}
          onClick={handleMicClick}
          className="hud-btn"
          style={{
            padding: '8px',
            borderColor: isListening ? 'var(--teal-accent)' : 'var(--cyan-border)',
            backgroundColor: isListening ? 'rgba(0, 255, 194, 0.25)' : 'transparent',
            boxShadow: isListening ? '0 0 12px var(--teal-glow)' : 'none',
            cursor: 'pointer',
            userSelect: 'none'
          }}
          title={`Voz [${hotkeyDisplayName}] (${pttMode === 'hold' ? 'Mantén presionado para hablar' : 'Pulsa para alternar'})`}
        >
          <Mic size={16} color={isListening ? 'var(--teal-accent)' : 'var(--cyan-neon)'} className={isListening ? 'animate-pulse-core' : ''} />
        </button>

        <input
          ref={inputRef}
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder={isListening ? "Escuchando tu voz..." : "Escribe una orden o pregunta..."}
          disabled={assistantStatus === 'THINKING'}
          style={{
            flex: 1,
            backgroundColor: 'rgba(0, 242, 255, 0.04)',
            border: `1px solid ${isListening ? 'var(--teal-accent)' : 'var(--cyan-border)'}`,
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
            e.target.style.borderColor = isListening ? 'var(--teal-accent)' : 'var(--cyan-border)';
            e.target.style.boxShadow = 'none';
          }}
        />

        {/* Botón Dinámico Send / Stop (Estilo Gemini) */}
        {isBusy ? (
          <button
            type="button"
            onClick={onStop}
            className="hud-btn hud-btn-danger"
            style={{
              padding: '8px 14px',
              backgroundColor: 'rgba(255, 75, 75, 0.2)',
              borderColor: 'rgba(255, 75, 75, 0.7)',
              boxShadow: '0 0 12px rgba(255, 75, 75, 0.4)',
              cursor: 'pointer'
            }}
            title="Detener procesamiento / habla (Stop)"
          >
            <Square size={14} fill="currentColor" color="#ff4b4b" />
          </button>
        ) : (
          <button
            type="submit"
            className="hud-btn"
            disabled={!inputText.trim()}
            style={{
              padding: '8px 14px',
              opacity: !inputText.trim() ? 0.4 : 1,
              cursor: !inputText.trim() ? 'not-allowed' : 'pointer'
            }}
            title="Enviar orden"
          >
            <Send size={15} />
          </button>
        )}
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
