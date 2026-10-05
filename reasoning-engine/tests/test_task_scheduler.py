"""
Unit and integration tests for TaskSchedulerService and TaskStore.
"""
from datetime import datetime, timedelta, timezone

import pytest

from services.task_scheduler.models import (
    ScheduledTask,
    TaskStatus,
    TriggerConfig,
    TriggerType,
)
from services.task_scheduler.scheduler_service import TaskSchedulerService
from services.task_scheduler.store import TaskStore


@pytest.mark.asyncio
async def test_store_crud(tmp_path):
    db_path = str(tmp_path / "test_tasks.db")
    store = TaskStore(db_path=db_path)
    await store.initialize()

    task = ScheduledTask(
        id="task_123",
        name="Test Task",
        description="A test description",
        tool_name="analizar_rendimiento_procesos",
        tool_arguments={"limite": 5},
        trigger_type=TriggerType.CRON,
        trigger_config=TriggerConfig(cron_expr="0 8 * * *"),
        status=TaskStatus.ACTIVE,
        notify_voice=True,
        created_at=datetime.now(timezone.utc).isoformat(),
        last_run_at=None,
        next_run_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    )

    await store.save_task(task)
    retrieved = await store.get_task("task_123")
    assert retrieved is not None
    assert retrieved.name == "Test Task"
    assert retrieved.tool_name == "analizar_rendimiento_procesos"
    assert retrieved.tool_arguments == {"limite": 5}
    assert retrieved.trigger_type == TriggerType.CRON

    # Update status
    await store.update_task_status("task_123", TaskStatus.PAUSED)
    updated = await store.get_task("task_123")
    assert updated is not None
    assert updated.status == TaskStatus.PAUSED

    # Delete
    deleted = await store.delete_task("task_123")
    assert deleted is True
    assert await store.get_task("task_123") is None

    await store.close()


@pytest.mark.asyncio
async def test_scheduler_next_run_calculation(tmp_path):
    db_path = str(tmp_path / "test_tasks2.db")
    store = TaskStore(db_path=db_path)
    await store.initialize()
    scheduler = TaskSchedulerService(store=store)

    # 1. One-shot in the future
    future_time = datetime.now(timezone.utc) + timedelta(minutes=15)
    cfg_oneshot_future = TriggerConfig(run_at=future_time.isoformat())
    next_run = scheduler.calculate_next_run(TriggerType.ONE_SHOT, cfg_oneshot_future)
    assert next_run is not None

    # 2. One-shot in the past
    past_time = datetime.now(timezone.utc) - timedelta(minutes=15)
    cfg_oneshot_past = TriggerConfig(run_at=past_time.isoformat())
    next_run_past = scheduler.calculate_next_run(TriggerType.ONE_SHOT, cfg_oneshot_past)
    assert next_run_past is None

    # 3. Cron calculation
    cfg_cron = TriggerConfig(cron_expr="0 8 * * *")
    next_cron = scheduler.calculate_next_run(TriggerType.CRON, cfg_cron)
    assert next_cron is not None
    assert next_cron.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc)
    assert next_cron.hour == 8
    assert next_cron.minute == 0

    await store.close()


@pytest.mark.asyncio
async def test_scheduler_rehydration_forward_looking(tmp_path):
    db_path = str(tmp_path / "test_tasks3.db")
    store = TaskStore(db_path=db_path)
    await store.initialize()
    scheduler = TaskSchedulerService(store=store)

    # Insert a one-shot task that was scheduled for yesterday (PC was off)
    past_time = datetime.now(timezone.utc) - timedelta(days=1)
    past_task = ScheduledTask(
        id="task_past_oneshot",
        name="Past One Shot",
        description="",
        tool_name="recordatorio",
        tool_arguments={},
        trigger_type=TriggerType.ONE_SHOT,
        trigger_config=TriggerConfig(run_at=past_time.isoformat()),
        status=TaskStatus.ACTIVE,
        notify_voice=False,
        created_at=past_time.isoformat(),
        last_run_at=None,
        next_run_at=past_time.isoformat(),
    )
    await store.save_task(past_task)

    # Insert a recurring task that was supposed to run daily at 8am
    cron_task = ScheduledTask(
        id="task_recurring_cron",
        name="Daily Email Review",
        description="",
        tool_name="consultar_correos_no_leidos",
        tool_arguments={},
        trigger_type=TriggerType.CRON,
        trigger_config=TriggerConfig(cron_expr="0 8 * * *"),
        status=TaskStatus.ACTIVE,
        notify_voice=False,
        created_at=(datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
        last_run_at=None,
        next_run_at=(datetime.now(timezone.utc) - timedelta(days=6)).isoformat(),
    )
    await store.save_task(cron_task)

    # Rehydrate
    await scheduler._rehydrate_tasks()

    # Past one-shot should now be EXPIRED
    rehydrated_past = await store.get_task("task_past_oneshot")
    assert rehydrated_past is not None
    assert rehydrated_past.status == TaskStatus.EXPIRED
    assert rehydrated_past.next_run_at is None

    # Recurring cron should remain ACTIVE and next_run_at should be strictly in the future
    rehydrated_cron = await store.get_task("task_recurring_cron")
    assert rehydrated_cron is not None
    assert rehydrated_cron.status == TaskStatus.ACTIVE
    assert rehydrated_cron.next_run_at is not None
    next_dt = datetime.fromisoformat(rehydrated_cron.next_run_at)
    assert next_dt.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc)

    await store.close()
