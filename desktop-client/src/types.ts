export type TabType = 'home' | 'settings';

export type VoiceState = 'IDLE' | 'LISTENING' | 'THINKING' | 'SPEAKING';

export type PttMode = 'hold' | 'toggle';

export interface ChatMessage {
  id: string;
  sender: 'user' | 'jarvis' | 'system';
  content: string;
  speechText?: string;
  timestamp: string;
  isStreaming?: boolean;
}

export interface TaskItem {
  id: string;
  title: string;
  description: string;
  status: 'PENDING' | 'IN_PROGRESS' | 'DONE';
  priority: 'LOW' | 'MEDIUM' | 'HIGH';
  category: string;
  createdAt: string;
}

export interface AppSettings {
  wsUrl: string;
  globalHotkey: string; // e.g., 'Numpad3'
  hotkeyDisplayName: string; // e.g., 'NUMPAD 3'
  modelName: string;
  temperature: number;
  audioSensitivity: number;
  autoSpeakResponse: boolean;
  pttMode: PttMode;
  ttsVoiceURI: string;
  ttsRate: number;
  ttsPitch: number;
  soundEffects: boolean;
}

export interface ConfirmationRequest {
  confirmationId: string;
  toolName: string;
  arguments: Record<string, any>;
  title: string;
  message: string;
  severity?: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  target?: string;
  details?: Record<string, any>;
}
