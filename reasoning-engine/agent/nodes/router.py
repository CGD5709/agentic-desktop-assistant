"""
Router node responsible for semantic intent classification and conditional memory retrieval.
"""
from typing import Any, Dict, List
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from ..models import AgentState
from ..prompts import ROUTER_PROMPT
from ..utils import extract_last_human_text, is_simple_greeting_or_trivial
from ..memory.vector_store import VectorMemoryStore


class RouterNode:
    """
    Evaluates incoming user messages to determine intent (CHAT vs COMMAND)
    and conditionally retrieves relevant long-term memories from ChromaDB.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        vector_store: VectorMemoryStore,
        prompt: str = ROUTER_PROMPT,
    ) -> None:
        """
        Initializes the router node with required dependencies.

        Args:
            llm: Language model used for semantic zero-shot classification.
            vector_store: Vector store used for level 2 semantic retrieval.
            prompt: System instruction prompt guiding intent classification.
        """
        self._llm = llm
        self._vector_store = vector_store
        self._prompt = prompt

    async def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        Executes intent classification and semantic retrieval.

        Args:
            state: Current agent state dictionary.

        Returns:
            Dictionary with classified 'intent' and 'retrieved_memories'.
        """
        messages = list(state.get("messages", []))
        last_human_text = extract_last_human_text(messages)

        if not last_human_text.strip():
            return {"intent": "CHAT", "retrieved_memories": []}

        # Intent classification between CHAT and COMMAND
        classification_messages = [
            SystemMessage(content=self._prompt),
            HumanMessage(content=f"Mensaje del usuario: {last_human_text}"),
        ]

        classification = await self._llm.ainvoke(classification_messages)
        decision = (
            classification.content.strip().upper()
            if isinstance(classification.content, str)
            else "CHAT"
        )
        intent = "COMMAND" if "COMMAND" in decision else "CHAT"

        # Conditional semantic retrieval (Level 2)
        retrieved_memories: List[Dict[str, Any]] = []
        if not is_simple_greeting_or_trivial(last_human_text):
            raw_memories = await self._vector_store.search_memories(
                query=last_human_text,
                limit=3,
                score_threshold=0.60,
            )
            retrieved_memories = [m.model_dump(mode="json") for m in raw_memories]

        return {
            "intent": intent,
            "retrieved_memories": retrieved_memories,
        }
