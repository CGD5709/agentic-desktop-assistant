import React, { useState, useEffect, useCallback, useRef } from 'react';
import { TabType, ChatMessage, TaskItem, AppSettings } from './types';
import { HeaderHUD } from './components/HeaderHUD';
import { ChatPanel } from './components/ChatPanel';
import { ArcReactorHUD } from './components/ArcReactorHUD';
import { TasksPanel } from './components/TasksPanel';
import { SettingsView } from './components/SettingsView';
import { wsService } from './services/websocket';
import { useVoice } from './hooks/useVoice';

const DEFAULT_SETTINGS: AppSettings = {
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

const INITIAL_TASKS: TaskItem[] = [
  {
    id: 't-1',
    title: 'Diagnóstico de Procesos del Sistema',
    description: 'Monitorear los procesos que consumen más de 500 MB de RAM.',
    status: 'DONE',
    priority: 'MEDIUM',
    category: 'SYSTEM',
    createdAt: '10:15:00'
  },
  {
    id: 't-2',
    title: 'Control de Audio del Sistema',
    description: 'Ajustar y monitorear los niveles de sonido maestro en Windows.',
    status: 'IN_PROGRESS',
    priority: 'HIGH',
    category: 'AUDIO',
    createdAt: '10:45:12'
  },
  {
    id: 't-3',
    title: 'Sincronizar Almacén de Memoria a Largo Plazo',
    description: 'Indexar nuevas preferencias del usuario en ChromaDB.',
    status: 'PENDING',
    priority: 'LOW',
    category: 'MEMORY',
    createdAt: '11:00:30'
  }
];

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('home');
  const [settings, setSettings] = useState<AppSettings>(() => {
    try {
      const saved = localStorage.getItem('jarvis_settings');
      return saved ? { ...DEFAULT_SETTINGS, ...JSON.parse(saved) } : DEFAULT_SETTINGS;
    } catch {
      return DEFAULT_SETTINGS;
    }
  });

  const [chatWidth, setChatWidth] = useState<number>(360);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'm-welcome',
      sender: 'jarvis',
      content: 'Buenos días. Todos los sistemas de asistencia y ejecución están en línea y a su completa disposición.',
      speechText: 'Buenos días. Todos los sistemas de asistencia y ejecución están en línea y a su completa disposición.',
      timestamp: new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [tasks] = useState<TaskItem[]>(INITIAL_TASKS);
  const [connectionStatus, setConnectionStatus] = useState<'CONNECTED' | 'DISCONNECTED' | 'CONNECTING'>('CONNECTING');
  const [assistantStatus, setAssistantStatus] = useState<'THINKING' | 'IDLE'>('IDLE');
  const [toolsCount, setToolsCount] = useState<number>(5);

  const autoSpeakRef = useRef(settings.autoSpeakResponse);
  autoSpeakRef.current = settings.autoSpeakResponse;

  // Enviar mensaje de usuario
  const handleSendMessage = useCallback((text: string) => {
    if (!text || !text.trim()) return;

    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`,
      sender: 'user',
      content: text.trim(),
      timestamp: new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    wsService.sendUserMessage(text.trim());
  }, []);

  // Hook unificado de voz (STT, TTS, PTT, Audio Analysis)
  const {
    voiceState,
    audioLevel,
    interimTranscript,
    startListening,
    stopListening,
    toggleListening,
    cancelSpeech,
    speak
  } = useVoice({
    hotkey: settings.globalHotkey,
    pttMode: settings.pttMode,
    ttsVoiceURI: settings.ttsVoiceURI,
    ttsRate: settings.ttsRate,
    ttsPitch: settings.ttsPitch,
    soundEffects: settings.soundEffects,
    onFinalTranscript: handleSendMessage
  });

  // Botón de Parada (Stop) estilo Gemini
  const handleStop = useCallback(() => {
    cancelSpeech();
    wsService.sendStop();
    setAssistantStatus('IDLE');
  }, [cancelSpeech]);

  // Conexión WebSocket al motor de razonamiento de Python
  useEffect(() => {
    wsService.setUrl(settings.wsUrl);
    wsService.connect();

    const unsubStatus = wsService.onStatus(status => {
      setConnectionStatus(status);
    });

    const unsubAssistantStatus = wsService.onAssistantStatus(state => {
      setAssistantStatus(state);
    });

    const unsubTools = wsService.onTools(toolsList => {
      setToolsCount(toolsList.length);
    });

    const unsubMessage = wsService.onMessage((content, speechText) => {
      const newMsg: ChatMessage = {
        id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`,
        sender: 'jarvis',
        content: content,
        speechText: speechText,
        timestamp: new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, newMsg]);

      // Reproducción automática de voz si está activada
      if (autoSpeakRef.current && (speechText || content)) {
        speak(speechText || content);
      }
    });

    return () => {
      unsubStatus();
      unsubAssistantStatus();
      unsubTools();
      unsubMessage();
      wsService.disconnect();
    };
  }, [settings.wsUrl, speak]);

  const handleClearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  const handleSaveSettings = useCallback((newSettings: AppSettings) => {
    setSettings(newSettings);
    localStorage.setItem('jarvis_settings', JSON.stringify(newSettings));
  }, []);

  return (
    <div style={{
      width: '100%',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      position: 'relative'
    }}>
      {/* 1. Header Superior HUD */}
      <HeaderHUD
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        connectionStatus={connectionStatus}
        voiceState={voiceState}
        hotkeyDisplayName={settings.hotkeyDisplayName}
        toolsCount={toolsCount}
        onToggleVoice={toggleListening}
      />

      {/* 2. Área Principal de Trabajo */}
      <main style={{
        flex: 1,
        display: 'flex',
        padding: '0 16px 16px 16px',
        gap: '14px',
        overflow: 'hidden',
        position: 'relative'
      }}>
        {activeTab === 'home' ? (
          <>
            {/* Panel de Chat (Izquierda, Redimensionable con Botón Dinámico Stop/Send) */}
            <ChatPanel
              messages={messages}
              onSendMessage={handleSendMessage}
              onClearMessages={handleClearMessages}
              onStop={handleStop}
              assistantStatus={assistantStatus}
              voiceState={voiceState}
              onStartListening={startListening}
              onStopListening={stopListening}
              onToggleVoice={toggleListening}
              interimTranscript={interimTranscript}
              hotkeyDisplayName={settings.hotkeyDisplayName}
              pttMode={settings.pttMode}
              width={chatWidth}
              onWidthChange={setChatWidth}
            />

            {/* Canvas Central Libre con Arc Reactor Reactivo */}
            <ArcReactorHUD
              voiceState={voiceState}
              audioLevel={audioLevel * (settings.audioSensitivity / 80)}
              toolsCount={toolsCount}
            />

            {/* Panel de Tareas Pendientes (Derecha) */}
            <TasksPanel
              tasks={tasks}
            />
          </>
        ) : (
          /* Pantalla de Ajustes */
          <SettingsView
            settings={settings}
            onSaveSettings={handleSaveSettings}
            onClose={() => setActiveTab('home')}
          />
        )}
      </main>
    </div>
  );
};

export default App;
