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

export type EmailCategoryType = 'URGENT' | 'UNIVERSITY' | 'NOTIFICATION' | 'NOT IMPORTANT' | 'SPAM';

export interface EmailDraftData {
  draft_id: string;
  original_message_id: string;
  account: 'GMAIL' | 'OUTLOOK' | string;
  account_address: string;
  recipient_name: string;
  recipient_email: string;
  subject: string;
  original_snippet: string;
  draft_body: string;
  category: EmailCategoryType;
  urgency_score: number;
  created_at: string;
}

export interface EmailItem {
  id: string;
  account: 'GMAIL' | 'OUTLOOK' | string;
  account_address: string;
  subject: string;
  from_name: string;
  from_address: string;
  reply_to_address: string;
  to_addresses?: string[];
  cc_addresses?: string[];
  received_at: string;
  body_snippet: string;
  body_text: string;
  has_attachments?: boolean;
  attachment_names?: string[];
  category: EmailCategoryType;
  urgency_score: number;
  requires_reply?: boolean;
  suggested_action?: string;
  draft?: {
    draft_id: string;
    draft_body: string;
    is_generating?: boolean;
    created_at?: string;
  };
}

export interface EmailActionPayload {
  action: 'approve_and_send' | 'discard_draft' | 'generate_draft' | 'regenerate_draft';
  draft_id?: string;
  email_id?: string;
  account?: string;
  recipient?: string;
  subject?: string;
  body?: string;
  instructions?: string;
  email?: Partial<EmailItem>;
}
