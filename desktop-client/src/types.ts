export type TabType = 'home' | 'settings';

export type VoiceState = 'IDLE' | 'LISTENING' | 'THINKING' | 'SPEAKING';

export interface ChatMessage {
  id: string;
  sender: 'user' | 'jarvis' | 'system';
  content: string;
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
}
