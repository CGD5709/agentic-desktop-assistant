# ADR-005: Dynamic Tool Discovery via Registry Broadcast and Strategy Pattern

## Context and Problem
The Python reasoning engine requires tool descriptors and JSON Schema definitions to configure tool-calling capabilities in the LLM.
The Java execution service hosts the actual operating system commands, input sanitization rules, and process blacklists.
Hardcoding tool schemas in Python tightly couples the cognitive layer to the execution runtime, requiring coordinated code edits and redeployments whenever an OS tool is added or modified.

## Alternatives Considered
* **Hardcoded Python Tool Definitions:** Define all tool signatures and parameters directly in Python LangChain classes.
  * *Pros:* Static analysis and IDE autocompletion in Python; simple initial setup.
  * *Cons:* Severe cross-service coupling; adding an OS capability in Java requires modifying and restarting the Python service; high risk of schema drift.
* **Shared Static Schema Repository:** Store JSON Schema definitions in a shared repository or submodule consumed at build time.
  * *Pros:* Clear documentation; schemas are decoupled from execution code.
  * *Cons:* Requires coordinated build pipelines; discrepancies emerge if deployed services run different schema versions than runtime code.
* **Dynamic Discovery via Registry Broadcast and Strategy Pattern:** Discover tools at runtime over the message bus, resolving execution through polymorphic strategies.
  * *Pros:* Java is the single source of truth for OS capabilities; new tools are registered with zero Python code changes; adheres to the Open-Closed Principle.
  * *Cons:* Runtime initialization ordering dependency; Python must handle periods where tool schemas have not yet been broadcast over the broker.

## Decision
We implemented dynamic tool discovery using the Town Crier pattern over RabbitMQ, backed by Inversion of Control (IoC) and the Strategy pattern in Java.
Each tool in the execution service implements the `AgentTool` interface and is registered as a Spring `@Component`.
On startup (`ApplicationReadyEvent`), `ToolRegistryBroadcaster` aggregates all injected `AgentTool` beans, serializes their schemas into a `ToolRegistryPayload`, and broadcasts the manifest to exchange `agent_events` with routing key `system.discovery.execution_service`.
Inbound execution requests are dispatched by `ExecutionListener` directly to the matching `AgentTool` strategy from an in-memory registry map, avoiding switch statements.
The Python reasoning engine listens for this discovery broadcast and dynamically supplies the received schemas to `ChatOllama.bind_tools()`.

## Justification
The execution service is the only component with direct knowledge of operating system constraints, parameter boundaries, and security blacklists.
The Strategy pattern allows engineers to introduce new OS automation tools simply by implementing `AgentTool` and annotating the class with `@Component`, leaving dispatching and messaging infrastructure untouched.
Dynamic discovery eliminates the need to redeploy or reconfigure the Python reasoning engine when extending OS management capabilities.

## Consequences
* **Positive:** Zero Python code changes required when introducing new OS tools; clean architectural decoupling; single source of truth for tool validation schemas and safety constraints.
* **Negative:** If Python boots and processes a command before the Java broadcast arrives, tools are unavailable until the broadcast completes; schema validation bugs can only be caught at runtime.
