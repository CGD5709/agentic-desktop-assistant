# ADR-009: Human-in-the-Loop Safeguard Architecture for Critical OS Tools

## Context and Problem
The JARVIS Agentic Desktop Assistant is capable of executing operating system-level commands, such as terminating processes, scanning ports, and managing host resources.
Direct, autonomous execution of destructive, irreversible, or high-impact actions by the LLM without human oversight poses substantial security, stability, and data-loss risks (e.g., terminating user applications with unsaved work or killing critical background processes not covered by static blacklists).

The challenge is to implement a robust **Human-in-the-Loop (HITL)** authorization mechanism that:
1. Keeps the Java Execution Service as the single source of truth for tool criticality and confirmation semantics.
2. Intercepts critical tool executions before any AMQP execution message is dispatched to the OS runtime.
3. Operates non-blockingly within the asynchronous Python event loop.
4. Delivers an immediate interactive HUD modal to the user while also dispatching native OS background notifications when the user is working in another application.

## Alternatives Considered

* **Alternative 1: Unrestricted Autonomous Execution with Static Blacklists Only**
  * *Pros:* Fully autonomous, zero UI latency, no state synchronization required.
  * *Cons:* Severe safety risk as said before; LLMs can hallucinate PIDs or process names, causing accidental data loss or unexpected application termination.
* **Alternative 2: Synchronous Execution Blocker inside the Java Execution Service**
  * *Pros:* Centralizes enforcement directly at the OS command execution site.
  * *Cons:* Blocks AMQP consumer threads, risks broker channel timeouts, creates tight coupling between the backend runtime and frontend UI, and pollutes the low-level worker with interactive state.
* **Alternative 3: Distributed Schema-Driven Human-in-the-Loop (HITL) Interception in the Cognitive Layer with Multi-Surface Telemetry**
  * *Pros:* 
    * Execution-service declares `critical: boolean` and optional `confirmationTemplate` during discovery broadcast, adhering to the Open-Closed Principle.
    * Reasoning-engine `ActionNode` intercepts critical calls *before* RabbitMQ dispatch, generating dynamic parameter-interpolated confirmation prompts without per-tool `if` branches.
    * An asynchronous promise manager (`ConfirmationManager`) suspends execution cleanly on the event loop without blocking CPU threads.
    * The frontend HUD displays a modal with keyboard shortcuts (<kbd>Enter</kbd>/<kbd>Esc</kbd>) and triggers native OS desktop notifications when the window is unfocused.
    * If rejected, the execution request is aborted cleanly in the cognitive graph without emitting any message to the execution queue.
  * *Cons:* Requires active WebSocket connectivity between the frontend client and the reasoning engine to resolve confirmation requests.

## Decision
We implemented **Alternative 3: Distributed Schema-Driven Human-in-the-Loop Interception**:
1. **Execution Service**: `AgentTool` defines `default boolean isCritical() { return false; }` and `default String getConfirmationTemplate() { return null; }`. These properties are broadcast in `ToolRegistryPayload`.
2. **Reasoning Engine**:
   - `services.rabbitmq_listener` ingests and stores `critical` flags and templates in dynamic tool metadata.
   - `services.confirmation_manager.ConfirmationManager` manages transient `asyncio.Future` promises keyed by unique `correlation_id`s.
   - `agent.hitl.generate_confirmation_context` formats human-friendly confirmation summaries using schema interpolation or fallback parameter tables.
   - `agent.nodes.action.ActionNode` checks if the target tool is critical; if so, it broadcasts a `confirmation_request` over WebSocket and awaits user authorization. If approved, it dispatches the RPC via RabbitMQ; if rejected, it emits a cancellation `ToolMessage` directly to the cognitive state.
   - `api.websockets` validates incoming `confirmation_response` frames and resolves the corresponding future.
3. **React Desktop Client**:
   - `ConfirmationModal` renders a cybernetic HUD overlay with tool parameters, human-readable confirmation prompts, and keyboard shortcuts (<kbd>Enter</kbd> to confirm, <kbd>Escape</kbd> to cancel).
   - `NotificationService` leverages the Web Notifications API to trigger Windows desktop notifications when a confirmation request arrives while the assistant window is minimized or unfocused.

## Justification
* **Defense in Depth**: Prevents unvetted execution of destructive actions at the cognitive gateway before any message enters `execution_service_queue`.
* **Zero Thread Contention**: Utilizes `asyncio.Future` non-blocking promises, allowing the Python event loop to continue serving pings, status updates, and other non-critical operations.
* **Extensible & Schema-Driven**: Adding a new critical tool in Java requires only declaring `isCritical() = true` and defining a template; no Python or frontend code changes are needed.
* **Omnipresent User Awareness**: Background Windows notifications ensure users are alerted immediately even when multitasking.

## Consequences
* **Positive:** Complete protection against unauthorized or accidental destructive OS operations; zero message queue pollution on rejected actions; rich contextual feedback across both HUD and native OS notifications; clean architectural separation across microservice boundaries.
* **Negative:** Critical tool execution relies on frontend client availability to receive authorization; turns involving critical tools remain paused until the user interacts with the prompt.
