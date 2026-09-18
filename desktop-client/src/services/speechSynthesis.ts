/**
 * Speech Synthesis service wrapping Web Speech Synthesis API.
 * Handles queue management, OS voice discovery, and instant barge-in cancellation.
 */

export interface SpeakOptions {
  voiceURI?: string;
  rate?: number;
  pitch?: number;
  volume?: number;
  lang?: string;
  onStart?: () => void;
  onEnd?: () => void;
  onError?: (err: any) => void;
}

class SpeechSynthesisService {
  private synth: SpeechSynthesis | null = null;
  private voices: SpeechSynthesisVoice[] = [];
  private isSpeakingActive: boolean = false;

  constructor() {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      this.synth = window.speechSynthesis;
      this.loadVoices();
      if (this.synth.onvoiceschanged !== undefined) {
        this.synth.onvoiceschanged = () => this.loadVoices();
      }
    }
  }

  private loadVoices(): void {
    if (!this.synth) return;
    try {
      this.voices = this.synth.getVoices();
    } catch {
      this.voices = [];
    }
  }

  public isSupported(): boolean {
    return !!this.synth;
  }

  public getVoices(): SpeechSynthesisVoice[] {
    if (this.voices.length === 0 && this.synth) {
      this.loadVoices();
    }
    return this.voices;
  }

  public getSpanishVoices(): SpeechSynthesisVoice[] {
    const all = this.getVoices();
    return all.filter(v => v.lang.startsWith('es'));
  }

  public speak(text: string, options: SpeakOptions = {}): void {
    if (!this.synth) return;

    if (!text || !text.trim()) {
      options.onEnd?.();
      return;
    }

    // Cancel any previous active playback
    this.cancelSpeech();

    const utterance = new SpeechSynthesisUtterance(text.trim());
    utterance.rate = options.rate ?? 1.05;
    utterance.pitch = options.pitch ?? 1.0;
    utterance.volume = options.volume ?? 1.0;
    utterance.lang = options.lang ?? 'es-ES';

    // Find requested voice
    const voices = this.getVoices();
    if (options.voiceURI) {
      const selected = voices.find(v => v.voiceURI === options.voiceURI);
      if (selected) {
        utterance.voice = selected;
      }
    }

    // If no specific voice matched, prefer a natural Spanish voice
    if (!utterance.voice) {
      const defaultEs = voices.find(v => v.lang.includes('es') && (v.name.includes('Natural') || v.name.includes('Online') || v.name.includes('Google') || v.name.includes('Microsoft')));
      if (defaultEs) {
        utterance.voice = defaultEs;
      }
    }

    utterance.onstart = () => {
      this.isSpeakingActive = true;
      options.onStart?.();
    };

    utterance.onend = () => {
      this.isSpeakingActive = false;
      options.onEnd?.();
    };

    utterance.onerror = (e) => {
      this.isSpeakingActive = false;
      // 'interrupted' is expected when cancelSpeech is triggered
      if (e.error !== 'interrupted' && e.error !== 'canceled') {
        console.warn('[SpeechSynthesis] Utterance error:', e);
        options.onError?.(e);
      } else {
        options.onEnd?.();
      }
    };

    try {
      this.synth.speak(utterance);
    } catch (err) {
      console.warn('[SpeechSynthesis] Failed to trigger speech:', err);
      this.isSpeakingActive = false;
      options.onEnd?.();
    }
  }

  public cancelSpeech(): void {
    if (this.synth) {
      try {
        this.synth.cancel();
      } catch {
        // Ignored
      }
    }
    this.isSpeakingActive = false;
  }

  public isSpeaking(): boolean {
    return this.isSpeakingActive || (this.synth ? this.synth.speaking : false);
  }
}

export const speechSynthesisService = new SpeechSynthesisService();
