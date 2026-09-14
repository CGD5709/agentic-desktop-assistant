# ADR-006: Inversion of Control Runtime Container and Bidirectional WebSocket State

## Context and Problem
The desktop frontend requires real-time visibility into agent execution states (`THINKING`, `IDLE`, error states) and conversational responses.
HTTP polling introduces high network overhead and latency, while unidirectional mechanisms like Server-Sent Events (SSE) require a separate HTTP POST channel for client messages.
The reasoning engine coordinates multiple stateful subsystems: a RabbitMQ connection, an SQLite profile store, a ChromaDB vector store, a background memory manager, and an SQLite checkpointer.
Relying on global singletons and import-time side effects (such as opening network sockets or creating SQLite databases on module import) causes connection leaks and breaks automated test isolation.

## Alternatives Considered
* **HTTP Polling with Global Module Singletons:** Frontend polls an API endpoint periodically; backend services initialize global singleton instances at import time.
  * *Pros:* Simple initial setup; no persistent socket connection required.
  * *Cons:* Polling introduces latency and unnecessary CPU overhead; import-time side effects trigger network and database connections during unit test discovery, causing test contamination.
* **Server-Sent Events (SSE) with Service Locator Pattern:** Frontend receives updates over SSE; components retrieve dependencies from a central static service locator.
  * *Pros:* Simple streaming over standard HTTP; native browser reconnection support.
  * *Cons:* Half-duplex communication requires separate HTTP requests to send user prompts; service locator obscures dependency graphs and preserves global mutable state.
* **Persistent WebSockets with Dependency Container Pattern:** Use full-duplex WebSockets for messaging and state notifications, encapsulating all subsystems within an injectable runtime container.
  * *Pros:* Real-time bidirectional communication over a single socket; zero import-time side effects; complete test isolation through explicit dependency injection.
  * *Cons:* Requires WebSocket connection handling and heartbeat ping-pong protocols; requires explicit plumbing of the runtime container through application layers.

## Decision
We adopted persistent WebSockets for client-server communication and implemented an explicit Dependency Container Pattern via `AgentRuntime`.
The WebSocket layer pushes status events (`{"type": "status", "state": "THINKING"}`) immediately upon receiving a prompt, streams back conversational responses (`assistant_message`), and returns to `IDLE` in a `finally` block once LangGraph execution completes.
All stateful services (message bus client, profile store, vector store, memory manager, session summarizer) are bundled into an `AgentRuntime` dataclass created via `create_agent_runtime` and mounted on `app.state`.
The LangGraph workflow is assembled via a pure factory function (`create_agent_graph`) that accepts runtime dependencies explicitly.
Service lifecycles are governed by FastAPI's asynchronous `lifespan` manager, calling `runtime.initialize()` on startup and `runtime.close()` on shutdown.

## Justification
Persistent WebSockets eliminate polling overhead and provide immediate visual feedback in the UI when the agent begins cognitive reasoning.
Encapsulating dependencies inside `AgentRuntime` ensures that importing the `agent` package executes zero network calls, creates no SQLite files, and spawns no background threads.
Automated unit tests can instantiate isolated runtimes with in-memory databases (`:memory:`) and mock RabbitMQ clients without cross-test state leakage.
Explicit lifecycle hooks in FastAPI guarantee that background memory tasks and database transactions are flushed cleanly to disk before the server process exits.

## Consequences
* **Positive:** Real-time UI updates reflecting agent reasoning states; zero import-time side effects; fully isolated, deterministic automated testing; clean resource disposal during process termination.
* **Negative:** The client must implement heartbeat tracking (`ping`/`pong`) and reconnection logic for network interruptions; developers must pass runtime instances explicitly rather than relying on global singletons.
