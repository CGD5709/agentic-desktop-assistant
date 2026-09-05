"""
Command node responsible for processing technical tasks and invoking dynamic tools.
"""
from typing import Any, Dict, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage

from ..memory.async_manager import AsyncMemoryManager
from ..memory.profile_store import ProfileStore
from ..memory.short_term import SessionSummarizer
from ..memory.vector_store import VectorMemoryStore
from ..models import AgentState
from ..prompts import COMMAND_PROMPT
from .base import BaseAgentNode, DEFAULT_MAX_DIALOGUE_TOKENS


class CommandNode(BaseAgentNode):
    """
    Manages technical commands, system queries, and dynamic tool binding.
    Inherits multi-tier memory assembly and turn recording from BaseAgentNode.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        profile_store: ProfileStore,
        session_summarizer: SessionSummarizer,
        vector_store: VectorMemoryStore,
        memory_manager: AsyncMemoryManager,
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: str = COMMAND_PROMPT,
        max_dialogue_tokens: int = DEFAULT_MAX_DIALOGUE_TOKENS,
    ) -> None:
        """
        Initialize the command node with tool registry and memory dependencies.

        Args:
            llm: Language model supporting tool-calling capabilities.
            profile_store: Relational profile storage (Tier 0).
            session_summarizer: Working memory summarizer (Tier 1).
            vector_store: Semantic vector memory store (Tier 2).
            memory_manager: Background asynchronous memory manager (Tier 3).
            tools: List of dynamic tool schemas registered from external execution environments.
            system_prompt: Command instruction prompt enforcing tool execution.
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
        self._tools = tools if tools is not None else []

    async def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        Execute technical command reasoning and bind available tools.

        Args:
            state: Current agent state dictionary.

        Returns:
            Dictionary containing the generated AIMessage response.
        """
        messages = list(state.get("messages", []))
        retrieved_memories = state.get("retrieved_memories") or []

        assembled_messages = await self._assemble_context(messages, retrieved_memories)

        if self._tools:
            llm_with_tools = self._llm.bind_tools(self._tools)
            response = await llm_with_tools.ainvoke(assembled_messages)
        else:
            response = await self._llm.ainvoke(assembled_messages)

        # If no tool calls were requested, record conversational turn immediately.
        # Otherwise, the turn will be consolidated following tool execution in SummarizeNode.
        has_tool_calls = isinstance(response, AIMessage) and bool(response.tool_calls)
        if not has_tool_calls:
            self._record_turn(messages, response)

        return {"messages": [response]}


__all__ = ["CommandNode"]
