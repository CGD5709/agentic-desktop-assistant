# ADR-003: Deterministic Directed Acyclic Graph for Cognitive Orchestration

## Context and Problem
Agentic systems frequently rely on cyclic ReAct (Reasoning and Acting) loops that allow an LLM to iteratively call tools and reflect on outputs until satisfied.
On local inference hardware, cyclic loops cause unpredictable response latency, unbounded token burn, and non-deterministic execution failure modes.
Desktop operating system administration requires bounded execution bounds, predictable latency, and guarantees against the fabrication of system telemetry.

## Alternatives Considered
* **Autonomous Cyclic ReAct Loop:** Let the LLM cycle continuously between execution and self-reflection until it emits a completion token.
  * *Pros:* High flexibility for open-ended, multi-step problem solving; minimal hardcoded workflow logic.
  * *Cons:* Risk of infinite tool-calling loops; unbounded token consumption; high latency variance on local LLMs; tendency to hallucinate system states when commands fail.
* **Hardcoded Procedural Pipeline:** Script fixed sequences of tool executions without dynamic LLM routing.
  * *Pros:* Fully deterministic; zero token waste; instantaneous execution.
  * *Cons:* Inflexible; cannot parse nuanced user instructions; cannot dynamically extract arguments from conversational text.
* **Deterministic Directed Acyclic Graph (DAG):** Model cognition as a state graph with strict forward-only edges and semantic intent routing.
  * *Pros:* Guaranteed execution termination; bounded token budgets; explicit separation between conversational dialogue and technical tool execution.
  * *Cons:* Cannot execute dynamic multi-hop exploratory tool loops within a single turn; multi-step operations require sequential user interactions.

## Decision
We structured the cognitive engine as a deterministic Directed Acyclic Graph (DAG) using LangGraph, eliminating all backward edges.
Execution begins at `RouterNode`, which classifies incoming user messages into either `CHAT` or `COMMAND` intent.
The `CHAT` branch routes directly to `ChatNode` to generate a conversational response and terminates at `END`.
The `COMMAND` branch routes to `CommandNode` to bind tool schemas, routes to `ActionNode` via RabbitMQ if tools are invoked, and routes through `SummarizeNode` to translate raw OS outputs into concise user responses before terminating at `END`.

## Justification
Removing cyclic edges guarantees an upper bound on token consumption and inference latency for every user turn.
Early intent classification prevents conversational messages from loading tool definitions or executing vector memory lookups.
`SummarizeNode` serves as a translation boundary that prevents raw terminal outputs, error traces, and JSON payloads from polluting the user interface.
The veracity guardrail forces the model to emit tool calls rather than inventing plausible system metrics like memory usage or active ports.

## Consequences
* **Positive:** Bounded execution time and cost per conversational turn; elimination of runaway agent loops; clean conversational presentation of technical results; deterministic termination guarantees.
* **Negative:** The agent cannot autonomously execute multi-step diagnostic sequences within a single interaction turn; complex troubleshooting workflows require multiple user prompts.
