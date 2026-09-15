"""
Centralized logging subsystem providing structured formatting, colorized console output,
and asynchronous context propagation (Correlation ID / Session ID) across the Reasoning Engine.
"""
import contextvars
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Async context variables for distributed request tracing
correlation_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)
session_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "session_id", default=None
)


def set_log_context(
    correlation_id: Optional[str] = None, session_id: Optional[str] = None
) -> None:
    """Sets the active correlation and session IDs for the current asynchronous context."""
    if correlation_id is not None:
        correlation_id_ctx.set(correlation_id)
    if session_id is not None:
        session_id_ctx.set(session_id)


def clear_log_context() -> None:
    """Clears the active correlation and session IDs from the current context."""
    correlation_id_ctx.set(None)
    session_id_ctx.set(None)


class ContextLogFilter(logging.Filter):
    """Logging filter that enriches every LogRecord with correlation_id and session_id attributes."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_ctx.get() or "-"
        record.session_id = session_id_ctx.get() or "-"
        return True


class ColorizedConsoleFormatter(logging.Formatter):
    """
    ANSI-colorized console log formatter for local development readability.
    Includes timestamps, level badges, module names, and tracing context.
    """

    # ANSI escape sequences
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    COLORS = {
        logging.DEBUG: "\033[36m",     # Cyan
        logging.INFO: "\033[32m",      # Green
        logging.WARNING: "\033[33m",   # Yellow
        logging.ERROR: "\033[31m",     # Red
        logging.CRITICAL: "\033[1;31m",# Bold Red
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, self.RESET)
        time_str = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S.%f"
        )[:-3]

        corr_id = getattr(record, "correlation_id", "-")
        context_str = f" [corrId={corr_id}]" if corr_id != "-" else ""

        level_name = f"{record.levelname:<5}"
        log_line = (
            f"{self.DIM}{time_str}{self.RESET} "
            f"{color}{self.BOLD}{level_name}{self.RESET} "
            f"\033[35m[{record.name}]{self.RESET}"
            f"\033[33m{context_str}\033[0m - "
            f"{record.getMessage()}"
        )

        if record.exc_info:
            log_line += "\n" + self.formatException(record.exc_info)
        return log_line


class JSONStructuredFormatter(logging.Formatter):
    """
    Structured JSON log formatter for production environments, ELK, Datadog, or Loki ingestion.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "service": "reasoning-engine",
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", None),
            "session_id": getattr(record, "session_id", None),
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(level_name: str = "INFO", log_format: str = "console") -> None:
    """
    Configures root logging, handlers, and formats for the entire application.

    Args:
        level_name: Log level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL').
        log_format: Formatter style ('console' or 'json').
    """
    numeric_level = getattr(logging, level_name.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove pre-existing handlers to prevent duplicated output
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.addFilter(ContextLogFilter())

    if log_format.lower() == "json":
        console_handler.setFormatter(JSONStructuredFormatter())
    else:
        console_handler.setFormatter(ColorizedConsoleFormatter())

    root_logger.addHandler(console_handler)

    # Align uvicorn and third-party loggers
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        uv_logger = logging.getLogger(logger_name)
        uv_logger.handlers = []
        uv_logger.propagate = True


def get_logger(name: str) -> logging.Logger:
    """Convenience helper to obtain a named logger."""
    return logging.getLogger(name)
