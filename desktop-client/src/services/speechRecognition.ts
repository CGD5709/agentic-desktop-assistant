/**
 * Speech Recognition service wrapping Web Speech Recognition API.
 * Provides continuous/transient speech-to-text with interim preview.
 */

// Typing for Web Speech API
interface IWindowSpeechRecognition extends Window {
  SpeechRecognition?: any;
  webkitSpeechRecognition?: any;
}

export interface RecognitionCallbacks {
  onInterim?: (text: string) => void;
  onFinal?: (text: string) => void;
  onError?: (error: string) => void;
  onEnd?: () => void;
}

class SpeechRecognitionService {
  private recognition: any = null;
  private isListening: boolean = false;
  private currentLanguage: string = 'es-ES';
  private callbacks: RecognitionCallbacks = {};

  constructor() {
    this.initRecognition();
  }

  private initRecognition(): void {
    const win = window as unknown as IWindowSpeechRecognition;
    const SpeechRecognitionClass = win.SpeechRecognition || win.webkitSpeechRecognition;

    if (!SpeechRecognitionClass) {
      return;
    }

    try {
      this.recognition = new SpeechRecognitionClass();
      this.recognition.continuous = true;
      this.recognition.interimResults = true;
      this.recognition.lang = this.currentLanguage;
      this.recognition.maxAlternatives = 1;

      this.recognition.onresult = (event: any) => {
        let interimText = '';
        let finalText = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalText += transcript;
          } else {
            interimText += transcript;
          }
        }

        if (interimText && this.callbacks.onInterim) {
          this.callbacks.onInterim(interimText.trim());
        }

        if (finalText && this.callbacks.onFinal) {
          this.callbacks.onFinal(finalText.trim());
        }
      };

      this.recognition.onerror = (event: any) => {
        // 'no-speech' or 'aborted' are non-critical during user interaction
        if (event.error !== 'no-speech' && event.error !== 'aborted') {
          console.warn('[SpeechRecognition] Error encountered:', event.error);
          this.callbacks.onError?.(event.error);
        }
      };

      this.recognition.onend = () => {
        this.isListening = false;
        this.callbacks.onEnd?.();
      };
    } catch (err) {
      console.warn('[SpeechRecognition] Initialization failed:', err);
      this.recognition = null;
    }
  }

  public isSupported(): boolean {
    const win = window as unknown as IWindowSpeechRecognition;
    return !!(win.SpeechRecognition || win.webkitSpeechRecognition);
  }

  public setLanguage(lang: string): void {
    this.currentLanguage = lang;
    if (this.recognition) {
      this.recognition.lang = lang;
    }
  }

  public start(callbacks: RecognitionCallbacks): boolean {
    if (!this.recognition) {
      this.initRecognition();
      if (!this.recognition) return false;
    }

    if (this.isListening) {
      try {
        this.recognition.abort();
      } catch {
        // Ignored
      }
    }

    this.callbacks = callbacks;
    try {
      this.recognition.lang = this.currentLanguage;
      this.recognition.start();
      this.isListening = true;
      return true;
    } catch (err) {
      console.warn('[SpeechRecognition] Failed to start:', err);
      this.isListening = false;
      return false;
    }
  }

  public stop(): void {
    if (this.recognition && this.isListening) {
      try {
        this.recognition.stop();
      } catch {
        // Ignored
      }
    }
    this.isListening = false;
  }

  public abort(): void {
    if (this.recognition) {
      try {
        this.recognition.abort();
      } catch {
        // Ignored
      }
    }
    this.isListening = false;
  }
}

export const speechRecognitionService = new SpeechRecognitionService();
