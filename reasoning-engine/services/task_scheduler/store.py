"""
Asynchronous SQLite persistence store for scheduled tasks and execution audit logs.
"""

import json
from pathlib import Path
from typing import Any

import aiosqlite
from logger import get_logger

from .models import (
    ScheduledTask,
    TaskExecutionLog,
    TaskStatus,
    TriggerConfig,
    TriggerType,
)

logger = get_logger("reasoning_engine.task_scheduler.store")


_UNSET = object()


class TaskStore:
    """
    Manages persistent SQLite storage for scheduled tasks and execution logs.
    """

    def __init__(self, db_path: str = "./data/scheduled_tasks.db"):
        self.db_path = Path(db_path)
        self._db: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Create database tables and required indexes."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(str(self.db_path))
        self._db.row_factory = aiosqlite.Row

        await self._db.execute("PRAGMA journal_mode=WAL;")
        await self._db.execute("PRAGMA synchronous=NORMAL;")

        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                tool_name TEXT NOT NULL,
                tool_arguments TEXT NOT NULL,
                trigger_type TEXT NOT NULL,
                trigger_config TEXT NOT NULL,
                status TEXT NOT NULL,
                notify_voice INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                last_run_at TEXT,
                next_run_at TEXT
            );
        """)

        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON scheduled_tasks(status);
        """)

        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS task_execution_logs (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                executed_at TEXT NOT NULL,
                duration_ms INTEGER NOT NULL,
                status TEXT NOT NULL,
                result_payload TEXT,
                error_message TEXT,
                FOREIGN KEY (task_id) REFERENCES scheduled_tasks(id) ON DELETE CASCADE
            );
        """)

        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_task_id ON task_execution_logs(task_id);
        """)

        await self._db.commit()
        logger.info("TaskStore SQLite initialized at %s", self.db_path)

    async def save_task(self, task: ScheduledTask) -> None:
        """Insert or replace a scheduled task in the database."""
        if not self._db:
            raise RuntimeError("TaskStore is not initialized. Call initialize() first.")

        query = """
            INSERT INTO scheduled_tasks (
                id, name, description, tool_name, tool_arguments,
                trigger_type, trigger_config, status, notify_voice,
                created_at, last_run_at, next_run_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                description=excluded.description,
                tool_name=excluded.tool_name,
                tool_arguments=excluded.tool_arguments,
                trigger_type=excluded.trigger_type,
                trigger_config=excluded.trigger_config,
                status=excluded.status,
                notify_voice=excluded.notify_voice,
                last_run_at=excluded.last_run_at,
                next_run_at=excluded.next_run_at;
        """
        await self._db.execute(
            query,
            (
                task.id,
                task.name,
                task.description,
                task.tool_name,
                json.dumps(task.tool_arguments),
                task.trigger_type.value,
                json.dumps(task.trigger_config.model_dump()),
                task.status.value,
                1 if task.notify_voice else 0,
                task.created_at,
                task.last_run_at,
                task.next_run_at,
            ),
        )
        await self._db.commit()

    async def get_task(self, task_id: str) -> ScheduledTask | None:
        """Fetch a single scheduled task by its unique identifier."""
        if not self._db:
            raise RuntimeError("TaskStore is not initialized.")

        cursor = await self._db.execute(
            "SELECT * FROM scheduled_tasks WHERE id = ?", (task_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return self._row_to_task(row)

    async def list_tasks(self, status: TaskStatus | None = None) -> list[ScheduledTask]:
        """List scheduled tasks, optionally filtered by status."""
        if not self._db:
            raise RuntimeError("TaskStore is not initialized.")

        if status:
            cursor = await self._db.execute(
                "SELECT * FROM scheduled_tasks WHERE status = ? ORDER BY created_at DESC",
                (status.value,),
            )
        else:
            cursor = await self._db.execute(
                "SELECT * FROM scheduled_tasks ORDER BY created_at DESC"
            )

        rows = await cursor.fetchall()
        return [self._row_to_task(row) for row in rows]

    async def update_task_status(self, task_id: str, status: TaskStatus) -> bool:
        """Update the status of a scheduled task."""
        if not self._db:
            raise RuntimeError("TaskStore is not initialized.")

        cursor = await self._db.execute(
            "UPDATE scheduled_tasks SET status = ? WHERE id = ?",
            (status.value, task_id),
        )
        await self._db.commit()
        return cursor.rowcount > 0

    async def update_task_run_times(
        self,
        task_id: str,
        last_run_at: Any = _UNSET,
        next_run_at: Any = _UNSET,
        status: Any = _UNSET,
    ) -> bool:
        """Update last_run_at, next_run_at, and optionally status."""
        if not self._db:
            raise RuntimeError("TaskStore is not initialized.")

        updates = []
        params = []
        if last_run_at is not _UNSET:
            updates.append("last_run_at = ?")
            params.append(last_run_at)
        if next_run_at is not _UNSET:
            updates.append("next_run_at = ?")
            params.append(next_run_at)
        if status is not _UNSET:
            updates.append("status = ?")
            params.append(status.value if isinstance(status, TaskStatus) else status)

        if not updates:
            return False

        params.append(task_id)
        query = f"UPDATE scheduled_tasks SET {', '.join(updates)} WHERE id = ?"
        cursor = await self._db.execute(query, tuple(params))
        await self._db.commit()
        return cursor.rowcount > 0

    async def delete_task(self, task_id: str) -> bool:
        """Permanently delete a scheduled task and its logs."""
        if not self._db:
            raise RuntimeError("TaskStore is not initialized.")

        await self._db.execute(
            "DELETE FROM task_execution_logs WHERE task_id = ?", (task_id,)
        )
        cursor = await self._db.execute(
            "DELETE FROM scheduled_tasks WHERE id = ?", (task_id,)
        )
        await self._db.commit()
        return cursor.rowcount > 0

    async def log_execution(self, log: TaskExecutionLog) -> None:
        """Record an execution event in the audit log."""
        if not self._db:
            raise RuntimeError("TaskStore is not initialized.")

        query = """
            INSERT INTO task_execution_logs (
                id, task_id, executed_at, duration_ms, status, result_payload, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        await self._db.execute(
            query,
            (
                log.id,
                log.task_id,
                log.executed_at,
                log.duration_ms,
                log.status,
                json.dumps(log.result_payload) if log.result_payload else None,
                log.error_message,
            ),
        )
        await self._db.commit()

    async def close(self) -> None:
        """Close the SQLite database connection cleanly."""
        if self._db:
            await self._db.close()
            self._db = None
            logger.info("TaskStore connection closed.")

    @staticmethod
    def _row_to_task(row: aiosqlite.Row) -> ScheduledTask:
        """Deserialize an SQLite row into a ScheduledTask model."""
        tool_args = json.loads(row["tool_arguments"]) if row["tool_arguments"] else {}
        trigger_cfg_dict = (
            json.loads(row["trigger_config"]) if row["trigger_config"] else {}
        )

        return ScheduledTask(
            id=row["id"],
            name=row["name"],
            description=row["description"] or "",
            tool_name=row["tool_name"],
            tool_arguments=tool_args,
            trigger_type=TriggerType(row["trigger_type"]),
            trigger_config=TriggerConfig.model_validate(trigger_cfg_dict),
            status=TaskStatus(row["status"]),
            notify_voice=bool(row["notify_voice"]),
            created_at=row["created_at"],
            last_run_at=row["last_run_at"],
            next_run_at=row["next_run_at"],
        )
