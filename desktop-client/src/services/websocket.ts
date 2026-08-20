type StatusCallback = (status: 'CONNECTED' | 'DISCONNECTED' | 'CONNECTING') => void;
type MessageCallback = (content: string) => void;
type AssistantStatusCallback = (state: 'THINKING' | 'IDLE') => void;
type ToolsCallback = (tools: string[]) => void;

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

    this.shouldReconnect = true;
    this.notifyStatus('CONNECTING');

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.notifyStatus('CONNECTED');
        this.startHeartbeat();
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleIncomingMessage(data);
        } catch (err) {
          console.warn('[WS] Error parseando mensaje entrante:', err);
        }
      };

      this.ws.onclose = () => {
        this.stopHeartbeat();
        this.notifyStatus('DISCONNECTED');
        if (this.shouldReconnect) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (error) => {
        console.warn('[WS] Error de socket:', error);
        this.ws?.close();
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
      this.ws.close();
      this.ws = null;
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

  private handleIncomingMessage(data: any) {
    switch (data.type) {
      case 'assistant_message':
        this.onMessageListeners.forEach(cb => cb(data.content || ''));
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

  private notifyStatus(status: 'CONNECTED' | 'DISCONNECTED' | 'CONNECTING') {
    this.onStatusListeners.forEach(cb => cb(status));
  }
}

// Instancia singleton compartida
export const wsService = new JarvisWebSocketClient();
