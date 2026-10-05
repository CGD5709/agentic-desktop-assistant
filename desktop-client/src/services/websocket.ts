import {
  ConfirmationRequest,
  EmailDraftData,
  EmailActionPayload,
  EmailItem,
  ScheduledTask,
  TaskCreatePayload,
  TaskTriggeredPayload,
} from "../types";

type StatusCallback = (
  status: "CONNECTED" | "DISCONNECTED" | "CONNECTING",
) => void;
type MessageCallback = (content: string, speechText?: string) => void;
type AssistantStatusCallback = (state: "THINKING" | "IDLE") => void;
type ToolsCallback = (tools: string[]) => void;
type ConfirmationCallback = (request: ConfirmationRequest) => void;
type EmailDraftCallback = (draft: EmailDraftData) => void;
type EmailDraftClearedCallback = (draftId?: string) => void;
type UnreadEmailsCallback = (emails: EmailItem[]) => void;
type TasksListCallback = (tasks: ScheduledTask[]) => void;
type TaskTriggeredCallback = (payload: TaskTriggeredPayload) => void;

export class JarvisWebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectInterval: number = 2500;
  private reconnectTimer: number | null = null;
  private shouldReconnect: boolean = true;
  private pingInterval: number | null = null;

  private onStatusListeners: Set<StatusCallback> = new Set();
  private onMessageListeners: Set<MessageCallback> = new Set();
  private onAssistantStatusListeners: Set<AssistantStatusCallback> = new Set();
  private onToolsListeners: Set<ToolsCallback> = new Set();
  private onConfirmationListeners: Set<ConfirmationCallback> = new Set();
  private onEmailDraftListeners: Set<EmailDraftCallback> = new Set();
  private onEmailDraftClearedListeners: Set<EmailDraftClearedCallback> =
    new Set();
  private onUnreadEmailsListeners: Set<UnreadEmailsCallback> = new Set();
  private onTasksListListeners: Set<TasksListCallback> = new Set();
  private onTaskTriggeredListeners: Set<TaskTriggeredCallback> = new Set();

  constructor(url: string = "ws://localhost:8000/ws") {
    this.url = url;
  }

  public setUrl(newUrl: string) {
    if (this.url !== newUrl) {
      this.url = newUrl;
      this.disconnect();
      this.connect();
    }
  }

  public connect() {
    if (
      this.ws &&
      (this.ws.readyState === WebSocket.OPEN ||
        this.ws.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    if (this.reconnectTimer) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    this.shouldReconnect = true;
    this.notifyStatus("CONNECTING");

    try {
      const ws = new WebSocket(this.url);
      this.ws = ws;

      ws.onopen = () => {
        if (this.ws !== ws) return;
        this.notifyStatus("CONNECTED");
        this.startHeartbeat();
      };

      ws.onmessage = (event) => {
        if (this.ws !== ws) return;
        try {
          const data = JSON.parse(event.data);
          this.handleIncomingMessage(data);
        } catch (err) {
          console.warn("[WS] Error parsing incoming message:", err);
        }
      };

      ws.onclose = () => {
        if (this.ws !== ws) return;
        this.stopHeartbeat();
        this.notifyStatus("DISCONNECTED");
        if (this.shouldReconnect) {
          this.scheduleReconnect();
        }
      };

      ws.onerror = (error) => {
        if (this.ws !== ws) return;
        console.warn("[WS] Socket error event:", error);
      };
    } catch (e) {
      console.error("[WS] Connection initialization error:", e);
      this.notifyStatus("DISCONNECTED");
      this.scheduleReconnect();
    }
  }

  public disconnect() {
    this.shouldReconnect = false;
    this.stopHeartbeat();
    if (this.reconnectTimer) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      const socketToClose = this.ws;
      this.ws = null;
      socketToClose.onopen = null;
      socketToClose.onmessage = null;
      socketToClose.onerror = null;
      socketToClose.onclose = null;
      try {
        socketToClose.close();
      } catch (err) {
        console.warn("[WS] Error closing socket:", err);
      }
    }
    this.notifyStatus("DISCONNECTED");
  }

  public sendUserMessage(content: string) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn("[WS] Cannot send message: not connected.");
      return false;
    }

    this.ws.send(
      JSON.stringify({
        type: "user_message",
        content: content.trim(),
      }),
    );
    return true;
  }

  public sendStop() {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return false;
    }

    this.ws.send(
      JSON.stringify({
        type: "stop",
      }),
    );
    return true;
  }

  public sendClearHistory() {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return false;
    }

    this.ws.send(
      JSON.stringify({
        type: "clear_history",
      }),
    );
    return true;
  }

  public sendConfirmationResponse(confirmationId: string, confirmed: boolean) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn("[WS] Cannot send confirmation: not connected.");
      return false;
    }

    this.ws.send(
      JSON.stringify({
        type: "confirmation_response",
        confirmation_id: confirmationId,
        confirmed: confirmed,
      }),
    );
    return true;
  }

  public sendEmailAction(payload: EmailActionPayload) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn("[WS] Cannot send email action: not connected.");
      return false;
    }

    this.ws.send(
      JSON.stringify({
        type: "email_action",
        ...payload,
      }),
    );
    return true;
  }

  private handleIncomingMessage(data: any) {
    switch (data.type) {
      case "assistant_message":
        this.onMessageListeners.forEach((cb) =>
          cb(data.content || "", data.speech_text),
        );
        break;
      case "status":
        this.onAssistantStatusListeners.forEach((cb) =>
          cb(data.state || "IDLE"),
        );
        break;
      case "connected":
        if (data.tools) {
          this.onToolsListeners.forEach((cb) => cb(data.tools));
        }
        break;
      case "tools_updated":
        if (data.tools) {
          this.onToolsListeners.forEach((cb) => cb(data.tools));
        }
        break;
      case "unread_emails_list":
        if (Array.isArray(data.emails)) {
          this.onUnreadEmailsListeners.forEach((cb) => cb(data.emails));
        }
        break;
      case "email_draft_view":
        if (data.draft_id || data.draftId || data.data) {
          const draftData: EmailDraftData = data.data || data;
          this.onEmailDraftListeners.forEach((cb) => cb(draftData));
        }
        break;
      case "email_draft_cleared":
        this.onEmailDraftClearedListeners.forEach((cb) =>
          cb(data.draft_id || data.draftId),
        );
        break;
      case "confirmation_request":
        const req: ConfirmationRequest = {
          confirmationId: data.confirmation_id,
          toolName: data.tool_name,
          arguments: data.arguments || {},
          title: data.title || "Confirmación de Acción Crítica",
          message: data.message || "¿Deseas permitir esta operación?",
          severity: data.severity || "CRITICAL",
          target: data.target,
          details: data.details || {},
        };
        this.onConfirmationListeners.forEach((cb) => cb(req));
        break;
      case "tasks_list":
        if (Array.isArray(data.tasks)) {
          this.onTasksListListeners.forEach((cb) => cb(data.tasks));
        }
        break;
      case "task_triggered":
        this.onTaskTriggeredListeners.forEach((cb) => cb(data));
        break;
      case "pong":
        break;
      default:
        break;
    }
  }

  public startHeartbeat() {
    this.stopHeartbeat();
    this.pingInterval = window.setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: "ping" }));
      }
    }, 15000);
  }

  public stopHeartbeat() {
    if (this.pingInterval) {
      window.clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return;
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      if (this.shouldReconnect) {
        this.connect();
      }
    }, this.reconnectInterval);
  }

  public onStatus(cb: StatusCallback) {
    this.onStatusListeners.add(cb);
    return () => this.onStatusListeners.delete(cb);
  }

  public onMessage(cb: MessageCallback) {
    this.onMessageListeners.add(cb);
    return () => this.onMessageListeners.delete(cb);
  }

  public onAssistantStatus(cb: AssistantStatusCallback) {
    this.onAssistantStatusListeners.add(cb);
    return () => this.onAssistantStatusListeners.delete(cb);
  }

  public onTools(cb: ToolsCallback) {
    this.onToolsListeners.add(cb);
    return () => this.onToolsListeners.delete(cb);
  }

  public onConfirmationRequest(cb: ConfirmationCallback) {
    this.onConfirmationListeners.add(cb);
    return () => this.onConfirmationListeners.delete(cb);
  }

  public onEmailDraft(cb: EmailDraftCallback) {
    this.onEmailDraftListeners.add(cb);
    return () => this.onEmailDraftListeners.delete(cb);
  }

  public onEmailDraftCleared(cb: EmailDraftClearedCallback) {
    this.onEmailDraftClearedListeners.add(cb);
    return () => this.onEmailDraftClearedListeners.delete(cb);
  }

  public onUnreadEmails(cb: UnreadEmailsCallback) {
    this.onUnreadEmailsListeners.add(cb);
    return () => this.onUnreadEmailsListeners.delete(cb);
  }

  public onTasksList(cb: TasksListCallback) {
    this.onTasksListListeners.add(cb);
    return () => this.onTasksListListeners.delete(cb);
  }

  public onTaskTriggered(cb: TaskTriggeredCallback) {
    this.onTaskTriggeredListeners.add(cb);
    return () => this.onTaskTriggeredListeners.delete(cb);
  }

  public getTasks() {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return false;
    this.ws.send(JSON.stringify({ type: "tasks_get" }));
    return true;
  }

  public createTask(task: TaskCreatePayload) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return false;
    this.ws.send(JSON.stringify({ type: "task_create", task }));
    return true;
  }

  public toggleTask(taskId: string, enabled: boolean) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return false;
    this.ws.send(
      JSON.stringify({ type: "task_toggle", task_id: taskId, enabled }),
    );
    return true;
  }

  public deleteTask(taskId: string) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return false;
    this.ws.send(JSON.stringify({ type: "task_delete", task_id: taskId }));
    return true;
  }

  public runTaskNow(taskId: string) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return false;
    this.ws.send(JSON.stringify({ type: "task_run_now", task_id: taskId }));
    return true;
  }

  public generateEmailDraft(email: EmailItem, instructions?: string) {
    return this.sendEmailAction({
      action: "generate_draft",
      email_id: email.id,
      account: email.account,
      recipient: email.reply_to_address || email.from_address,
      subject: email.subject,
      instructions: instructions,
      email: {
        id: email.id,
        account: email.account,
        account_address: email.account_address,
        subject: email.subject,
        from_name: email.from_name,
        from_address: email.from_address,
        reply_to_address: email.reply_to_address,
        body_text: email.body_text,
        body_snippet: email.body_snippet,
        category: email.category,
        urgency_score: email.urgency_score,
      },
    });
  }

  private notifyStatus(status: "CONNECTED" | "DISCONNECTED" | "CONNECTING") {
    this.onStatusListeners.forEach((cb) => cb(status));
  }
}

// Shared singleton instance
export const wsService = new JarvisWebSocketClient();
