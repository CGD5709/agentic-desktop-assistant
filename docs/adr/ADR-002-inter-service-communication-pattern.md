# ADR-002: Asynchronous RPC via Message Bus for Inter-Service Communication

## Context and Problem
The reasoning engine must dispatch execution requests to the Java execution service and receive results.
Operating system commands (such as process termination, network port scanning, or system metrics collection) have variable execution times ranging from milliseconds to several minutes.
Synchronous communication patterns block worker threads or exhaust connection pools while waiting for remote operating system operations to complete.

## Alternatives Considered
* **Synchronous HTTP REST:** The reasoning engine sends HTTP POST requests directly to Java REST endpoints.
  * *Pros:* Simple architecture; straightforward debugging using cURL; minimal setup.
  * *Cons:* Persistent socket connections risk timeouts during long OS tasks; client calls risk blocking the asyncio event loop under load; point-to-point coupling prevents message buffering during service restarts.
* **gRPC with Bidirectional Streaming:** Connect services using HTTP/2 and Protocol Buffers.
  * *Pros:* High throughput; binary serialization; strongly-typed contracts generated for Python and Java.
  * *Cons:* Complex connection lifecycle management; lack of built-in durable message buffering when a service restarts; high mocking complexity for unit testing.
* **Asynchronous RPC over Message Bus:** Route requests and responses asynchronously over an AMQP message broker.
  * *Pros:* Producers and consumers are decoupled; native message buffering during service downtime; non-blocking execution inside Python using event loop futures.
  * *Cons:* Requires managing message broker infrastructure; introduces asynchronous tracing complexity; requires tracking request-response correlation in application memory.

## Decision
We chose RabbitMQ as the central message bus and implemented an asynchronous RPC pattern over AMQP 0-9-1.
All communications pass through a durable topic exchange named `agent_events`.
Every message is encapsulated in an `EventEnvelope` containing metadata (`eventId`, `correlationId`, `timestamp`, `source`, `eventType`) and a typed payload.
In the Python engine, `send_and_wait` registers an `asyncio.Future` in an in-memory dictionary keyed by `correlationId`, publishes `EXECUTION_REQUEST`, and awaits the future without blocking the event loop.
The execution service processes requests from `execution_service_queue`, runs the tool, and returns `EXECUTION_RESPONSE` with identical correlation metadata.
Results and failures are mapped using `ToolExecutionResponsePayload` with explicit status indicators (`SUCCESS` or `ERROR`) and error codes (`INVALID_REQUEST`, `TOOL_NOT_FOUND`, `EXECUTION_ERROR`).

## Justification
Awaiting an `asyncio.Future` yields control to the asyncio event loop immediately, allowing FastAPI to process incoming user messages and WebSocket frames while OS operations run.
RabbitMQ durable queues (`durable=True`) preserve execution requests if the execution service restarts during processing.
The `EventEnvelope` standardizes distributed tracing through `correlationId` and isolates Pydantic field aliases (`snake_case`) from Java record naming (`camelCase`).
Standardized payload error structures allow the reasoning engine to handle tool errors programmatically without misinterpreting transport-level transport failures.

## Consequences
* **Positive:** The FastAPI event loop is never blocked by OS commands; messages are safely buffered during service restarts; end-to-end tracing is guaranteed across language boundaries via correlation IDs.
* **Negative:** RabbitMQ is an operational dependency that must run for the system to function; task cancellations must clean up the `pending_futures` dictionary to prevent memory leaks; debugging requires inspecting messages across distributed queue logs.
