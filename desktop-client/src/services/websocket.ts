import { ConfirmationRequest } from '../types';

type StatusCallback = (status: 'CONNECTED' | 'DISCONNECTED' | 'CONNECTING') => void;
type MessageCallback = (content: string, speechText?: string) => void;
type AssistantStatusCallback = (state: 'THINKING' | 'IDLE') => void;
type ToolsCallback = (tools: string[]) => void;
type ConfirmationCallback = (request: ConfirmationRequest) => void;

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

  constructor(url: string = 'ws://localhost:8000/ws') {
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
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    if (this.reconnectTimer) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    this.shouldReconnect = true;
    this.notifyStatus('CONNECTING');

    try {
      const ws = new WebSocket(this.url);
      this.ws = ws;

      ws.onopen = () => {
        if (this.ws !== ws) return;
        this.notifyStatus('CONNECTED');
        this.startHeartbeat();
      };

      ws.onmessage = (event) => {
        if (this.ws !== ws) return;
        try {
          const data = JSON.parse(event.data);
          this.handleIncomingMessage(data);
        } catch (err) {
          console.warn('[WS] Error parseando mensaje entrante:', err);
        }
      };

      ws.onclose = () => {
        if (this.ws !== ws) return;
        this.stopHeartbeat();
        this.notifyStatus('DISCONNECTED');
        if (this.shouldReconnect) {
          this.scheduleReconnect();
        }
      };

      ws.onerror = (error) => {
        if (this.ws !== ws) return;
        console.warn('[WS] Error de socket:', error);
      };
    } catch (e) {
      console.error('[WS] Fallo de inicialización de conexión:', e);
      this.notifyStatus('DISCONNECTED');
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
        console.warn('[WS] Error al cerrar socket:', err);
      }
    }
    this.notifyStatus('DISCONNECTED');
  }

  public sendUserMessage(content: string) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('[WS] No conectado al enviar mensaje.');
      return false;
    }

    this.ws.send(JSON.stringify({
      type: 'user_message',
      content: content.trim()
    }));
    return true;
  }

  public sendStop() {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return false;
    }

    this.ws.send(JSON.stringify({
      type: 'stop'
    }));
    return true;
  }

  public sendConfirmationResponse(confirmationId: string, confirmed: boolean) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('[WS] No conectado al enviar respuesta de confirmación.');
      return false;
    }

    this.ws.send(JSON.stringify({
      type: 'confirmation_response',
      confirmation_id: confirmationId,
      confirmed: confirmed
    }));
    return true;
  }

  private handleIncomingMessage(data: any) {
    switch (data.type) {
      case 'assistant_message':
        this.onMessageListeners.forEach(cb => cb(data.content || '', data.speech_text));
        break;
      case 'status':
        this.onAssistantStatusListeners.forEach(cb => cb(data.state || 'IDLE'));
        break;
      case 'connected':
        if (data.tools) {
          this.onToolsListeners.forEach(cb => cb(data.tools));
        }
        break;
      case 'tools_updated':
        if (data.tools) {
          this.onToolsListeners.forEach(cb => cb(data.tools));
        }
        break;
      case 'confirmation_request':
        const req: ConfirmationRequest = {
          confirmationId: data.confirmation_id,
          toolName: data.tool_name,
          arguments: data.arguments || {},
          title: data.title || 'Confirmación de Acción Crítica',
          message: data.message || '¿Deseas permitir esta operación?',
          severity: data.severity || 'CRITICAL',
          target: data.target,
          details: data.details || {},
        };
        this.onConfirmationListeners.forEach(cb => cb(req));
        break;
      case 'pong':
        // Heartbeat respondido
        break;
      default:
        break;
    }
  }

  private startHeartbeat() {
    this.stopHeartbeat();
    this.pingInterval = window.setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 15000);
  }

  private stopHeartbeat() {
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

  private notifyStatus(status: 'CONNECTED' | 'DISCONNECTED' | 'CONNECTING') {
    this.onStatusListeners.forEach(cb => cb(status));
  }
}

// Instancia singleton compartida
export const wsService = new JarvisWebSocketClient();
