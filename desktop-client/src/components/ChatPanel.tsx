import React, { useState, useRef, useEffect } from "react";
import { ChatMessage, VoiceState, PttMode } from "../types";
import {
  Send,
  Mic,
  Trash2,
  Bot,
  Sparkles,
  MessageSquare,
  Square,
  Volume2,
} from "lucide-react";

interface ChatPanelProps {
  messages: ChatMessage[];
  onSendMessage: (content: string) => void;
  onClearMessages: () => void;
  onStop: () => void;
  assistantStatus: "THINKING" | "IDLE";
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
  interimTranscript = "",
  hotkeyDisplayName,
  pttMode,
  width,
  onWidthChange,
}) => {
  const [inputText, setInputText] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const isBusy = assistantStatus === "THINKING" || voiceState === "SPEAKING";
  const isListening = voiceState === "LISTENING";
  const isSpeaking = voiceState === "SPEAKING";

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, assistantStatus, interimTranscript]);

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
      window.addEventListener("mousemove", handleMouseMove);
      window.addEventListener("mouseup", handleMouseUp);
    }
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
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
    setInputText("");
  };

  const handleMicMouseDown = (e: React.MouseEvent) => {
    if (pttMode === "hold") {
      e.preventDefault();
      onStartListening();
    }
  };

  const handleMicMouseUp = (e: React.MouseEvent) => {
    if (pttMode === "hold") {
      e.preventDefault();
      onStopListening();
    }
  };

  const handleMicClick = () => {
    if (pttMode === "toggle") {
      onToggleVoice();
    }
  };

  return (
    <div
      className="hud-panel"
      style={{
        width: `${width}px`,
        height: "100%",
        display: "flex",
        flexDirection: "column",
        position: "relative",
        flexShrink: 0,
        overflow: "hidden",
      }}
    >
      {/* 1. Panel Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "16px",
          borderBottom: "1px solid var(--border-color)",
          backgroundColor: "var(--bg-surface-elevated)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <MessageSquare size={18} className="text-muted" />
          <span className="title-primary">
            Chat Asistente
          </span>
        </div>

        <button
          onClick={onClearMessages}
          className="hud-btn hud-btn-danger"
          style={{ padding: "6px", minWidth: "auto" }}
          title="Limpiar registro de chat"
        >
          <Trash2 size={14} />
        </button>
      </div>

      {/* 2. Message Feed */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "16px",
          display: "flex",
          flexDirection: "column",
          gap: "16px",
        }}
      >
        {messages.length === 0 ? (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              color: "var(--text-muted)",
              textAlign: "center",
              gap: "12px",
            }}
          >
            <Bot size={32} style={{ opacity: 0.5 }} />
            <p style={{ margin: 0, fontSize: "14px", fontWeight: 500 }}>Sistema Listo</p>
            <p style={{ fontSize: "13px", color: "var(--text-muted)", maxWidth: "200px" }}>
              Escribe un mensaje o usa [{hotkeyDisplayName}] para hablar.
            </p>
          </div>
        ) : (
          messages.map((msg) => {
            const isUser = msg.sender === "user";
            return (
              <div
                key={msg.id}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: isUser ? "flex-end" : "flex-start",
                  gap: "6px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    fontSize: "11px",
                    color: "var(--text-muted)",
                  }}
                >
                  {isUser ? (
                    <>
                      <span>{msg.timestamp}</span>
                      <span style={{ fontWeight: 500 }}>TÚ</span>
                    </>
                  ) : (
                    <>
                      <Bot size={12} />
                      <span style={{ fontWeight: 500 }}>ASISTENTE</span>
                      <span>{msg.timestamp}</span>
                    </>
                  )}
                </div>

                <div
                  style={{
                    maxWidth: "90%",
                    padding: "12px 16px",
                    borderRadius: isUser ? "14px 14px 0 14px" : "14px 14px 14px 0",
                    backgroundColor: isUser ? "var(--primary-accent)" : "var(--bg-surface-elevated)",
                    color: isUser ? "#fff" : "var(--text-primary)",
                    border: isUser ? "none" : "1px solid var(--border-color)",
                    fontSize: "13.5px",
                    lineHeight: "1.5",
                    wordBreak: "break-word",
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {msg.content}
                </div>
              </div>
            );
          })
        )}

        {isListening && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "10px 14px",
              borderRadius: "var(--radius-md)",
              backgroundColor: "var(--bg-surface-elevated)",
              border: "1px solid var(--success-color)",
              fontSize: "13px",
              color: "var(--success-color)",
            }}
          >
            <Mic size={14} className="animate-pulse-core" />
            <span>
              Escuchando... {interimTranscript ? `"${interimTranscript}"` : ""}
            </span>
          </div>
        )}

        {assistantStatus === "THINKING" && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "10px 14px",
              borderRadius: "var(--radius-md)",
              backgroundColor: "var(--bg-surface-elevated)",
              border: "1px solid var(--warning-color)",
              fontSize: "13px",
              color: "var(--warning-color)",
            }}
          >
            <Sparkles size={14} className="animate-pulse-core" />
            <span>Procesando...</span>
          </div>
        )}

        {isSpeaking && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "10px 14px",
              borderRadius: "var(--radius-md)",
              backgroundColor: "var(--bg-surface-elevated)",
              border: "1px solid var(--primary-accent)",
              fontSize: "13px",
              color: "var(--primary-accent)",
            }}
          >
            <Volume2 size={14} className="animate-pulse-core" />
            <span>Hablando...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 3. Input Bar */}
      <form
        onSubmit={handleSend}
        style={{
          padding: "16px",
          borderTop: "1px solid var(--border-color)",
          backgroundColor: "var(--bg-surface)",
          display: "flex",
          alignItems: "center",
          gap: "10px",
        }}
      >
        <button
          type="button"
          onMouseDown={handleMicMouseDown}
          onMouseUp={handleMicMouseUp}
          onMouseLeave={handleMicMouseUp}
          onClick={handleMicClick}
          className={`hud-btn ${isListening ? "hud-btn-primary" : ""}`}
          style={{
            padding: "10px",
            borderRadius: "50%",
            width: "36px",
            height: "36px",
          }}
          title={`Voz [${hotkeyDisplayName}]`}
        >
          <Mic size={16} />
        </button>

        <input
          ref={inputRef}
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder={isListening ? "Escuchando..." : "Mensaje..."}
          disabled={assistantStatus === "THINKING"}
          style={{ flex: 1 }}
        />

        {isBusy ? (
          <button
            type="button"
            onClick={onStop}
            className="hud-btn hud-btn-danger"
            style={{
              padding: "10px",
              borderRadius: "50%",
              width: "36px",
              height: "36px",
            }}
            title="Detener"
          >
            <Square size={14} fill="currentColor" />
          </button>
        ) : (
          <button
            type="submit"
            className="hud-btn hud-btn-primary"
            disabled={!inputText.trim()}
            style={{
              padding: "10px",
              borderRadius: "50%",
              width: "36px",
              height: "36px",
              opacity: !inputText.trim() ? 0.5 : 1,
            }}
          >
            <Send size={15} style={{ marginLeft: "2px" }} />
          </button>
        )}
      </form>

      {/* 4. Drag bar */}
      <div
        onMouseDown={() => setIsDragging(true)}
        style={{
          position: "absolute",
          top: 0,
          right: 0,
          width: "4px",
          height: "100%",
          cursor: "col-resize",
          backgroundColor: isDragging ? "var(--primary-accent)" : "transparent",
          transition: "background-color 0.2s",
          zIndex: 100,
        }}
        onMouseEnter={(e) => {
          (e.target as HTMLElement).style.backgroundColor = "var(--border-color)";
        }}
        onMouseLeave={(e) => {
          if (!isDragging) {
            (e.target as HTMLElement).style.backgroundColor = "transparent";
          }
        }}
      />
    </div>
  );
};
