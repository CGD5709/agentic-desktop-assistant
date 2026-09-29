# JARVIS System Architecture Specification

## 1. Executive Summary & System Vision

**JARVIS** is an enterprise-grade, distributed desktop assistant engineered to execute autonomous cognitive reasoning, local operating system automation, intelligent workspace telemetry, and voice-assisted workflow execution on Windows host systems.

The architecture is governed by strict **Microservices Separation of Concerns**, **Clean Architecture**, and **Asynchronous Message-Driven Coordination**. By isolating high-level probabilistic reasoning (Python/LLM) from low-level deterministic operating system mutation (Java/Spring Boot) and rich user presentation (React/TypeScript), JARVIS provides strong reliability, sandboxed execution boundaries, zero process collision, and sub-second voice/HUD response latency.

---

## 2. Architectural Principles & Quality Attributes

1. **Polyglot Isolation of Concerns**:
   * *Cognitive Reasoning & Memory*: Python 3.11 with LangGraph and ChromaDB excels at vector manipulation, prompt graph topologies, and conversational AI.
   * *OS Automation & Deterministic Drivers*: Java 21 with Spring Boot provides robust type safety, robust subprocess isolation, connection pooling, and multi-threaded throughput.
   * *HUD Presentation*: React 18 with TypeScript and Vite provides hardware-accelerated Web Audio/Speech integration, glassmorphism aesthetics, and real-time state visualization.
2. **Asynchronous Message-Driven Coordination**:
   * All inter-service commands and data transfers between the cognitive core and execution subsystem occur over a high-throughput RabbitMQ message bus using asynchronous Remote Procedure Calls (RPC) with explicit correlation identifiers.
3. **Zero-Trust Host Execution with Human-in-the-Loop (HITL)**:
   * Non-idempotent or destructive actions (such as process termination, system modifications, or email transmission) require explicit interactive user authorization via the Desktop Client before OS execution.
4. **Resilient Four-Tier Memory**:
   * Retains user preferences, working dialogue context, and long-term semantic knowledge without blocking foreground inference turns or exhausting model context windows.

---

## 3. C4 Architecture Blueprint

### 3.1 C4 Level 1: System Context Diagram

```mermaid
flowchart TD
    User(["User (Operator)"])

    subgraph System_Boundary ["JARVIS Agentic Desktop Assistant System Boundary"]
        JARVIS["JARVIS Desktop Assistant<br/><i>(HUD, Cognitive Engine, Execution Subsystem)</i>"]
    end

    subgraph Host_Environment ["Local Host Environment & Cloud Services"]
        WindowsOS["Windows Operating System<br/><i>(Process Management, Filesystem, Audio APIs)</i>"]
        OllamaEngine["Ollama Server (Local)<br/><i>(qwen2.5:7b & nomic-embed-text)</i>"]
        MailServices["Email Providers<br/><i>(Gmail IMAP/SMTP & Microsoft Graph API)</i>"]
    end

    User <== "Voice (PTT / STT / TTS)<br/>Keyboard & HUD Interaction" ==> JARVIS
    JARVIS <== "Local Inference & Embeddings" ==> OllamaEngine
    JARVIS <== "System Process & Shell Management" ==> WindowsOS
    JARVIS <== "Fetch Unread & Send Approved Emails" ==> MailServices

    classDef userStyle fill:#0284c7,stroke:#0369a1,stroke-width:2px,color:#ffffff;
    classDef systemStyle fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#f8fafc;
    classDef extStyle fill:#1e293b,stroke:#64748b,stroke-width:1px,color:#f8fafc;

    class User userStyle;
    class JARVIS systemStyle;
    class WindowsOS,OllamaEngine,MailServices extStyle;
```

---

### 3.2 C4 Level 2: Container Diagram (Distributed Microservices)

```mermaid
flowchart TB
    User(["User"])

    subgraph Presentation_Container ["desktop-client (React 18 / TypeScript / Vite)"]
        UI_HUD["Cybernetic HUD & Chat Panel<br/><code>ArcReactorHUD | ChatPanel | TasksPanel</code>"]
        EmailDeck["Email Review Deck<br/><code>EmailReviewDeck.tsx</code>"]
        VoiceSubsystem["Voice Controller<br/><code>useVoice | Web Audio Analyser | Web Speech</code>"]
        WS_Client["WebSocket Client<br/><code>websocket.ts</code>"]
    end

    subgraph Cognitive_Container ["reasoning-engine (Python 3.11 / FastAPI)"]
        WS_Server["WebSocket Dispatcher<br/><code>api/websockets.py</code>"]
        LangGraph["LangGraph State Engine<br/><code>RouterNode | CommandNode | ActionNode | SummarizeNode</code>"]
        EmailAssistant["EmailAssistantService<br/><i>5-Category Classifier & Draft Drafter</i>"]
        MemoryTiers["4-Tier Memory Engine<br/><code>ProfileStore | ChromaDB VectorStore | AsyncWorker</code>"]
        RMQ_Client["RabbitMQ RPC Client<br/><code>rabbitmq.py</code>"]
    end

    subgraph Messaging_Container ["Message Fabric (RabbitMQ Broker)"]
        Exchange["Topic Exchange: <code>agent_events</code>"]
        ExecQueue["Queue: <code>execution_service_queue</code>"]
    end

    subgraph Execution_Container ["execution-service (Java 21 / Spring Boot 3)"]
        Listener["ExecutionListener<br/><i>@RabbitListener</i>"]
        Broadcaster["ToolRegistryBroadcaster<br/><i>ApplicationReadyEvent</i>"]
        ToolManager["Tool Strategy Registry<br/><i>Spring DI Catalog</i>"]
        ProcessEngine["Process Execution Sandbox<br/><i>ProcessBuilder & Windows Native API</i>"]
        MailManager["EmailAccountManager<br/><i>JavaMail IMAP/SMTP & Graph SDK</i>"]
    end

    subgraph Storage_Container ["Local Storage & Inference"]
        OllamaServer["Ollama LLM Server<br/><code>http://localhost:11434</code>"]
        SQLiteDB[("SQLite Databases<br/><code>assistant_profile.db | agent_memory.db</code>")]
        ChromaDB[("ChromaDB Vector Store<br/><code>/data/chroma_db</code>")]
    end

    User <== "Push-to-Talk / Audio Output / Click" ==> UI_HUD
    UI_HUD --> VoiceSubsystem
    UI_HUD --> EmailDeck
    UI_HUD <--> WS_Client

    WS_Client <== "Full-Duplex WS Protocol<br/>(JSON Tagged-Union: ws://localhost:8000/ws)" ==> WS_Server
    WS_Server <== "ainvoke(AgentState)" ==> LangGraph
    LangGraph <--> EmailAssistant
    LangGraph <--> MemoryTiers
    MemoryTiers <--> SQLiteDB
    MemoryTiers <--> ChromaDB
    LangGraph <== "Chat / Embeddings HTTP" ==> OllamaServer
    EmailAssistant <== "Classification HTTP" ==> OllamaServer

    LangGraph <== "Asynchronous RPC Request" ==> RMQ_Client
    RMQ_Client <== "AMQP 0-9-1" ==> Exchange
    Exchange --> ExecQueue
    ExecQueue --> Listener
    Broadcaster -- "Publish Dynamic Tools" --> Exchange
    Listener --> ToolManager
    ToolManager --> ProcessEngine
    ToolManager --> MailManager
    Listener -- "Publish RPC Result" --> Exchange
    Exchange -- "tool.response.*" --> RMQ_Client

    classDef uiStyle fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#f8fafc;
    classDef cogStyle fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#f8fafc;
    classDef msgStyle fill:#431407,stroke:#f97316,stroke-width:2px,color:#f8fafc;
    classDef execStyle fill:#14532d,stroke:#22c55e,stroke-width:2px,color:#f8fafc;
    classDef dbStyle fill:#18181b,stroke:#64748b,stroke-width:1px,color:#f8fafc;

    class UI_HUD,EmailDeck,VoiceSubsystem,WS_Client uiStyle;
    class WS_Server,LangGraph,EmailAssistant,MemoryTiers,RMQ_Client cogStyle;
    class Exchange,ExecQueue msgStyle;
    class Listener,Broadcaster,ToolManager,ProcessEngine,MailManager execStyle;
    class OllamaServer,SQLiteDB,ChromaDB dbStyle;
```

---

## 4. Subsystem Specifications

### 4.1 Presentation Layer (`desktop-client`)
* **Framework**: React 18, TypeScript, Vite.
* **Component Hierarchy**:
  * `App.tsx`: Central coordinator managing active tabs, WebSocket event dispatching, global hotkeys, and voice lifecycles.
  * `HeaderHUD.tsx`: System telemetry (online/offline status, connected tools counter, digital clock, microphone mode indicator).
  * `ChatPanel.tsx`: Resizable conversation log supporting Markdown formatting, streaming interim transcripts, and dynamic Stop/Send controls.
  * `EmailReviewDeck.tsx`: Central interactive canvas displaying unread emails, category badges, RFC-822 verified recipients, AI draft generation, real-time draft editing, and one-click dispatch.
  * `ArcReactorHUD.tsx`: Concentric orbital holographic reactor visualizing 4 assistant states (`IDLE`, `LISTENING`, `THINKING`, `SPEAKING`).
  * `ConfirmationModal.tsx`: High-contrast modal intercepting critical tool calls for user authorization.
  * `SettingsView.tsx`: User configuration view for voice synthesis selection, PTT modes, model parameters, and hotkey bindings.

---

### 4.2 Cognitive Core (`reasoning-engine`)
* **State Machine Topology**: Directed acyclic graph (DAG) constructed using LangGraph with an `AsyncSqliteSaver` checkpointer.
* **Nodes**:
  1. `RouterNode`: Evaluates user intent using semantic classification (`CHAT` vs `COMMAND`). If `COMMAND`, queries `VectorMemoryStore` for relevant semantic memories.
  2. `ChatNode`: Generates polite, natural conversational responses without technical tool invocation.
  3. `CommandNode`: Discovers registered tools dynamically and invokes structured tool calls matching user intent.
  4. `ActionNode`: Intercepts critical tools for Human-in-the-Loop confirmation, executes non-blocking RPC across RabbitMQ, and dispatches unread email lists and drafts to the frontend.
  5. `SummarizeNode`: Translates raw tool execution output into concise conversational responses, concluding email reviews with clear reminders regarding the central application deck.
* **Memory Subsystem**:
  * **Tier 0 (ProfileStore)**: Relational SQLite storage for user personal data and configuration.
  * **Tier 1 (Working Memory)**: Token-budgeted dialogue buffer using `tiktoken`.
  * **Tier 2 (VectorMemoryStore)**: ChromaDB semantic vector store using cosine similarity over `nomic-embed-text` embeddings.
  * **Tier 3 (AsyncMemoryManager)**: Asynchronous background memory extractor operating on a 45-second debounce worker.

---

### 4.3 Execution Subsystem (`execution-service`)
* **Framework**: Java 21, Spring Boot 3.4.
* **Key Components**:
  * `ToolRegistry`: In-memory strategy registry populated on startup via Spring component scanning (`AgentTool` interface).
  * `ToolRegistryBroadcaster`: Publishes tool definitions and parameter JSON Schemas to `system.discovery.execution_service` upon `ApplicationReadyEvent`.
  * `ExecutionListener`: `@RabbitListener` consuming from `execution_service_queue` matching `tool.request.*`.
  * `ProcessEngine`: Sandboxed execution of host processes with hard execution timeouts (default: 30s) and infrastructure termination blacklists.
  * `EmailAccountManager`: Multi-provider email management engine supporting Gmail IMAP/SMTP and Microsoft 365 Graph REST API.

---

## 5. Security & Human-in-the-Loop Safeguards

```mermaid
sequenceDiagram
    autonumber
    participant User as Operator
    participant Client as Desktop Client
    participant Engine as Reasoning Engine
    participant Broker as RabbitMQ Broker
    participant Exec as Execution Service

    Engine->>Engine: Evaluates LLM tool call (e.g. "matar_proceso")
    Engine->>Engine: Checks tool criticality flag (critical == true)
    Engine->>Client: Broadcasts confirmation_request (WebSocket)
    Client->>Client: Displays ConfirmationModal (HUD Alert + Tone)
    
    alt User Approves (Click / Enter)
        User->>Client: Authorizes execution
        Client->>Engine: confirmation_response (confirmed: true)
        Engine->>Broker: Dispatches tool.request.<toolName> (AMQP)
        Broker->>Exec: Consumes request
        Exec->>Exec: Validates arguments against blacklists
        Exec->>Exec: Executes OS subprocess
        Exec->>Broker: Publishes tool.response.<toolName>
        Broker->>Engine: Resolves asynchronous RPC Future
        Engine->>Client: Returns conversational confirmation
    else User Rejects / Escape / Timeout
        User->>Client: Denies authorization
        Client->>Engine: confirmation_response (confirmed: false)
        Engine->>Engine: Aborts execution without dispatching AMQP message
        Engine->>Client: Confirms operation cancellation in Chat
    end
```

---

## 6. Resilience & Fault Tolerance

1. **Broker Reconnection & Offline Readiness**:
   * If RabbitMQ is unavailable during startup, both `reasoning-engine` and `execution-service` log clear warnings and continue operating local memory and API surfaces without crashing.
   * `desktop-client` auto-reconnects to WebSockets with exponential backoff.
2. **Deterministic RPC Future Resolution**:
   * All AMQP messages carry a unique `correlationId`. Unmatched or timed-out responses are cleanly rejected after 30 seconds without hanging Python event loops.
3. **Dead Letter Queue (DLQ) Poison Pill Isolation**:
   * Malformed payloads or unhandled runtime exceptions are routed to `agent_events.dlq` without blocking the main execution queue.
