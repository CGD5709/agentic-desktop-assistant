# ADR-008: Cascaded Audio Transducers vs. Native End-to-End Multimodal Audio LLMs

## Context and Problem
The JARVIS assistant requires a bidirectional voice interface supporting low-latency speech input (Push-to-Talk) and vocal response generation (Text-to-Speech), while orchestrating multi-step system tools and maintaining local execution on consumer hardware.

Modern AI architectures offer two contrasting paradigms for voice interaction:
1. **End-to-End Multimodal Audio LLMs (Speech-to-Speech)**: Single monolithic models that ingest raw audio waveforms and directly emit audio tokens (e.g., GPT-4o Audio, Gemini Live, AudioPaLM).
2. **Cascaded Transducer Pipeline (Modular STT -> Text LLM -> Dual-Format Sanitizer -> TTS)**: Decoupled architecture using specialized speech-to-text transducers, text-based reasoning models, and dedicated speech synthesizers.

We must determine the voice pipeline topology that optimizes for local compute efficiency, sub-second latency, deterministic tool calling, and hardware resource utilization.

## Alternatives Considered

* **Native End-to-End Multimodal Audio LLM:**
  * *Pros:* Preserves acoustic nuances, prosody, emotional tone, and non-verbal speech cues in a single inference pass.
  * *Cons:* Prohibitive local compute requirements (demands 16GB–24GB+ dedicated VRAM for continuous audio token encoding/decoding); high VRAM contention starving ChromaDB vector stores and local agent graphs; unpredictable hallucinations during structured tool-calling arguments; lacks visual Markdown separation for hybrid chat HUDs.
* **Cascaded Modular Transducer Pipeline (Selected):**
  * *Pros:* Maximum computational efficiency; speech recognition and synthesis run on native client OS/Web Audio subsystems with zero VRAM consumption; 100% of GPU compute remains allocated to local text LLM reasoning (`qwen2.5:7b`); deterministic tool execution with strict JSON Schema validation; enables dual-channel output payload (`content` for rich visual Markdown, `speech_text` for phonetically fluent speech); instant sub-millisecond client-side cancellation (*Barge-in*).
  * *Cons:* Loss of emotional audio prosody passing into the LLM; slight pipeline boundary serialization.

## Decision
We chose the **Cascaded Modular Transducer Pipeline** across the frontend and reasoning engine:
1. **Input Transduction (STT)**: Client-side Speech Recognition API captures microphone streams with real-time interim transcription, operating with near-zero latency and zero backend GPU load.
2. **Cognitive Reasoning**: The Python Reasoning Engine consumes plain text transcripts and executes LangGraph DAG routing, memory retrieval, and RabbitMQ tool execution.
3. **Dual-Channel Output Sanitization**: A specialized voice sanitizer ([`voice_cleaner.py`](../../reasoning-engine/agent/voice_cleaner.py)) cleans raw Markdown, code blocks, tables, and emojis from the LLM output to produce a natural `speech_text` payload alongside the full visual `content`.
4. **Output Synthesis (TTS)**: Client-side Speech Synthesis API reproduces `speech_text` using native operating system neural voices, providing instant abort capabilities (`cancelSpeech()`) upon user interruption.
5. **System Audio Control**: A dedicated Java tool ([`SystemAudioTool.java`](../../execution-service/src/main/java/com/agentic/execution_service/tools/SystemAudioTool.java)) manages Windows master volume and mute state via native CoreAudio COM interfaces.

## Justification
Running an end-to-end multimodal audio model locally on consumer hardware would saturate available GPU VRAM, introduce 2–4s time-to-first-audio latency, and compromise tool-calling reliability.
By decoupling audio transduction to native client engines:
* Inference hardware is fully reserved for cognitive reasoning and deterministic tool calling.
* The frontend HUD achieves immediate visual feedback (<10ms) and fluid Push-to-Talk UX.
* The system cleanly separates rich visual Markdown formatting from natural, conversational speech dialogue.
* The user can instantly silence the assistant (*Barge-in*) or abort long-running tasks without tearing down complex audio websocket streams.

## Consequences
* **Positive:** Sub-second latency; zero backend VRAM overhead for voice processing; deterministic tool-calling precision; seamless barge-in interruption; clean separation between visual rendering and vocal narration.
* **Negative:** Voice input does not retain pitch or emotional prosody in the LLM context; client must support browser/desktop Web Speech APIs or fallback audio streaming.
