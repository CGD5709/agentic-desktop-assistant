"""
Command node responsible for processing technical tasks and invoking dynamic tools.
"""
from typing import Any, Dict, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage

from ..models import AgentState
from ..prompts import COMMAND_PROMPT
from ..utils import extract_last_human_text
from ..memory.profile_store import ProfileStore
from ..memory.vector_store import VectorMemoryStore
from ..memory.short_term import SessionSummarizer
from ..memory.async_manager import AsyncMemoryManager
from ..memory.context_assembler import ContextAssembler


class CommandNode:
    """
    Manages technical commands, system queries, and dynamic tool binding.
    Assembles contextual memory layers with specialized tool invocation instructions.
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
        max_dialogue_tokens: int = 3000,
    ) -> None:
        """
        Initializes the command node with injected dependencies.

        Args:
            llm: Language model supporting tool-calling capabilities.
            profile_store: Relational profile storage (Tier 0).
            session_summarizer: Working memory summarizer (Tier 1).
            vector_store: Semantic vector memory store (Tier 2).
            memory_manager: Background asynchronous memory manager (Tier 3).
            tools: Dynamic tools list registered from external execution environments.
            system_prompt: Command instruction prompt enforcing tool execution.
            max_dialogue_tokens: Maximum token budget for conversational history.
        """
        self._llm = llm
        self._profile_store = profile_store
        self._session_summarizer = session_summarizer
        self._vector_store = vector_store
        self._memory_manager = memory_manager
        self._tools = tools if tools is not None else []
        self._system_prompt = system_prompt
        self._max_dialogue_tokens = max_dialogue_tokens

    async def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        Executes technical command reasoning and binds available tools.

        Args:
            state: Current agent state dictionary.

        Returns:
            Dictionary with generated messages list containing AIMessage.
        """
        messages = list(state.get("messages", []))
        retrieved_memories = state.get("retrieved_memories") or []

        profile_ctx = await self._profile_store.format_for_context()
        summary_ctx = self._session_summarizer.get_summary_context()

        assembled_messages = ContextAssembler.assemble(
            base_system_prompt=self._system_prompt,
            messages=messages,
            profile_context=profile_ctx,
            retrieved_memories=retrieved_memories,
            session_summary_context=summary_ctx,
            max_dialogue_tokens=self._max_dialogue_tokens,
            memory_store_formatter=self._vector_store.format_for_context,
        )

        if self._tools:
            llm_with_tools = self._llm.bind_tools(self._tools)
            response = await llm_with_tools.ainvoke(assembled_messages)
        else:
            response = await self._llm.ainvoke(assembled_messages)

        # If no tools were invoked, record turn immediately in memory manager
        if not (isinstance(response, AIMessage) and response.tool_calls):
            last_human_text = extract_last_human_text(messages)
            assistant_text = response.content if isinstance(response.content, str) else ""
            self._memory_manager.record_turn(role="user", content=last_human_text)
            self._memory_manager.record_turn(role="assistant", content=assistant_text)

        return {"messages": [response]}
