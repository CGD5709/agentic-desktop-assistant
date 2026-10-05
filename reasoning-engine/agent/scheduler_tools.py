import json
from typing import Any, Dict, List

from services.task_scheduler.models import TaskCreateRequest, TriggerType, TriggerConfig, TaskStatus

SCHEDULER_TOOLS_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "programar_tarea",
            "description": "Create a new scheduled task (cron or one_shot). IMPORTANT: The user must confirm before creating it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the task (e.g. 'Morning email review')."
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of what the task does."
                    },
                    "tool_name": {
                        "type": "string",
                        "description": "The exact name of the tool to execute (e.g. 'consultar_correos_no_leidos', 'analizar_rendimiento_procesos')."
                    },
                    "tool_arguments": {
                        "type": "object",
                        "description": "JSON arguments for the tool.",
                        "additionalProperties": True
                    },
                    "trigger_type": {
                        "type": "string",
                        "enum": ["CRON", "ONE_SHOT"],
                        "description": "Trigger type."
                    },
                    "cron_expr": {
                        "type": "string",
                        "description": "Cron expression (only if trigger_type is CRON)."
                    },
                    "run_at": {
                        "type": "string",
                        "description": "ISO 8601 date and time (only if trigger_type is ONE_SHOT)."
                    },
                    "notify_voice": {
                        "type": "boolean",
                        "description": "If true, the agent will speak when the task is executed."
                    }
                },
                "required": ["name", "tool_name", "trigger_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "listar_tareas_programadas",
            "description": "Return the list of current scheduled tasks.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancelar_tarea_programada",
            "description": "Delete a scheduled task by ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The ID of the task to delete."
                    }
                },
                "required": ["task_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "pausar_reanudar_tarea",
            "description": "Pause or resume a scheduled task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The ID of the task."
                    },
                    "status": {
                        "type": "string",
                        "enum": ["ACTIVE", "PAUSED"],
                        "description": "The new status of the task."
                    }
                },
                "required": ["task_id", "status"]
            }
        }
    }
]

async def handle_scheduler_tool_execution(tool_name: str, tool_args: Dict[str, Any], task_scheduler: Any) -> str:
    """
    Handle the execution of scheduler tools.
    """
    try:
        if tool_name == "programar_tarea":
            trigger_type_str = tool_args.get("trigger_type", "ONE_SHOT")
            trigger_type = TriggerType.CRON if trigger_type_str == "CRON" else TriggerType.ONE_SHOT
            
            run_at = tool_args.get("run_at")
            cron_expr = tool_args.get("cron_expr")
            
            trigger_config = TriggerConfig(run_at=run_at, cron_expr=cron_expr)
            
            req = TaskCreateRequest(
                name=tool_args.get("name", "Unnamed Task"),
                description=tool_args.get("description", ""),
                tool_name=tool_args.get("tool_name", ""),
                tool_arguments=tool_args.get("tool_arguments", {}),
                trigger_type=trigger_type,
                trigger_config=trigger_config,
                notify_voice=tool_args.get("notify_voice", False)
            )
            task = await task_scheduler.create_task(req)
            return f"Task '{task.name}' successfully scheduled with ID {task.id}."
            
        elif tool_name == "listar_tareas_programadas":
            tasks = await task_scheduler.get_all_tasks()
            if not tasks:
                return "No scheduled tasks found."
            
            res = "Scheduled tasks:\n"
            for t in tasks:
                res += f"- ID: {t.id} | Name: {t.name} | Status: {t.status.value} | Trigger: {t.trigger_type.value} | Next run: {t.next_run_at}\n"
            return res
            
        elif tool_name == "cancelar_tarea_programada":
            task_id = tool_args.get("task_id")
            if not task_id:
                return "Error: task_id is required."
            deleted = await task_scheduler.delete_task(task_id)
            if deleted:
                return f"Task {task_id} successfully deleted."
            else:
                return f"Task {task_id} not found."
                
        elif tool_name == "pausar_reanudar_tarea":
            task_id = tool_args.get("task_id")
            status_str = tool_args.get("status")
            if not task_id or not status_str:
                return "Error: task_id and status are required."
                
            status = TaskStatus.ACTIVE if status_str == "ACTIVE" else TaskStatus.PAUSED
            updated = await task_scheduler.update_task_status(task_id, status)
            if updated:
                return f"Task {task_id} status updated to {status.value}."
            else:
                return f"Task {task_id} not found."
                
        else:
            return f"Unknown scheduler tool: {tool_name}"
            
    except Exception as e:
        return f"Error executing scheduler tool {tool_name}: {str(e)}"
