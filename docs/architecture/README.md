# System Architecture Documentation

This directory contains the formal architectural specifications, technical blueprints, and protocol definitions for the **JARVIS Agentic Desktop Assistant**.

---

## Document Index

| Document | Purpose & Scope | Target Audience |
| :--- | :--- | :--- |
| **[System Architecture](system-architecture.md)** | Comprehensive end-to-end system design, C4 container model, microservice boundaries, failure domains, and data consistency models. | Architects, Lead Engineers, Contributors |
| **[Email Subsystem Architecture](email-subsystem-architecture.md)** | Multi-account ingestion, 5-category semantic classification, RFC-822 zero-hallucination recipient resolution, and interactive central canvas review deck. | Backend, AI & Frontend Developers |
| **[WebSocket Protocol Specification](websocket-protocol-spec.md)** | Formal tagged-union JSON schema contracts, full-duplex message lifecycle, heartbeat probing, state telemetry, and HITL payloads. | Frontend & API Engineers |

---

## Cross-Cutting References

* **Architecture Decision Records (ADRs)**: [`docs/adr/`](../adr/)
* **Canonical RabbitMQ AMQP Specification**: [`docs/messaging/rabbitmq-spec.md`](../messaging/rabbitmq-spec.md)
* **Master System Overview**: [`README.md`](../../README.md)
