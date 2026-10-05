"""
TaskSchedulerService manages lifecycle, cron/one-shot trigger evaluation,
persistent SQLite synchronization, and tool dispatching for scheduled routines.
"""
import asyncio
from datetime import datetime, timedelta, timezone
import json
import time
from typing import Any, Dict, List, Optional
import uuid

from croniter import croniter

from logger import get_logger
from .models import (
    ScheduledTask,
    TaskCreateRequest,
    TaskExecutionLog,
    TaskStatus,
    TriggerConfig,
    TriggerType,
)
from .store import TaskStore

logger = get_logger("reasoning_engine.task_scheduler.service")

MS_PER_SECOND = 1000
DEFAULT_SOURCE_ID = "reasoning-engine"
TOOL_REQUEST_ROUTING_KEY_PREFIX = "tool.request."


class TaskSchedulerService:
    """
    Core scheduler service responsible for recurring and one-shot task execution.
    """

    def __init__(
        self,
        store: Optional[TaskStore] = None,
        runtime: Optional[Any] = None,
        ws_manager: Optional[Any] = None,
    ) -> None:
        self.store = store or TaskStore()
        self.runtime = runtime
        self.ws_manager = ws_manager
        self._running = False
        self._loop_task: Optional[asyncio.Task[None]] = None
        self._executing_tasks: set[str] = set()

    async def start(self) -> None:
        """
        Initialize the SQLite store, rehydrate active tasks according to the
        strictly forward-looking startup policy, and launch the scheduler loop.
        """
        if self._running:
            return

        logger.info("Starting TaskSchedulerService...")
        await self.store.initialize()
        self._running = True

        # Rehydrate and compute forward-looking next_run_at timestamps
        await self._rehydrate_tasks()

        # Launch the periodic evaluation loop
        self._loop_task = asyncio.create_task(self._scheduler_loop())
        logger.info("TaskSchedulerService active and evaluating tasks.")

    async def stop(self) -> None:
        """Gracefully stop the scheduler loop and close the database store."""
        if not self._running:
            return

        logger.info("Stopping TaskSchedulerService...")
        self._running = False
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass

        await self.store.close()
        logger.info("TaskSchedulerService stopped.")

    def calculate_next_run(
        self,
        trigger_type: TriggerType,
        trigger_config: TriggerConfig,
        from_time: Optional[datetime] = None,
    ) -> Optional[datetime]:
        """
        Compute the next occurrence strictly after 'from_time' (or current local time).
        """
        base_time = from_time or datetime.now()

        if trigger_type == TriggerType.ONE_SHOT:
            if not trigger_config.run_at:
                return None
            try:
                target_time = datetime.fromisoformat(trigger_config.run_at)
                # Compare without timezone issues if naive
                if target_time.tzinfo and not base_time.tzinfo:
                    base_time = base_time.astimezone()
                elif not target_time.tzinfo and base_time.tzinfo:
                    target_time = target_time.astimezone()
                
                return target_time if target_time > base_time else None
            except Exception as e:
                logger.warning("Invalid one-shot run_at format '%s': %s", trigger_config.run_at, e)
                return None

        elif trigger_type == TriggerType.CRON:
            if not trigger_config.cron_expr:
                return None
            try:
                # Calculate next occurrence strictly in the future
                cron = croniter(trigger_config.cron_expr, base_time)
                return cron.get_next(datetime)
            except Exception as e:
                logger.warning("Invalid cron expression '%s': %s", trigger_config.cron_expr, e)
                return None

        elif trigger_type == TriggerType.INTERVAL:
            seconds = trigger_config.interval_seconds or 60
            return base_time + timedelta(seconds=max(1, seconds))

        return None

    async def _rehydrate_tasks(self) -> None:
        """
        Scan all active tasks in SQLite and adjust next_run_at strictly to the future.
        Expired one-shots are marked EXPIRED. Recurring tasks skip past missed intervals.
        """
        now = datetime.now()
        active_tasks = await self.store.list_tasks(status=TaskStatus.ACTIVE)
        logger.info("Rehydrating %d active scheduled tasks from store...", len(active_tasks))

        for task in active_tasks:
            if task.trigger_type == TriggerType.ONE_SHOT:
                next_run = self.calculate_next_run(task.trigger_type, task.trigger_config, now)
                if next_run is None:
                    # One-shot scheduled for the past while system was off -> mark EXPIRED
                    logger.info("One-shot task '%s' (%s) expired while offline. Marking EXPIRED.", task.name, task.id)
                    await self.store.update_task_run_times(
                        task.id,
                        last_run_at=task.last_run_at,
                        next_run_at=None,
                        status=TaskStatus.EXPIRED,
                    )
                else:
                    await self.store.update_task_run_times(
                        task.id,
                        last_run_at=task.last_run_at,
                        next_run_at=next_run.isoformat(),
                        status=TaskStatus.ACTIVE,
                    )
            else:
                # Recurrent (CRON / INTERVAL): calculate next future run >= now
                next_run = self.calculate_next_run(task.trigger_type, task.trigger_config, now)
                next_run_iso = next_run.isoformat() if next_run else None
                await self.store.update_task_run_times(
                    task.id,
                    last_run_at=task.last_run_at,
                    next_run_at=next_run_iso,
                    status=TaskStatus.ACTIVE,
                )

    async def _scheduler_loop(self) -> None:
        """
        Continuous asynchronous loop polling for due tasks.
        """
        while self._running:
            try:
                now = datetime.now()
                tasks = await self.store.list_tasks(status=TaskStatus.ACTIVE)

                for task in tasks:
                    if not task.next_run_at:
                        continue

                    try:
                        next_run_dt = datetime.fromisoformat(task.next_run_at)
                        now_cmp = now
                        if next_run_dt.tzinfo and not now_cmp.tzinfo:
                            now_cmp = now_cmp.astimezone()
                        elif not next_run_dt.tzinfo and now_cmp.tzinfo:
                            next_run_dt = next_run_dt.astimezone()

                        if next_run_dt <= now_cmp and task.id not in self._executing_tasks:
                            self._executing_tasks.add(task.id)
                            asyncio.create_task(self._safe_execute_task(task.id))
                    except Exception as parse_err:
                        logger.warning("Error evaluating trigger time for task '%s': %s", task.id, parse_err)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in scheduler evaluation loop: %s", e)

            await asyncio.sleep(1.0)

    async def _safe_execute_task(self, task_id: str) -> None:
        """Wrapper to ensure executing task ID is removed from tracking set."""
        try:
            await self.execute_task(task_id, is_manual=False)
        finally:
            self._executing_tasks.discard(task_id)

    async def execute_task(self, task_id: str, is_manual: bool = False) -> Dict[str, Any]:
        """
        Execute a scheduled task:
        1. Invokes the associated tool or proactive notification.
        2. Logs the result in SQLite.
        3. Updates the task lifecycle (ONE_SHOT -> COMPLETED, CRON -> next future date).
        4. Broadcasts WebSocket updates and triggers audio/HUD notifications.
        """
        task = await self.store.get_task(task_id)
        if not task:
            logger.warning("Cannot execute task: task_id '%s' not found.", task_id)
            return {"status": "ERROR", "message": "Task not found"}

        if not is_manual and task.status != TaskStatus.ACTIVE:
            logger.info("Skipping task '%s' because status is %s", task.name, task.status)
            return {"status": "SKIPPED", "message": f"Task is {task.status}"}

        start_time = time.time()
        logger.info("Executing scheduled task: '%s' (Tool: '%s', Manual: %s)", task.name, task.tool_name, is_manual)

        status_result = "SUCCESS"
        error_msg: Optional[str] = None
        result_payload: Dict[str, Any] = {}
        speech_text = ""

        try:
            # 1. Dispatch action
            if task.tool_name in ("notificacion_proactiva", "recordatorio", "alerta"):
                # Pure proactive notification
                speech_text = task.description or task.name
                result_payload = {"message": speech_text}
            else:
                # Dispatch tool via RabbitMQ to Java Execution Service or local handler
                if self.runtime and self.runtime.mq_client:
                    from agent.models import (
                        EventEnvelope,
                        EventMetadata,
                        EventType,
                        ToolExecutionRequestPayload,
                    )
                    tool_call_id = str(uuid.uuid4())
                    request_payload = ToolExecutionRequestPayload(
                        tool_name=task.tool_name,
                        arguments=task.tool_arguments,
                    )
                    envelope = EventEnvelope(
                        metadata=EventMetadata(
                            event_id=str(uuid.uuid4()),
                            correlation_id=tool_call_id,
                            timestamp=int(time.time() * MS_PER_SECOND),
                            source=DEFAULT_SOURCE_ID,
                            event_type=EventType.EXECUTION_REQUEST,
                        ),
                        payload=request_payload.model_dump(by_alias=True),
                    )
                    routing_key = f"{TOOL_REQUEST_ROUTING_KEY_PREFIX}{task.tool_name}"
                    raw_response = await self.runtime.mq_client.send_and_wait(routing_key, envelope)

                    if raw_response and isinstance(raw_response, dict):
                        payload = raw_response.get("payload", {})
                        if payload.get("status") == "SUCCESS":
                            output = payload.get("output", "Completado.")
                            result_payload = {"output": output}
                            speech_text = f"Tarea programada completada: {task.name}. {output}"

                            # Trigger email classifier if tool was unread emails
                            if task.tool_name == "consultar_correos_no_leidos" and self.runtime.email_service and self.ws_manager:
                                raw_emails = self.runtime.email_service.parse_emails_from_tool_output(output)
                                emails_payload = []
                                for raw_email in raw_emails:
                                    classified = await self.runtime.email_service.classify_email(raw_email)
                                    emails_payload.append({
                                        "id": raw_email.id,
                                        "account": raw_email.account,
                                        "account_address": raw_email.account_address,
                                        "subject": raw_email.subject,
                                        "from_name": raw_email.from_name,
                                        "from_address": raw_email.from_address,
                                        "reply_to_address": raw_email.reply_to_address or raw_email.from_address,
                                        "received_at": raw_email.received_at,
                                        "body_snippet": raw_email.body_snippet or "",
                                        "body_text": raw_email.body_text or raw_email.body_snippet or "",
                                        "has_attachments": raw_email.has_attachments,
                                        "category": classified.category.value,
                                        "urgency_score": classified.urgency_score,
                                        "requires_reply": classified.requires_reply,
                                        "suggested_action": classified.suggested_action,
                                    })
                                await self.ws_manager.send_or_broadcast({
                                    "type": "unread_emails_update",
                                    "emails": emails_payload,
                                })
                        else:
                            status_result = "ERROR"
                            error_msg = payload.get("output", "Execution failed.")
                            speech_text = f"Aviso: La tarea '{task.name}' reportó un problema: {error_msg}"
                    else:
                        status_result = "ERROR"
                        error_msg = "No response received from execution service."
                else:
                    result_payload = {"simulated": True, "message": f"Tool '{task.tool_name}' executed."}
                    speech_text = f"Tarea programada completada: {task.name}."

        except Exception as e:
            logger.error("Exception executing task '%s': %s", task.id, e, exc_info=True)
            status_result = "ERROR"
            error_msg = str(e)
            speech_text = f"Error al ejecutar la tarea programada {task.name}."

        duration_ms = int((time.time() - start_time) * MS_PER_SECOND)
        now_iso = datetime.now().isoformat()

        # 2. Log execution
        log_entry = TaskExecutionLog(
            id=f"log_{uuid.uuid4().hex[:12]}",
            task_id=task.id,
            executed_at=now_iso,
            duration_ms=duration_ms,
            status=status_result,
            result_payload=result_payload,
            error_message=error_msg,
        )
        await self.store.log_execution(log_entry)

        # 3. Update task lifecycle
        if task.trigger_type == TriggerType.ONE_SHOT:
            new_status = TaskStatus.COMPLETED
            next_run_iso = None
        else:
            new_status = task.status
            next_run = self.calculate_next_run(task.trigger_type, task.trigger_config, datetime.now())
            next_run_iso = next_run.isoformat() if next_run else None

        await self.store.update_task_run_times(
            task.id,
            last_run_at=now_iso,
            next_run_at=next_run_iso,
            status=new_status,
        )

        # 4. Broadcast proactive notification and updated task list via WebSocket
        if self.ws_manager:
            # Send notification event
            await self.ws_manager.send_or_broadcast({
                "type": "task_triggered",
                "task_id": task.id,
                "name": task.name,
                "status": status_result,
                "result": result_payload,
                "speech_text": speech_text if task.notify_voice else "",
                "notify_voice": task.notify_voice,
            })
            # Send updated tasks list
            all_tasks = await self.list_tasks()
            await self.ws_manager.send_or_broadcast({
                "type": "tasks_list",
                "tasks": [t.model_dump() for t in all_tasks],
            })

        return {
            "status": status_result,
            "task_id": task.id,
            "duration_ms": duration_ms,
            "result": result_payload,
            "error": error_msg,
        }

    async def create_task(self, req: TaskCreateRequest) -> ScheduledTask:
        """Create and persist a new scheduled task, calculating its initial next_run_at."""
        task_id = f"task_{uuid.uuid4().hex[:10]}"
        now = datetime.now()
        next_run = self.calculate_next_run(req.trigger_type, req.trigger_config, now)
        next_run_iso = next_run.isoformat() if next_run else None

        initial_status = TaskStatus.ACTIVE
        if req.trigger_type == TriggerType.ONE_SHOT and next_run is None:
            initial_status = TaskStatus.EXPIRED

        task = ScheduledTask(
            id=task_id,
            name=req.name,
            description=req.description,
            tool_name=req.tool_name,
            tool_arguments=req.tool_arguments,
            trigger_type=req.trigger_type,
            trigger_config=req.trigger_config,
            status=initial_status,
            notify_voice=req.notify_voice,
            created_at=now.isoformat(),
            last_run_at=None,
            next_run_at=next_run_iso,
        )

        await self.store.save_task(task)
        logger.info("Created scheduled task '%s' (%s) with next run at %s", task.name, task.id, task.next_run_at)

        if self.ws_manager:
            all_tasks = await self.list_tasks()
            await self.ws_manager.send_or_broadcast({
                "type": "tasks_list",
                "tasks": [t.model_dump() for t in all_tasks],
            })

        return task

    async def list_tasks(self, status: Optional[TaskStatus] = None) -> List[ScheduledTask]:
        """List scheduled tasks from the persistent SQLite store."""
        return await self.store.list_tasks(status=status)

    async def toggle_task(self, task_id: str, enabled: bool) -> Optional[ScheduledTask]:
        """Enable (ACTIVE) or pause (PAUSED) a scheduled task."""
        task = await self.store.get_task(task_id)
        if not task:
            return None

        new_status = TaskStatus.ACTIVE if enabled else TaskStatus.PAUSED
        next_run_iso = task.next_run_at

        if enabled:
            # Recalculate next run strictly in the future
            next_run = self.calculate_next_run(task.trigger_type, task.trigger_config, datetime.now())
            next_run_iso = next_run.isoformat() if next_run else None

        await self.store.update_task_run_times(
            task_id=task_id,
            last_run_at=task.last_run_at,
            next_run_at=next_run_iso,
            status=new_status,
        )
        updated = await self.store.get_task(task_id)

        if self.ws_manager:
            all_tasks = await self.list_tasks()
            await self.ws_manager.send_or_broadcast({
                "type": "tasks_list",
                "tasks": [t.model_dump() for t in all_tasks],
            })

        return updated

    async def delete_task(self, task_id: str) -> bool:
        """Permanently delete a task."""
        success = await self.store.delete_task(task_id)
        if success and self.ws_manager:
            all_tasks = await self.list_tasks()
            await self.ws_manager.send_or_broadcast({
                "type": "tasks_list",
                "tasks": [t.model_dump() for t in all_tasks],
            })
        return success
