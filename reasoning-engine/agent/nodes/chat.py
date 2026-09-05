"""
Chat node responsible for conversational dialogue with 4-tier context assembly.
"""
from typing import Any, Dict
from langchain_core.language_models.chat_models import BaseChatModel

from ..memory.async_manager import AsyncMemoryManager
from ..memory.profile_store import ProfileStore
from ..memory.short_term import SessionSummarizer
from ..memory.vector_store import VectorMemoryStore
from ..models import AgentState
from ..prompts import JARVIS_SYSTEM_PROMPT
from .base import BaseAgentNode, DEFAULT_MAX_DIALOGUE_TOKENS


class ChatNode(BaseAgentNode):
    """
    Handles general conversational exchanges for the Jarvis assistant.
    Inherits multi-tier memory assembly and asynchronous turn recording from BaseAgentNode.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        profile_store: ProfileStore,
        session_summarizer: SessionSummarizer,
        vector_store: VectorMemoryStore,
        memory_manager: AsyncMemoryManager,
        system_prompt: str = JARVIS_SYSTEM_PROMPT,
        max_dialogue_tokens: int = DEFAULT_MAX_DIALOGUE_TOKENS,
    ) -> None:
        """
        Initialize the chat node with required memory and LLM dependencies.

        Args:
            llm: Language model used for conversational generation.
            profile_store: Relational profile storage (Level 0).
            session_summarizer: Working memory summarizer (Level 1).
            vector_store: Semantic vector memory store (Level 2).
            memory_manager: Background asynchronous memory manager (Level 3).
            system_prompt: Base persona system prompt.
            max_dialogue_tokens: Maximum token budget for conversational history.
        """
        super().__init__(
            llm=llm,
            profile_store=profile_store,
            session_summarizer=session_summarizer,
            vector_store=vector_store,
            memory_manager=memory_manager,
            system_prompt=system_prompt,
            max_dialogue_tokens=max_dialogue_tokens,
        )

    async def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        Execute conversational turn generation with assembled memory context.

        Args:
            state: Current agent state dictionary.

        Returns:
            Dictionary containing the generated assistant response message list.
        """
        messages = list(state.get("messages", []))
        retrieved_memories = state.get("retrieved_memories") or []

        assembled_messages = await self._assemble_context(messages, retrieved_memories)
        response = await self._llm.ainvoke(assembled_messages)
        self._record_turn(messages, response)

        return {"messages": [response]}


__all__ = ["ChatNode"]
