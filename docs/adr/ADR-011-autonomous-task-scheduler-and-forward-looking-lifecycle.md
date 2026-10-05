# ADR-011: Autonomous Task Scheduler with Strictly Forward-Looking Desktop Lifecycle

## Status
Accepted

## Date
2026-10-01

## Context
As an autonomous desktop assistant, JARVIS must execute one-shot reminders and recurring automation routines (e.g., daily email triage, resource monitoring). Unlike cloud microservices that run 24/7 in serverless or containerized environments, a desktop assistant operates on personal workstations subject to non-deterministic power cycles (shutdowns, sleep mode, prolonged offline periods).

If a naive scheduler attempts retrospective catch-up or accumulative replay, prolonged offline periods (e.g., a laptop powered off for three weeks) would result in a "thundering herd" storm of dozens of queued executions immediately upon boot.

Furthermore, scheduling operations must be manageable across two distinct human-agent interaction planes:
1. **Conversational Cognitive Channel**: Voice and chat intent decomposition via LangGraph tools.
2. **Deterministic UI Control Plane**: Manual modal configuration and visual task cards on the React HUD.

## Decision
We implemented a dedicated **`TaskSchedulerService`** within the `reasoning-engine` subsystem backed by asynchronous SQLite persistence (`aiosqlite`) and cron evaluation (`croniter`), governed by the following architectural tenets:

1. **Strictly Forward-Looking Startup Policy**:
   * **Recurring Tasks (`CRON` / `INTERVAL`)**: When the system boots, `next_run_at` timestamps are recalculated strictly for the next future occurrence (`next_run_at >= now()`). All past missed intervals while the machine was powered off are discarded with zero execution accumulation.
   * **One-Shot Tasks (`ONE_SHOT`)**: If the target timestamp has passed while offline, the task transitions immediately to `EXPIRED` without running out-of-context retroactive actions.
2. **Dual-Plane Management Architecture**:
   * Cognitive LangGraph tools (`programar_tarea`, `listar_tareas_programadas`, `cancelar_tarea_programada`, `pausar_reanudar_tarea`) execute directly in Python, seamlessly interfacing with the agent's LLM intent router.
   * Full-duplex WebSocket contracts (`task_create`, `task_toggle`, `task_delete`, `task_run_now`, `tasks_list`, `task_triggered`) synchronize state bidirectionally with the React `desktop-client`.
3. **Reactive Proactive Notification**:
   * Upon task execution, the dispatcher executes the tool RPC (via RabbitMQ to Java or local Python handler), records execution duration in audit logs, and pushes proactive speech synthesis (TTS) and HUD visual toasts to the client.

## Consequences

### Positive
* **Zero Offline Storms**: Eliminates runaway task storms and unexpected host OS mutations when booting a machine after prolonged offline intervals.
* **Persistent & Resilient**: Preserves all tasks and schedule definitions across system restarts in local SQLite database.
* **Unified Control**: Seamless parity between voice/chat commands and the React HUD visual deck.

### Trade-offs
* One-shot tasks scheduled during an offline window will not execute (marked `EXPIRED`). This behavior is deliberate to prevent outdated, irrelevant, or disruptive actions from running retroactively.
