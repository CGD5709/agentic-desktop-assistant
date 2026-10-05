"""
Domain models and schemas for the Scheduled Tasks & Routines subsystem.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TriggerType(str, Enum):
    """Supported trigger mechanisms for scheduled tasks."""

    ONE_SHOT = "ONE_SHOT"
    CRON = "CRON"
    INTERVAL = "INTERVAL"


class TaskStatus(str, Enum):
    """Lifecycle status of a scheduled task."""

    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"


class TriggerConfig(BaseModel):
    """
    Configuration payload for task trigger evaluation.

    Attributes:
        run_at: ISO8601 string for one-shot execution (e.g., '2026-10-01T18:30:00').
        cron_expr: Standard 5-field cron expression (e.g., '0 8 * * 1-5').
        interval_seconds: Number of seconds between recurring executions.
    """

    run_at: str | None = None
    cron_expr: str | None = None
    interval_seconds: int | None = None


class ScheduledTask(BaseModel):
    """
    Representation of a scheduled task stored in the persistent database.
    """

    id: str
    name: str
    description: str = ""
    tool_name: str
    tool_arguments: dict[str, Any] = Field(default_factory=dict)
    trigger_type: TriggerType
    trigger_config: TriggerConfig
    status: TaskStatus = TaskStatus.ACTIVE
    notify_voice: bool = True
    created_at: str
    last_run_at: str | None = None
    next_run_at: str | None = None


class TaskCreateRequest(BaseModel):
    """
    Request model for creating a new scheduled task from UI or agent tools.
    """

    name: str
    description: str = ""
    tool_name: str
    tool_arguments: dict[str, Any] = Field(default_factory=dict)
    trigger_type: TriggerType
    trigger_config: TriggerConfig
    notify_voice: bool = True


class TaskExecutionLog(BaseModel):
    """
    Audit log entry recording an individual task execution event.
    """

    id: str
    task_id: str
    executed_at: str
    duration_ms: int
    status: str
    result_payload: dict[str, Any] | None = None
    error_message: str | None = None
