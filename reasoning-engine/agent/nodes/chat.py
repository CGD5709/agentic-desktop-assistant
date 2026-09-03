"""
Chat node responsible for conversational dialogue with 4-tier context assembly.
"""
from typing import Any, Dict
from langchain_core.language_models.chat_models import BaseChatModel

from ..models import AgentState
from ..prompts import JARVIS_SYSTEM_PROMPT
from ..utils import extract_last_human_text
from ..memory.profile_store import ProfileStore
from ..memory.vector_store import VectorMemoryStore
from ..memory.short_term import SessionSummarizer
from ..memory.async_manager import AsyncMemoryManager
from ..memory.context_assembler import ContextAssembler


class ChatNode:
    """
    Handles general conversational exchanges for the Jarvis assistant.
    Assembles a consolidated 4-tier memory context (system persona, profile,
    retrieved RAG memories, session summary, and trimmed history).
    """

    def __init__(
        self,
        llm: BaseChatModel,
        profile_store: ProfileStore,
        session_summarizer: SessionSummarizer,
        vector_store: VectorMemoryStore,
        memory_manager: AsyncMemoryManager,
        system_prompt: str = JARVIS_SYSTEM_PROMPT,
        max_dialogue_tokens: int = 3000,
    ) -> None:
        """
        Initializes the chat node with injected dependencies.

        Args:
            llm: Language model used for generation.
            profile_store: Relational profile storage (Tier 0).
            session_summarizer: Working memory summarizer (Tier 1).
            vector_store: Semantic vector memory store (Tier 2).
            memory_manager: Background asynchronous memory manager (Tier 3).
            system_prompt: Base persona system prompt.
            max_dialogue_tokens: Maximum token budget for conversational history.
        """
        self._llm = llm
        self._profile_store = profile_store
        self._session_summarizer = session_summarizer
        self._vector_store = vector_store
        self._memory_manager = memory_manager
        self._system_prompt = system_prompt
        self._max_dialogue_tokens = max_dialogue_tokens

    async def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        Executes conversational turn generation with assembled memory context.

        Args:
            state: Current agent state dictionary.

        Returns:
            Dictionary with generated messages list.
        """
        messages = list(state.get("messages", []))
        retrieved_memories = state.get("retrieved_memories") or []

        # Level 0: Persistent Profile
        profile_ctx = await self._profile_store.format_for_context()
        # Level 1: Working Session Summary
        summary_ctx = self._session_summarizer.get_summary_context()

        # Assemble clean 4-tier context
        assembled_messages = ContextAssembler.assemble(
            base_system_prompt=self._system_prompt,
            messages=messages,
            profile_context=profile_ctx,
            retrieved_memories=retrieved_memories,
            session_summary_context=summary_ctx,
            max_dialogue_tokens=self._max_dialogue_tokens,
            memory_store_formatter=self._vector_store.format_for_context,
        )

        response = await self._llm.ainvoke(assembled_messages)

        # Record turns in background for asynchronous memory extraction (Level 3)
        last_human_text = extract_last_human_text(messages)
        assistant_text = response.content if isinstance(response.content, str) else ""
        self._memory_manager.record_turn(role="user", content=last_human_text)
        self._memory_manager.record_turn(role="assistant", content=assistant_text)

        return {"messages": [response]}
