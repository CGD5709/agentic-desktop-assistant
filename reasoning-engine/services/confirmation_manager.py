"""
Confirmation manager service for Human-in-the-Loop (HITL) tool execution.
"""
import asyncio
from typing import Dict, Optional

from logger import get_logger

logger = get_logger("reasoning_engine.confirmation_manager")


class ConfirmationManager:
    """
    Thread-safe / asyncio manager tracking pending Human-in-the-Loop confirmation requests.
    Maps confirmation_id to asyncio.Future instances awaiting user approval from WebSocket clients.
    """

    def __init__(self) -> None:
        self._pending_confirmations: Dict[str, asyncio.Future[bool]] = {}

    def create_confirmation(self, confirmation_id: str) -> asyncio.Future[bool]:
        """
        Create and register a new pending confirmation Future for the given confirmation_id.

        Args:
            confirmation_id: Unique identifier for the confirmation request.

        Returns:
            An asyncio.Future resolving to True or False.
        """
        loop = asyncio.get_running_loop()
        future: asyncio.Future[bool] = loop.create_future()
        self._pending_confirmations[confirmation_id] = future
        logger.info("Registered pending HITL confirmation '%s'", confirmation_id)
        return future

    def resolve_confirmation(self, confirmation_id: str, confirmed: bool) -> bool:
        """
        Resolve a pending confirmation Future with the user's decision.

        Args:
            confirmation_id: The unique confirmation request ID.
            confirmed: True if approved, False if denied.

        Returns:
            True if the confirmation was found and resolved; False otherwise.
        """
        future = self._pending_confirmations.get(confirmation_id)
        if future is not None and not future.done():
            future.set_result(confirmed)
            logger.info(
                "Resolved HITL confirmation '%s' with result: %s",
                confirmation_id,
                "APPROVED" if confirmed else "DENIED",
            )
            return True

        logger.warning(
            "Attempted to resolve unknown or already completed confirmation: '%s'",
            confirmation_id,
        )
        return False

    def cancel_confirmation(self, confirmation_id: str) -> None:
        """
        Cancel a specific pending confirmation, resolving it to False.

        Args:
            confirmation_id: The unique confirmation request ID.
        """
        future = self._pending_confirmations.pop(confirmation_id, None)
        if future is not None and not future.done():
            future.set_result(False)
            logger.info("Cancelled pending HITL confirmation '%s'", confirmation_id)

    def cancel_all(self) -> None:
        """
        Cancel all active pending confirmations, resolving each to False.
        """
        count = len(self._pending_confirmations)
        if count == 0:
            return

        logger.info("Cancelling %d active pending confirmations...", count)
        for conf_id, future in list(self._pending_confirmations.items()):
            if not future.done():
                future.set_result(False)
        self._pending_confirmations.clear()

    def remove(self, confirmation_id: str) -> Optional[asyncio.Future[bool]]:
        """Remove a confirmation from tracking without modifying its state."""
        return self._pending_confirmations.pop(confirmation_id, None)


__all__ = ["ConfirmationManager"]
