"""
Base node abstractions, shared dependencies, and graph enumeration constants.
"""
from enum import Enum
from typing import Any, Dict, Final, List, Optional, Sequence
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage

from ..memory.async_manager import AsyncMemoryManager
from ..memory.context_assembler import ContextAssembler
from ..memory.profile_store import ProfileStore
from ..memory.short_term import SessionSummarizer
from ..memory.vector_store import VectorMemoryStore
from ..utils import extract_last_human_text

# Default token budget for conversational history truncation across nodes
DEFAULT_MAX_DIALOGUE_TOKENS: Final[int] = 3000


class NodeName(str, Enum):
    """Canonical identifier names for graph nodes and terminal states."""
    ROUTER = "router_node"
    CHAT = "chat_node"
    COMMAND = "command_node"
    ACTION = "action_node"
    SUMMARIZE = "summarize_node"
    END = "end"


class Intent(str, Enum):
    """Categorical classification of user intent."""
    CHAT = "CHAT"
    COMMAND = "COMMAND"


class BaseAgentNode:
    """
    Abstract base class providing shared multi-tier memory integration,
    context assembly, and asynchronous turn persistence for conversational nodes.
    """

    # TODO: Integrate centralized logging framework across agent nodes once standardized.

    def __init__(
        self,
        llm: BaseChatModel,
        profile_store: ProfileStore,
        session_summarizer: SessionSummarizer,
        vector_store: VectorMemoryStore,
        memory_manager: AsyncMemoryManager,
        system_prompt: str,
        max_dialogue_tokens: int = DEFAULT_MAX_DIALOGUE_TOKENS,
    ) -> None:
        """
        Initialize base node dependencies.

        Args:
            llm: Language model used for generation.
            profile_store: Relational profile storage (Level 0).
            session_summarizer: Working memory summarizer (Level 1).
            vector_store: Semantic vector memory store (Level 2).
            memory_manager: Background asynchronous memory manager (Level 3).
            system_prompt: Base instruction prompt for the node.
            max_dialogue_tokens: Maximum token budget for conversational history.
        """
        self._llm = llm
        self._profile_store = profile_store
        self._session_summarizer = session_summarizer
        self._vector_store = vector_store
        self._memory_manager = memory_manager
        self._system_prompt = system_prompt
        self._max_dialogue_tokens = max_dialogue_tokens

    async def _assemble_context(
        self,
        messages: List[BaseMessage],
        retrieved_memories: Optional[List[Dict[str, Any]]] = None,
    ) -> List[BaseMessage]:
        """
        Fetch profile and session memory layers, then assemble the 4-tier conversational context.

        Args:
            messages: Current conversation messages.
            retrieved_memories: Optional semantically retrieved memory dicts.

        Returns:
            List of assembled and token-budgeted BaseMessage instances.
        """
        profile_context = await self._profile_store.format_for_context()
        session_context = self._session_summarizer.get_summary_context()

        return ContextAssembler.assemble(
            base_system_prompt=self._system_prompt,
            messages=messages,
            profile_context=profile_context,
            retrieved_memories=retrieved_memories or [],
            session_summary_context=session_context,
            max_dialogue_tokens=self._max_dialogue_tokens,
            memory_store_formatter=self._vector_store.format_for_context,
        )

    def _record_turn(
        self,
        messages: Sequence[BaseMessage],
        assistant_response: Any,
    ) -> None:
        """
        Record the user and assistant turns into the asynchronous memory consolidation queue.

        Args:
            messages: Conversation history containing the last user turn.
            assistant_response: Response object containing assistant text content.
        """
        last_human_text = extract_last_human_text(messages)
        content = getattr(assistant_response, "content", "")
        assistant_text = content if isinstance(content, str) else ""

        self._memory_manager.record_turn(role="user", content=last_human_text)
        self._memory_manager.record_turn(role="assistant", content=assistant_text)


__all__ = [
    "DEFAULT_MAX_DIALOGUE_TOKENS",
    "NodeName",
    "Intent",
    "BaseAgentNode",
]
