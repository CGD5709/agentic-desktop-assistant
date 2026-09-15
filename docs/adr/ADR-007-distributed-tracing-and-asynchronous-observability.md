# ADR-007: Distributed Tracing and Asynchronous Observability

## Context and Problem
In a polyglot microservices architecture composed of an AI reasoning engine (Python, FastAPI, LangGraph) and an operating system execution service (Java 21, Spring Boot), actions triggered by the LLM traverse multiple asynchronous boundaries (WebSocket $\rightarrow$ Graph State Machine $\rightarrow$ RabbitMQ Topic Exchange $\rightarrow$ Host OS Subprocesses $\rightarrow$ AMQP Response $\rightarrow$ WebSocket Stream).

When an execution error, security block, or operating system anomaly occurs, it is impossible to determine which user prompt or LLM cognitive turn originated the failure by inspecting decoupled terminal logs independently.

Furthermore, relying on unbuffered, blocking console output statements (`print()` in Python, `System.out.println()` / `System.err.println()` in Java) introduces thread synchronization locks and synchronous I/O overhead. This contention degrades the throughput and responsiveness of the `asyncio` event loop and AMQP message listener threads.

## Alternatives Considered
* **Unstructured Synchronous Print Statements:** Rely on standard `print` and `System.out.println` statements.
  * *Pros:* Zero architectural overhead; immediate local terminal output.
  * *Cons:* Blocks worker threads during I/O operations; lacks log level severity filtering; impossible to correlate events across distributed service consoles; high risk of leaking sensitive data.
* **Full OpenTelemetry / Jaeger Distributed Tracing Suite:** Deploy OpenTelemetry SDKs, agents, and a centralized trace collector (e.g., Jaeger or Zipkin).
  * *Pros:* Visual waterfall dependency graphs; automated distributed context propagation across diverse network protocols.
  * *Cons:* Excessive operational footprint and memory overhead; requires external daemon containers that unnecessarily complicate a desktop assistant designed for local host operation.
* **Correlated Message Envelopes with MDC, Async ContextVars, and Asynchronous Log Buffering:** Embed correlation identifiers in shared domain event envelopes, map them to native thread/coroutine contexts (Logback MDC in Java, `contextvars` in Python), and buffer log writes asynchronously via `AsyncAppender`.
  * *Pros:* Non-blocking I/O; zero additional infrastructure dependencies; deterministic end-to-end trace correlation from the UI to the host OS; full compatibility with SLF4J and Python standard logging.
  * *Cons:* Requires disciplined lifecycle management of diagnostic contexts (`MDC.put` / `MDC.remove` and `contextvars` cleanup).

## Decision
We decided to implement a lightweight, non-blocking distributed tracing and structured logging architecture across all services:

1. **Distributed Tracing via Correlated Envelopes:**
   * The reasoning engine generates a unique `correlationId` (UUID v4) upon receiving a user interaction via WebSocket.
   * This identifier is embedded within the `EventMetadata` of the `EventEnvelope` transmitted over RabbitMQ topic exchanges.
   * The Java execution service extracts the `correlationId` within [`ExecutionListener`](../../execution-service/src/main/java/com/agentic/execution_service/service/ExecutionListener.java) and injects it into SLF4J's **MDC (Mapped Diagnostic Context)**, ensuring every log statement executed on that worker thread carries the transaction context before clearing it in a `finally` block.

2. **Asynchronous Context Propagation in Python:**
   * Python coroutines manage request context through `contextvars.ContextVar` (`correlation_id_ctx`), bound automatically to log records via a custom `ContextLogFilter` in [`logger.py`](../../reasoning-engine/logger.py).

3. **Non-Blocking Asynchronous Appender (Java):**
   * Configured [`logback-spring.xml`](../../execution-service/src/main/resources/logback-spring.xml) with `ch.qos.logback.classic.AsyncAppender` wrapping the console appender. Log write operations are delegated to an internal bounded ring buffer (`queueSize=512`, `discardingThreshold=0`), shielding AMQP consumer threads from standard I/O latency.

4. **Structured Dual Formatting:**
   * Configured ANSI colorized formatting for local developer clarity, with an optional switch to structured JSON formatting for production log ingestion engines.

## Justification
* **End-to-End Cognitive Traceability:** A single correlation ID allows engineers to track the complete lifecycle of a Jarvis cognitive "thought"—from WebSocket ingestion and LangGraph routing to RabbitMQ RPC dispatch, Java tool execution in PowerShell, and the resulting response payload.
* **I/O Latency Shielding:** Offloading logging I/O to background daemon threads preserves the high-frequency message processing capacity of RabbitMQ listeners and the Python event loop.
* **Architectural Simplicity:** Eliminates the operational burden of running heavy observability backends while providing enterprise-grade diagnostic precision.

## Consequences
* **Positive:** Complete visibility into distributed execution paths; decoupled failure diagnosis; eliminated I/O thread contention; consistent log formatting and severity levels across Python and Java.
* **Negative:** Developers must ensure diagnostic contexts are properly set and cleared at thread/coroutine entry and exit points; in-memory log buffering consumes a minor, bounded heap allocation in the JVM.
