# JARVIS Desktop Client (React + TypeScript HUD)

The **Desktop Client** is the interactive presentation layer and Heads-Up Display (HUD) for the JARVIS Agentic Desktop Assistant. Built with React 18, TypeScript, and Vite, it delivers a high-contrast cybernetic HUD aesthetic with low-latency bidirectional voice interaction, real-time telemetry, full-duplex WebSocket communication, and an interactive central canvas for email review and supervised AI reply drafting.

---

## 1. Core Features & Capabilities

### 1.1 Bidirectional Voice Subsystem (STT and TTS)
* **Push-to-Talk (PTT)**:
  * **Hold-to-Talk Mode**: Capture audio while holding the configured global hotkey (default: `NUMPAD 3`) or the on-screen microphone button; releasing automatically finalizes and dispatches the prompt.
  * **Toggle Mode**: A single keypress opens the audio channel; a second keypress closes and sends the transcribed text.
* **Instant Speech Recognition (STT)**: Powered by [`speechRecognition.ts`](src/services/speechRecognition.ts) using the Web Speech Recognition API with real-time interim streaming preview.
* **Operating System Speech Synthesis (TTS)**: Powered by [`speechSynthesis.ts`](src/services/speechSynthesis.ts) with dynamic host OS voice discovery, adjustable speech rate and pitch, and live preview testing.
* **Seamless Barge-in Interruption**: Activating the microphone while Jarvis is speaking immediately silences vocal playback without corrupting background tasks.
* **Procedural HUD Sound FX**: [`audioFeedback.ts`](src/services/audioFeedback.ts) generates acoustic feedback cues (Mic Open, Mic Close, Action Done, Stop) using native `Web Audio API` oscillators without external audio asset dependencies.

### 1.2 State-Aware Stop Controller (Dynamic Abort Interface)
* Displays a **Send** icon (`Send`) when the assistant is in the `IDLE` state.
* Dynamically transforms into an amber/red **Square Stop Button** (`Square`) when the engine is in `THINKING` or `SPEAKING` state.
* Clicking the Stop button immediately aborts local speech synthesis and dispatches a non-blocking `stop` cancellation signal to the Python LangGraph orchestrator.

### 1.3 Central Interactive Canvas & Intelligent Email Review Deck
* **Dual-Mode Central Area**: Seamlessly switches between the holographic Arc Reactor HUD and the interactive [`EmailReviewDeck.tsx`](src/components/EmailReviewDeck.tsx) when unread emails are ingested.
* **Carousel & Step Navigation**:
  * Step indicators (*Correo 1 de N*) and navigation buttons (*Anterior*, *Siguiente*, *Pasar al siguiente correo*).
  * Direct clickable dots reflecting unread, drafted, or sent status.
* **RFC-822 Recipient Grounding Indicator**: Displays locked, verified sender and recipient data with cybernetic security badges to prevent recipient hallucination.
* **5-Category Smart Badges**: Visual indicators for `URGENT`, `UNIVERSITY`, `NOTIFICATION`, `NOT IMPORTANT`, and `SPAM`.
* **On-Demand AI Response Generation**:
  * Prominent **"GENERAR RESPUESTA CON IA"** action button.
  * Optional prompt customization drawer to supply custom reply directives before generation.
  * Animated pulsing loader during LLM drafting.
* **Live Editable Response Textarea**: Allows the operator to freely edit, refine, or rewrite the generated reply before approving.
* **Supervised One-Click Transmission**: Glowing **"APROBAR Y ENVIAR"** button executes physical dispatch via the Java execution service and automatically transitions to the next pending email.

### 1.4 Reactive Arc Reactor Visualizer
* Displays live state transitions in [`ArcReactorHUD.tsx`](src/components/ArcReactorHUD.tsx):
  * `IDLE`: Steady pulse and concentric orbital ring rotation.
  * `LISTENING`: Real-time audio frequency scaling driven by microphone input volume (`AnalyserNode`).
  * `THINKING`: High-speed core spin indicating cognitive reasoning and tool execution.
  * `SPEAKING`: Radiant vocal emission waves synchronized with speech playback.

### 1.5 Human-in-the-Loop (HITL) Safeguards & OS Notifications
* **Cybernetic Confirmation Modal**: When the reasoning engine intercepts a critical tool invocation, [`ConfirmationModal.tsx`](src/components/ConfirmationModal.tsx) presents a high-contrast HUD alert detailing the tool name, contextual message, and parameter table.
* **Keyboard Hotkeys**: Press <kbd>Enter</kbd> to authorize execution or <kbd>Escape</kbd> to cancel the operation immediately.
* **Background Windows Notifications**: [`notifications.ts`](src/services/notifications.ts) utilizes the Web Notifications API to trigger native Windows desktop alerts when a confirmation request arrives while the assistant window is minimized or in the background.

---

## 2. Directory Structure

```
desktop-client/
├── src/
│   ├── components/
│   │   ├── ArcReactorHUD.tsx       # Central holographic visualizer with 4-state audio telemetry
│   │   ├── ChatPanel.tsx           # Resizable chat log, interim speech banner, Stop controller
│   │   ├── ConfirmationModal.tsx   # Cybernetic Human-in-the-Loop authorization modal
│   │   ├── EmailReviewDeck.tsx     # Central unread email viewer & interactive AI response deck
│   │   ├── HeaderHUD.tsx           # System status telemetry, digital clock, quick mic toggle
│   │   ├── SettingsView.tsx        # OS voice picker, PTT mode toggle, rate/pitch sliders, sound FX
│   │   └── TasksPanel.tsx          # System diagnostics and active background task log
│   ├── hooks/
│   │   └── useVoice.ts             # Unified orchestrator for PTT, STT, TTS, Web Audio analysis, and hotkeys
│   ├── services/
│   │   ├── audioFeedback.ts        # Procedural Web Audio API sound cue synthesizer
│   │   ├── notifications.ts        # Web Notifications API service for Windows background alerts
│   │   ├── speechRecognition.ts    # Web Speech Recognition API wrapper (STT)
│   │   ├── speechSynthesis.ts      # Web Speech Synthesis API wrapper (TTS)
│   │   └── websocket.ts            # Full-duplex WebSocket client with heartbeat, email, and HITL signaling
│   ├── types.ts                    # TypeScript interfaces (EmailItem, EmailDraftData, VoiceState, AppSettings)
│   ├── App.tsx                     # Root component binding settings, voice pipeline, and HUD state
│   ├── main.tsx                    # React DOM entrypoint
│   └── index.css                   # HUD styling, glassmorphism, and neon CSS custom properties
├── index.html                      # HTML5 template with dark theme base
├── package.json                    # Dependencies and build scripts
└── vite.config.ts                  # Vite bundler configuration
```

---

## 3. Communication Protocol

The client maintains a persistent WebSocket connection to the Reasoning Engine at `ws://localhost:8000/ws`.

### Inbound Events to Backend
* `user_message`: Sends typed or voice-transcribed prompt (`{ "type": "user_message", "content": "..." }`).
* `email_action`: Dispatches draft generation, approval, or discard actions (`{ "type": "email_action", "action": "generate_draft" | "approve_and_send" | "discard_draft", ... }`).
* `confirmation_response`: Resolves pending authorization for critical tools (`{ "type": "confirmation_response", "confirmation_id": "...", "confirmed": true/false }`).
* `stop`: Cancels active reasoning graph or speech (`{ "type": "stop" }`).
* `clear_history`: Clears active conversation checkpoints in SQLite (`{ "type": "clear_history" }`).
* `ping`: Heartbeat probe dispatched periodically every 15 seconds.

### Outbound Events from Backend
* `connected`: Initial system handshake containing the loaded tool inventory.
* `status`: Updates assistant cognitive state (`THINKING` / `IDLE`).
* `unread_emails_list`: Delivers ingested unread emails array to mount `EmailReviewDeck`.
* `email_draft_view`: Delivers generated AI response draft for live editing.
* `email_draft_cleared`: Confirms draft discard.
* `confirmation_request`: Requests human authorization before running critical tools (`{ "type": "confirmation_request", "confirmation_id": "...", "tool_name": "...", "message": "...", ... }`).
* `assistant_message`: Delivers dual-payload response:
  * `content`: Rich Markdown for chat bubble rendering.
  * `speech_text`: Cleaned phonetic text for automatic TTS narration.

---

## 4. Development & Build

### Prerequisites
* **Node.js**: v18.0.0 or higher
* **npm**: v9.0.0 or higher

### Commands

```bash
# Install dependencies
npm install

# Start development server on http://localhost:5173
npm run dev

# Compile TypeScript and create production bundle in dist/
npm run build

# Preview production build locally
npm run preview
```
