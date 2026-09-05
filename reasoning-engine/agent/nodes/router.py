"""
Router node responsible for semantic intent classification and conditional memory retrieval.
"""
from typing import Any, Dict, Final, List
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from ..memory.vector_store import VectorMemoryStore
from ..models import AgentState
from ..prompts import ROUTER_PROMPT
from ..utils import extract_last_human_text, is_simple_greeting_or_trivial
from .base import Intent

# Default vector store retrieval limit for intent routing
DEFAULT_RETRIEVAL_LIMIT: Final[int] = 3

# Default similarity score threshold for relevant long-term memory retrieval
DEFAULT_SCORE_THRESHOLD: Final[float] = 0.60


class RouterNode:
    """
    Evaluates incoming user messages to classify intent (CHAT or COMMAND)
    and conditionally queries long-term vector memory when contextually relevant.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        vector_store: VectorMemoryStore,
        prompt: str = ROUTER_PROMPT,
        retrieval_limit: int = DEFAULT_RETRIEVAL_LIMIT,
        score_threshold: float = DEFAULT_SCORE_THRESHOLD,
    ) -> None:
        """
        Initialize the router node.

        Args:
            llm: Language model used for zero-shot intent classification.
            vector_store: Semantic vector memory store.
            prompt: System instruction guiding classification.
            retrieval_limit: Maximum number of vector memory items to retrieve.
            score_threshold: Minimum cosine similarity score required for retrieved memories.
        """
        self._llm = llm
        self._vector_store = vector_store
        self._prompt = prompt
        self._retrieval_limit = retrieval_limit
        self._score_threshold = score_threshold

    async def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        Execute intent classification and conditional semantic retrieval.

        Args:
            state: Current agent state dictionary.

        Returns:
            Dictionary containing classified 'intent' and 'retrieved_memories'.
        """
        messages = list(state.get("messages", []))
        last_human_text = extract_last_human_text(messages)

        if not last_human_text.strip():
            return {
                "intent": Intent.CHAT.value,
                "retrieved_memories": [],
            }

        classification_messages = [
            SystemMessage(content=self._prompt),
            HumanMessage(content=f"Mensaje del usuario: {last_human_text}"),
        ]

        classification = await self._llm.ainvoke(classification_messages)
        decision = (
            classification.content.strip().upper()
            if isinstance(classification.content, str)
            else Intent.CHAT.value
        )
        intent = Intent.COMMAND.value if Intent.COMMAND.value in decision else Intent.CHAT.value

        # TODO: Log classification decisions and vector retrieval outcomes once logger is configured.

        # Conditional semantic retrieval (Level 2)
        retrieved_memories: List[Dict[str, Any]] = []
        if not is_simple_greeting_or_trivial(last_human_text):
            raw_memories = await self._vector_store.search_memories(
                query=last_human_text,
                limit=self._retrieval_limit,
                score_threshold=self._score_threshold,
            )
            retrieved_memories = [m.model_dump(mode="json") for m in raw_memories]

        return {
            "intent": intent,
            "retrieved_memories": retrieved_memories,
        }


__all__ = [
    "DEFAULT_RETRIEVAL_LIMIT",
    "DEFAULT_SCORE_THRESHOLD",
    "RouterNode",
]
