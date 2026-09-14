# ADR-001: Polyglot Microservices Separation of Concerns

## Context and Problem
The desktop assistant combines probabilistic AI reasoning, host operating system interaction, and a desktop user interface.
Python dominates LLM orchestration, vector search, and graph-based agent frameworks.
Host system automation (process management, socket inspection, shell command execution) requires deterministic process isolation, strict typing, and defensive security controls.
A single-language monolith forces unacceptable engineering compromises between AI ecosystem tooling and operating system execution safety.

## Alternatives Considered
* **Monolithic Python Architecture:** Implement reasoning, OS automation, and the UI inside a single Python process.
  * *Pros:* Single runtime to deploy; zero network serialization overhead; shared code models.
  * *Cons:* Asyncio event loop blocking during heavy subprocess execution; weak isolation for destructive OS commands; absence of strict compile-time safety on system commands.
* **Monolithic Java Architecture:** Implement cognitive graphs and execution routines entirely in Java 21 and Spring Boot.
  * *Pros:* Mature process execution controls; strict compile-time safety; strong thread concurrency.
  * *Cons:* Immature LLM agent ecosystem; limited native support for stateful graph orchestration like LangGraph; delayed access to community tool bindings.
* **Polyglot Microservices:** Isolate cognitive reasoning, physical execution, and the user interface into separate runtime environments.
  * *Pros:* Each domain utilizes its optimal technology stack; hard process boundaries prevent OS execution failures from crashing cognitive state; independent service scaling.
  * *Cons:* Distributed networking overhead; cross-language schema synchronization costs; multi-runtime developer environment setup.

## Decision
We chose a polyglot microservices architecture maintained within a monorepo.
The cognitive layer is implemented in Python using FastAPI and LangGraph.
The execution layer is implemented in Java 21 using Spring Boot.
The user interface is built with React, TypeScript, and Vite.
Shared message broker infrastructure (RabbitMQ) is containerized via Docker Compose, while application runtimes execute natively on the host OS to retain direct system access.

## Justification
Python provides immediate access to LangGraph state machines, ChromaDB vector stores, and Ollama model APIs.
Java 21 provides deterministic process controls, explicit thread management, and security blacklisting required for safe OS-level automation.
TypeScript guarantees type safety across the frontend user experience.
A monorepo structure keeps data contracts synchronized across services, while restricting Docker to broker infrastructure avoids sandboxing restrictions that would interfere with host OS execution.

## Consequences
* **Positive:** Failures during OS command execution do not terminate the cognitive engine; domain boundaries are strictly enforced; services evolve independently within their native ecosystems.
* **Negative:** Local development requires three separate toolchains (Python 3.11+, Java 21, Node.js); memory consumption increases due to running both the JVM and Python runtimes; inter-service communication introduces latency and serialization overhead.
