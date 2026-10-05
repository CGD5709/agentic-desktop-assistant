export type TabType = "home" | "settings";

export type VoiceState = "IDLE" | "LISTENING" | "THINKING" | "SPEAKING";

export type PttMode = "hold" | "toggle";

export interface ChatMessage {
  id: string;
  sender: "user" | "jarvis" | "system";
  content: string;
  speechText?: string;
  timestamp: string;
  isStreaming?: boolean;
}

export type TaskTriggerType = "ONE_SHOT" | "CRON" | "INTERVAL";
export type ScheduledTaskStatus = "ACTIVE" | "PAUSED" | "COMPLETED" | "EXPIRED";

export interface TriggerConfig {
  run_at?: string;
  cron_expr?: string;
  interval_seconds?: number;
}

export interface ScheduledTask {
  id: string;
  name: string;
  description?: string;
  tool_name: string;
  tool_arguments?: Record<string, any>;
  trigger_type: TaskTriggerType;
  trigger_config: TriggerConfig;
  status: ScheduledTaskStatus;
  notify_voice: boolean;
  created_at: string;
  last_run_at?: string | null;
  next_run_at?: string | null;
}

export interface TaskCreatePayload {
  name: string;
  description?: string;
  tool_name: string;
  tool_arguments?: Record<string, any>;
  trigger_type: TaskTriggerType;
  trigger_config: TriggerConfig;
  notify_voice?: boolean;
}

export interface TaskTriggeredPayload {
  task_id: string;
  name: string;
  status: string;
  result?: Record<string, any>;
  speech_text?: string;
  notify_voice?: boolean;
}

export interface TaskItem {
  id: string;
  title: string;
  description: string;
  status: "PENDING" | "IN_PROGRESS" | "DONE";
  priority: "LOW" | "MEDIUM" | "HIGH";
  category: string;
  createdAt: string;
}

export interface AppSettings {
  wsUrl: string;
  globalHotkey: string; // e.g., 'Numpad3'
  hotkeyDisplayName: string; // e.g., 'NUMPAD 3'
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
  severity?: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  target?: string;
  details?: Record<string, any>;
}

export type EmailCategoryType =
  "URGENT" | "UNIVERSITY" | "NOTIFICATION" | "NOT IMPORTANT" | "SPAM";

export interface EmailDraftData {
  draft_id: string;
  original_message_id: string;
  account: "GMAIL" | "OUTLOOK" | string;
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
  account: "GMAIL" | "OUTLOOK" | string;
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
  action:
    | "approve_and_send"
    | "discard_draft"
    | "generate_draft"
    | "regenerate_draft";
  draft_id?: string;
  email_id?: string;
  account?: string;
  recipient?: string;
  subject?: string;
  body?: string;
  instructions?: string;
  email?: Partial<EmailItem>;
}
