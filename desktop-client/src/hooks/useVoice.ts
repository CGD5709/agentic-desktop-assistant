import { useState, useEffect, useRef, useCallback } from 'react';
import { VoiceState, PttMode } from '../types';
import { audioFeedback } from '../services/audioFeedback';
import { speechRecognitionService } from '../services/speechRecognition';
import { speechSynthesisService } from '../services/speechSynthesis';

export interface UseVoiceOptions {
  hotkey?: string;
  pttMode?: PttMode;
  ttsVoiceURI?: string;
  ttsRate?: number;
  ttsPitch?: number;
  soundEffects?: boolean;
  onFinalTranscript?: (text: string) => void;
}

export function useVoice(options: UseVoiceOptions = {}) {
  const {
    hotkey = 'Numpad3',
    pttMode = 'hold',
    ttsVoiceURI = '',
    ttsRate = 1.05,
    ttsPitch = 1.0,
    soundEffects = true,
    onFinalTranscript
  } = options;

  const [voiceState, setVoiceState] = useState<VoiceState>('IDLE');
  const [audioLevel, setAudioLevel] = useState<number>(0);
  const [interimTranscript, setInterimTranscript] = useState<string>('');
  const [isSupported] = useState<boolean>(true);

  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const isKeyDownRef = useRef<boolean>(false);
  const currentVoiceStateRef = useRef<VoiceState>('IDLE');
  const accumulatedTranscriptRef = useRef<string>('');

  currentVoiceStateRef.current = voiceState;

  // Sync sound effects enabled state
  useEffect(() => {
    audioFeedback.setEnabled(soundEffects);
  }, [soundEffects]);

  // Audio level analyzer loop
  const startAudioAnalyzer = async () => {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        return;
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      mediaStreamRef.current = stream;

      const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const audioCtx = new AudioContextClass();
      audioContextRef.current = audioCtx;

      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.8;
      analyserRef.current = analyser;

      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const updateLevel = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);

        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        const avg = sum / dataArray.length;
        const normalized = Math.min(1, avg / 128);
        setAudioLevel(normalized);

        animationFrameRef.current = requestAnimationFrame(updateLevel);
      };

      updateLevel();
    } catch (err) {
      console.warn('[useVoice] Microfono no disponible para visualizador:', err);
    }
  };

  const stopAudioAnalyzer = () => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    setAudioLevel(0);
  };

  // Start listening (PTT active)
  const startListening = useCallback(() => {
    // If Jarvis is speaking, cancel immediately (Barge-in without breaking system state)
    if (speechSynthesisService.isSpeaking() || currentVoiceStateRef.current === 'SPEAKING') {
      speechSynthesisService.cancelSpeech();
    }

    accumulatedTranscriptRef.current = '';
    setInterimTranscript('');
    setVoiceState('LISTENING');

    if (soundEffects) {
      audioFeedback.playMicOpen();
    }

    startAudioAnalyzer();

    speechRecognitionService.start({
      onInterim: (text) => {
        setInterimTranscript(text);
      },
      onFinal: (text) => {
        accumulatedTranscriptRef.current = (accumulatedTranscriptRef.current + ' ' + text).trim();
        setInterimTranscript('');
      },
      onError: () => {
        // Recognition errors handled gracefully
      },
      onEnd: () => {
        // Will be finalized in stopListening
      }
    });
  }, [soundEffects]);

  // Stop listening and dispatch recorded command
  const stopListening = useCallback(() => {
    if (currentVoiceStateRef.current !== 'LISTENING') return;

    speechRecognitionService.stop();
    stopAudioAnalyzer();

    if (soundEffects) {
      audioFeedback.playMicClose();
    }

    setVoiceState('IDLE');

    // Give SpeechRecognition a moment to flush final results
    setTimeout(() => {
      const fullTranscript = accumulatedTranscriptRef.current.trim() || interimTranscript.trim();
      if (fullTranscript && onFinalTranscript) {
        onFinalTranscript(fullTranscript);
      }
      accumulatedTranscriptRef.current = '';
      setInterimTranscript('');
    }, 120);
  }, [soundEffects, interimTranscript, onFinalTranscript]);

  const toggleListening = useCallback(() => {
    if (voiceState === 'LISTENING') {
      stopListening();
    } else {
      startListening();
    }
  }, [voiceState, startListening, stopListening]);

  // Cancel speech synthesis locution
  const cancelSpeech = useCallback(() => {
    speechSynthesisService.cancelSpeech();
    if (voiceState === 'SPEAKING') {
      setVoiceState('IDLE');
    }
    if (soundEffects) {
      audioFeedback.playStopCue();
    }
  }, [voiceState, soundEffects]);

  // Speak assistant response with TTS
  const speak = useCallback((text: string, onEnd?: () => void) => {
    if (!text || !text.trim()) {
      onEnd?.();
      return;
    }

    setVoiceState('SPEAKING');

    speechSynthesisService.speak(text, {
      voiceURI: ttsVoiceURI,
      rate: ttsRate,
      pitch: ttsPitch,
      onStart: () => {
        setVoiceState('SPEAKING');
      },
      onEnd: () => {
        setVoiceState('IDLE');
        onEnd?.();
      },
      onError: () => {
        setVoiceState('IDLE');
        onEnd?.();
      }
    });
  }, [ttsVoiceURI, ttsRate, ttsPitch]);

  // Keyboard Hotkey Listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA')) {
        return;
      }

      if (e.code === hotkey) {
        e.preventDefault();

        if (pttMode === 'hold') {
          if (!isKeyDownRef.current) {
            isKeyDownRef.current = true;
            startListening();
          }
        } else {
          // Toggle mode
          toggleListening();
        }
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA')) {
        return;
      }

      if (e.code === hotkey && pttMode === 'hold') {
        e.preventDefault();
        isKeyDownRef.current = false;
        stopListening();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [hotkey, pttMode, startListening, stopListening, toggleListening]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      speechSynthesisService.cancelSpeech();
      speechRecognitionService.abort();
      stopAudioAnalyzer();
    };
  }, []);

  return {
    voiceState,
    setVoiceState,
    audioLevel,
    interimTranscript,
    isListening: voiceState === 'LISTENING',
    isSpeaking: voiceState === 'SPEAKING',
    startListening,
    stopListening,
    toggleListening,
    cancelSpeech,
    speak,
    isSupported: speechRecognitionService.isSupported() && isSupported
  };
}
