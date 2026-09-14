# ADR-004: Four-Tier Memory Architecture with Debounced Async Consolidation

## Context and Problem
An intelligent desktop assistant requires persistence across sessions, including fixed environment facts, active working context, and long-term semantic memories.
Executing information extraction and vector embedding generation synchronously on every user interaction saturates local GPU and CPU resources.
Synchronous memory updates introduce several seconds of latency per message, degrading conversational responsiveness.
Naive sliding-window truncation risks splitting atomic tool execution blocks (`AIMessage` tool calls and `ToolMessage` results), violating LangChain validation invariants.

## Alternatives Considered
* **Synchronous Per-Turn Extraction:** Parse and persist memories immediately during the inference cycle of each message.
  * *Pros:* Immediate consistency; extracted facts are queryable on the immediate next turn.
  * *Cons:* Adds 2 to 5 seconds of latency per turn; causes severe GPU inference contention on local models; degrades interactive chat responsiveness.
* **Ephemeral In-Memory History:** Keep conversational history purely in process memory without disk persistence.
  * *Pros:* Near-zero latency overhead; simple implementation.
  * *Cons:* Zero cross-session persistence; cannot retain long-term user preferences, project paths, or execution history.
* **Hierarchical Four-Tier Memory with Debounced Consolidation:** Separate memory storage into distinct physical layers and defer consolidation to user idle periods.
  * *Pros:* Zero GPU contention during active user interactions; clean separation between deterministic data and probabilistic vector search; protected message trimming.
  * *Cons:* Eventual consistency model; risk of losing unconsolidated buffer data if the process crashes during an active debounce window.

## Decision
We implemented a hierarchical four-tier memory architecture:
* **Tier 0 (Profile Store):** Asynchronous SQLite key-value storage (`ProfileStore`) for stable user preferences and environment paths, using atomic UPSERT operations.
* **Tier 1 (Working Memory):** Context window token budgeting via `SessionSummarizer` using `tiktoken`, enforcing atomic block grouping to prevent separation of tool calls from tool outputs.
* **Tier 2 (Vector Store):** ChromaDB collection (`VectorMemoryStore`) storing long-term semantic memories via local `nomic-embed-text` embeddings.
* **Tier 3 (Lifecycle Manager):** Background worker (`AsyncMemoryManager`) that records conversation turns and triggers extraction only after a 45-second user inactivity debounce window.

To eliminate wasted inference calls, incoming turns are evaluated against immutable `frozenset` collections and precompiled regular expressions to discard trivial messages before invoking the background extractor model (`qwen2.5:7b`).
Graph checkpointing across turns is persisted to SQLite using `AsyncSqliteSaver`.

## Justification
Offloading extraction to a 45-second debounce window ensures that local GPU compute is dedicated entirely to foreground user interactions while the user is actively chatting.
Zero-cost heuristic pre-filtering discards greetings and acknowledgments in microseconds, preventing low-value noise from polluting ChromaDB.
Using SQLite for Tier 0 guarantees exact-match retrieval for system paths and user names, eliminating the hallucinations common in probabilistic vector lookups.
Atomic tool grouping protects the structural integrity of conversation turns during token budget pruning.

## Consequences
* **Positive:** Interactive chat latency is preserved with zero GPU contention; persistent memories survive application restarts; token trimming never breaks LangChain tool schemas.
* **Negative:** Memory consolidation is eventually consistent; facts mentioned in conversation are not indexed until 45 seconds of inactivity elapse; sudden process termination during the debounce window discards unpersisted buffer turns.
