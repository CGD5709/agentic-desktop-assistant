"""
Summarize node responsible for translating technical tool execution outputs into natural responses.
"""
from typing import Any, Dict
from langchain_core.language_models.chat_models import BaseChatModel

from ..memory.async_manager import AsyncMemoryManager
from ..memory.profile_store import ProfileStore
from ..memory.short_term import SessionSummarizer
from ..memory.vector_store import VectorMemoryStore
from ..models import AgentState
from ..prompts import SUMMARIZE_PROMPT
from .base import BaseAgentNode, DEFAULT_MAX_DIALOGUE_TOKENS


class SummarizeNode(BaseAgentNode):
    """
    Synthesizes raw technical tool execution results into a refined, concise,
    and conversational response aligning with the Jarvis assistant persona.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        profile_store: ProfileStore,
        session_summarizer: SessionSummarizer,
        vector_store: VectorMemoryStore,
        memory_manager: AsyncMemoryManager,
        system_prompt: str = SUMMARIZE_PROMPT,
        max_dialogue_tokens: int = DEFAULT_MAX_DIALOGUE_TOKENS,
    ) -> None:
        """
        Initialize the summarize node with memory and LLM dependencies.

        Args:
            llm: Language model used for conversational response synthesis.
            profile_store: Relational profile storage (Tier 0).
            session_summarizer: Working memory summarizer (Tier 1).
            vector_store: Semantic vector memory store (Tier 2).
            memory_manager: Background asynchronous memory manager (Tier 3).
            system_prompt: Summarization instruction prompt.
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
        Execute synthesis of tool results into a polite and clear conversational answer.

        Args:
            state: Current agent state dictionary.

        Returns:
            Dictionary containing the synthesized assistant response message.
        """
        messages = list(state.get("messages", []))
        retrieved_memories = state.get("retrieved_memories") or []

        assembled_messages = await self._assemble_context(messages, retrieved_memories)
        response = await self._llm.ainvoke(assembled_messages)
        self._record_turn(messages, response)

        return {"messages": [response]}


__all__ = ["SummarizeNode"]
