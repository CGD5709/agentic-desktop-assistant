import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  TabType,
  ChatMessage,
  AppSettings,
  ConfirmationRequest,
  EmailDraftData,
  EmailItem,
  ScheduledTask,
  TaskCreatePayload,
} from "./types";
import { HeaderHUD } from "./components/HeaderHUD";
import { ChatPanel } from "./components/ChatPanel";
import { ArcReactorHUD } from "./components/ArcReactorHUD";
import { TasksPanel } from "./components/TasksPanel";
import { ScheduledTaskModal } from "./components/ScheduledTaskModal";
import { SettingsView } from "./components/SettingsView";
import { ConfirmationModal } from "./components/ConfirmationModal";
import { EmailReviewDeck } from "./components/EmailReviewDeck";
import { wsService } from "./services/websocket";
import { notificationService } from "./services/notifications";
import { useVoice } from "./hooks/useVoice";

const DEFAULT_SETTINGS: AppSettings = {
  wsUrl: "ws://localhost:8000/ws",
  globalHotkey: "Numpad3",
  hotkeyDisplayName: "NUMPAD 3",
  audioSensitivity: 80,
  autoSpeakResponse: false,
  pttMode: "hold",
  ttsVoiceURI: "",
  ttsRate: 1.05,
  ttsPitch: 1.0,
  soundEffects: true,
};

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>("home");
  const [settings, setSettings] = useState<AppSettings>(() => {
    try {
      const saved = localStorage.getItem("jarvis_settings");
      return saved
        ? { ...DEFAULT_SETTINGS, ...JSON.parse(saved) }
        : DEFAULT_SETTINGS;
    } catch {
      return DEFAULT_SETTINGS;
    }
  });

  const [chatWidth, setChatWidth] = useState<number>(360);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "m-welcome",
      sender: "jarvis",
      content:
        "Buenos días. Todos los sistemas de asistencia y ejecución están en línea y a su completa disposición.",
      speechText:
        "Buenos días. Todos los sistemas de asistencia y ejecución están en línea y a su completa disposición.",
      timestamp: new Date().toLocaleTimeString("es-ES", {
        hour: "2-digit",
        minute: "2-digit",
      }),
    },
  ]);
  const [tasks, setTasks] = useState<ScheduledTask[]>([]);
  const [isTaskModalOpen, setIsTaskModalOpen] = useState<boolean>(false);
  const [availableToolsList, setAvailableToolsList] = useState<string[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<
    "CONNECTED" | "DISCONNECTED" | "CONNECTING"
  >("CONNECTING");
  const [assistantStatus, setAssistantStatus] = useState<"THINKING" | "IDLE">(
    "IDLE",
  );
  const [toolsCount, setToolsCount] = useState<number>(5);
  const [pendingConfirmation, setPendingConfirmation] =
    useState<ConfirmationRequest | null>(null);
  const [unreadEmails, setUnreadEmails] = useState<EmailItem[]>([]);
  const [activeEmailDraft, setActiveEmailDraft] =
    useState<EmailDraftData | null>(null);

  const autoSpeakRef = useRef(settings.autoSpeakResponse);
  autoSpeakRef.current = settings.autoSpeakResponse;

  /**
   * Dispatches user chat message to local state and WebSocket channel.
   */
  const handleSendMessage = useCallback((text: string) => {
    if (!text || !text.trim()) return;

    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`,
      sender: "user",
      content: text.trim(),
      timestamp: new Date().toLocaleTimeString("es-ES", {
        hour: "2-digit",
        minute: "2-digit",
      }),
    };

    setMessages((prev) => [...prev, userMsg]);
    wsService.sendUserMessage(text.trim());
  }, []);

  // Voice orchestration hook (STT, TTS, PTT, Audio Analysis)
  const {
    voiceState,
    audioLevel,
    interimTranscript,
    startListening,
    stopListening,
    toggleListening,
    cancelSpeech,
    speak,
  } = useVoice({
    hotkey: settings.globalHotkey,
    pttMode: settings.pttMode,
    ttsVoiceURI: settings.ttsVoiceURI,
    ttsRate: settings.ttsRate,
    ttsPitch: settings.ttsPitch,
    soundEffects: settings.soundEffects,
    onFinalTranscript: handleSendMessage,
  });

  // Stop controller: aborts active speech and active reasoning turn
  const handleStop = useCallback(() => {
    cancelSpeech();
    wsService.sendStop();
    setAssistantStatus("IDLE");
    setPendingConfirmation(null);
  }, [cancelSpeech]);

  // Human-in-the-Loop confirmation handlers
  const handleConfirmAction = useCallback(() => {
    if (pendingConfirmation) {
      wsService.sendConfirmationResponse(
        pendingConfirmation.confirmationId,
        true,
      );
      setPendingConfirmation(null);
    }
  }, [pendingConfirmation]);

  const handleCancelAction = useCallback(() => {
    if (pendingConfirmation) {
      wsService.sendConfirmationResponse(
        pendingConfirmation.confirmationId,
        false,
      );
      setPendingConfirmation(null);
    }
  }, [pendingConfirmation]);

  // Email subsystem action handlers
  const handleGenerateEmailDraft = useCallback(
    (email: EmailItem, instructions?: string) => {
      wsService.generateEmailDraft(email, instructions);
    },
    [],
  );

  const handleApproveAndSendEmail = useCallback(
    (
      draftId: string,
      account: string,
      recipient: string,
      subject: string,
      body: string,
      emailId: string,
    ) => {
      wsService.sendEmailAction({
        action: "approve_and_send",
        draft_id: draftId,
        account,
        recipient,
        subject,
        body,
        email_id: emailId,
      });
    },
    [],
  );

  const handleDiscardEmailDraft = useCallback(
    (draftId: string, emailId: string) => {
      wsService.sendEmailAction({
        action: "discard_draft",
        draft_id: draftId,
        email_id: emailId,
      });
      if (activeEmailDraft?.draft_id === draftId) {
        setActiveEmailDraft(null);
      }
    },
    [activeEmailDraft],
  );

  const handleCloseEmailDeck = useCallback(() => {
    setUnreadEmails([]);
    setActiveEmailDraft(null);
  }, []);

  // Scheduled Tasks action handlers
  const handleCreateTask = useCallback((taskPayload: TaskCreatePayload) => {
    wsService.createTask(taskPayload);
  }, []);

  const handleToggleTask = useCallback((taskId: string, enabled: boolean) => {
    wsService.toggleTask(taskId, enabled);
  }, []);

  const handleDeleteTask = useCallback((taskId: string) => {
    wsService.deleteTask(taskId);
  }, []);

  const handleRunTaskNow = useCallback((taskId: string) => {
    wsService.runTaskNow(taskId);
  }, []);

  // WebSocket subscription lifecycle
  useEffect(() => {
    notificationService.requestPermission();

    wsService.setUrl(settings.wsUrl);
    wsService.connect();

    const unsubStatus = wsService.onStatus((status) => {
      setConnectionStatus(status);
    });

    const unsubAssistantStatus = wsService.onAssistantStatus((state) => {
      setAssistantStatus(state);
    });

    const unsubTools = wsService.onTools((toolsList) => {
      setToolsCount(toolsList.length);
      setAvailableToolsList(toolsList);
    });

    const unsubTasks = wsService.onTasksList((tasksList) => {
      setTasks(tasksList);
    });

    const unsubTaskTriggered = wsService.onTaskTriggered((payload) => {
      const taskMsg: ChatMessage = {
        id: `msg-task-${Date.now()}`,
        sender: "system",
        content: `⏰ Tarea programada ejecutada: ${payload.name} [${payload.status}]`,
        speechText: payload.speech_text,
        timestamp: new Date().toLocaleTimeString("es-ES", {
          hour: "2-digit",
          minute: "2-digit",
        }),
      };
      setMessages((prev) => [...prev, taskMsg]);

      if (
        payload.speech_text &&
        (payload.notify_voice !== false || autoSpeakRef.current)
      ) {
        speak(payload.speech_text);
      }

      notificationService.sendNotification(`JARVIS - Tarea: ${payload.name}`, {
        body: payload.speech_text || `Estado: ${payload.status}`,
      });
    });

    const unsubUnreadEmails = wsService.onUnreadEmails((emails) => {
      setUnreadEmails(emails);
    });

    const unsubEmailDraft = wsService.onEmailDraft((draft) => {
      setActiveEmailDraft(draft);
    });

    const unsubEmailDraftCleared = wsService.onEmailDraftCleared(() => {
      setActiveEmailDraft(null);
    });

    const unsubConfirmation = wsService.onConfirmationRequest((req) => {
      setPendingConfirmation(req);

      // Trigger OS desktop notification if window is minimized or unfocused
      if (document.hidden || !document.hasFocus()) {
        notificationService.sendNotification(
          `[CONFIRMACIÓN REQUERIDA] JARVIS - ${req.title}`,
          {
            body: req.message,
            requireInteraction: true,
          },
        );
      }
    });

    const unsubMessage = wsService.onMessage((content, speechText) => {
      const newMsg: ChatMessage = {
        id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`,
        sender: "jarvis",
        content: content,
        speechText: speechText,
        timestamp: new Date().toLocaleTimeString("es-ES", {
          hour: "2-digit",
          minute: "2-digit",
        }),
      };
      setMessages((prev) => [...prev, newMsg]);

      if (autoSpeakRef.current && (speechText || content)) {
        speak(speechText || content);
      }
    });

    return () => {
      unsubStatus();
      unsubAssistantStatus();
      unsubTools();
      unsubTasks();
      unsubTaskTriggered();
      unsubUnreadEmails();
      unsubEmailDraft();
      unsubEmailDraftCleared();
      unsubConfirmation();
      unsubMessage();
      wsService.disconnect();
    };
  }, [settings.wsUrl, speak]);

  const handleClearMessages = useCallback(() => {
    setMessages([]);
    wsService.sendClearHistory();
  }, []);

  const handleSaveSettings = useCallback((newSettings: AppSettings) => {
    setSettings(newSettings);
    localStorage.setItem("jarvis_settings", JSON.stringify(newSettings));
  }, []);

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        position: "relative",
      }}
    >
      {/* Human-in-the-Loop Confirmation Modal */}
      {pendingConfirmation && (
        <ConfirmationModal
          request={pendingConfirmation}
          onConfirm={handleConfirmAction}
          onCancel={handleCancelAction}
        />
      )}

      {/* Scheduled Task Builder Modal */}
      <ScheduledTaskModal
        isOpen={isTaskModalOpen}
        availableTools={availableToolsList}
        onClose={() => setIsTaskModalOpen(false)}
        onCreateTask={handleCreateTask}
      />

      {/* Top Header HUD */}
      <HeaderHUD
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        connectionStatus={connectionStatus}
        voiceState={voiceState}
        hotkeyDisplayName={settings.hotkeyDisplayName}
        toolsCount={toolsCount}
        onToggleVoice={toggleListening}
      />

      {/* Main Workspace */}
      <main
        style={{
          flex: 1,
          display: "flex",
          padding: "0 16px 16px 16px",
          gap: "14px",
          overflow: "hidden",
          position: "relative",
        }}
      >
        {activeTab === "home" ? (
          <>
            {/* Chat Panel */}
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

            {/* Central Canvas: Email Review Deck or Arc Reactor */}
            {unreadEmails.length > 0 || activeEmailDraft ? (
              <EmailReviewDeck
                emails={
                  unreadEmails.length > 0
                    ? unreadEmails
                    : activeEmailDraft
                      ? [
                          {
                            id: activeEmailDraft.original_message_id,
                            account: activeEmailDraft.account,
                            account_address: activeEmailDraft.account_address,
                            subject: activeEmailDraft.subject,
                            from_name: activeEmailDraft.recipient_name,
                            from_address: activeEmailDraft.recipient_email,
                            reply_to_address: activeEmailDraft.recipient_email,
                            received_at: activeEmailDraft.created_at,
                            body_snippet: activeEmailDraft.original_snippet,
                            body_text: activeEmailDraft.original_snippet,
                            category: activeEmailDraft.category,
                            urgency_score: activeEmailDraft.urgency_score,
                            draft: {
                              draft_id: activeEmailDraft.draft_id,
                              draft_body: activeEmailDraft.draft_body,
                              is_generating: false,
                              created_at: activeEmailDraft.created_at,
                            },
                          },
                        ]
                      : []
                }
                activeDraft={activeEmailDraft}
                onGenerateDraft={handleGenerateEmailDraft}
                onApproveAndSend={handleApproveAndSendEmail}
                onDiscardDraft={handleDiscardEmailDraft}
                onClose={handleCloseEmailDeck}
              />
            ) : (
              <ArcReactorHUD
                voiceState={voiceState}
                audioLevel={audioLevel * (settings.audioSensitivity / 80)}
                toolsCount={toolsCount}
              />
            )}

            {/* Tasks Panel */}
            <TasksPanel
              tasks={tasks}
              onOpenCreateModal={() => setIsTaskModalOpen(true)}
              onToggleTask={handleToggleTask}
              onDeleteTask={handleDeleteTask}
              onRunTaskNow={handleRunTaskNow}
            />
          </>
        ) : (
          /* Settings View */
          <SettingsView
            settings={settings}
            onSaveSettings={handleSaveSettings}
            onClose={() => setActiveTab("home")}
          />
        )}
      </main>
    </div>
  );
};

export default App;
