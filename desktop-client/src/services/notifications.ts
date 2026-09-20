/**
 * Windows / Desktop Notification Service utilizing Web Notifications API.
 */

export class NotificationService {
  private static instance: NotificationService;

  private constructor() {
    this.requestPermission();
  }

  public static getInstance(): NotificationService {
    if (!NotificationService.instance) {
      NotificationService.instance = new NotificationService();
    }
    return NotificationService.instance;
  }

  /**
   * Check if Notifications API is supported in the current environment.
   */
  public isSupported(): boolean {
    return 'Notification' in window;
  }

  /**
   * Request permission from the user for desktop notifications.
   */
  public async requestPermission(): Promise<NotificationPermission> {
    if (!this.isSupported()) {
      return 'denied';
    }

    if (Notification.permission === 'default') {
      try {
        return await Notification.requestPermission();
      } catch (err) {
        console.warn('[NotificationService] Error solicitando permisos de notificación:', err);
        return 'denied';
      }
    }

    return Notification.permission;
  }

  /**
   * Send a native Windows / Desktop notification.
   * If the user clicks the notification, focus the browser/client window.
   */
  public sendNotification(
    title: string,
    options?: {
      body?: string;
      icon?: string;
      tag?: string;
      requireInteraction?: boolean;
    }
  ): Notification | null {
    if (!this.isSupported()) {
      return null;
    }

    if (Notification.permission !== 'granted') {
      this.requestPermission();
      return null;
    }

    try {
      const notification = new Notification(title, {
        body: options?.body,
        icon: options?.icon || undefined,
        tag: options?.tag || 'jarvis-hitl-alert',
        requireInteraction: options?.requireInteraction ?? true,
      });

      notification.onclick = () => {
        window.focus();
        notification.close();
      };

      return notification;
    } catch (err) {
      console.warn('[NotificationService] Fallo al despachar notificación:', err);
      return null;
    }
  }
}

export const notificationService = NotificationService.getInstance();
