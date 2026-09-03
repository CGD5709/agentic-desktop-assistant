from typing import List, Sequence, Optional, Any, Callable, Union
from langchain_core.messages import BaseMessage, SystemMessage
from .short_term import trim_messages_token_budget
from .models import MemoryItem

# Default token allocation for dynamic dialogue history pruning
DEFAULT_MAX_DIALOGUE_TOKENS = 3000


def _default_memory_formatter(memories: Sequence[Union[MemoryItem, Any]]) -> str:
    """
    Formats a sequence of retrieved memory items into standard XML-tagged context.
    Acts as a fallback formatter when a custom store-specific formatter is not provided.

    Args:
        memories: Sequence of MemoryItem instances or dictionary representations.

    Returns:
        str: Formatted context block wrapped in XML tags, or empty string if no items.
    """
    if not memories:
        return ""

    lines = ["<auxiliary_context>", "Información relevante recuperada de sesiones anteriores:"]
    for mem in memories:
        text = mem.get("text", "") if isinstance(mem, dict) else getattr(mem, "text", "")
        if text:
            lines.append(f"- {text}")
    lines.append("</auxiliary_context>")
    return "\n".join(lines)


class ContextAssembler:
    """
    Unified Multi-Tier Context Assembler.

    Consolidates and structures all 4 memory tiers into an optimized message payload for LLM inference:
    1. Base System Prompt (Persona, operational boundaries, tool rules).
    2. User Profile Store (Level 0: Deterministic user facts and preferences).
    3. Long-Term Semantic Memory (Level 2: RAG retrieved cross-session items).
    4. Session Summary (Level 1: Compact synthesis of previous dialogue turns).
    5. Pruned Dialogue History (Level 1: Recent turns bounded by token budget).
    """

    @staticmethod
    def assemble(
        base_system_prompt: str,
        messages: Sequence[BaseMessage],
        profile_context: Optional[str] = None,
        retrieved_memories: Optional[Sequence[Any]] = None,
        session_summary_context: Optional[str] = None,
        max_dialogue_tokens: int = DEFAULT_MAX_DIALOGUE_TOKENS,
        memory_store_formatter: Optional[Callable[[Sequence[Any]], str]] = None
    ) -> List[BaseMessage]:
        """
        Constructs the final, structured sequence of messages for LLM invocation.

        Merges all system prompt layers into a single consolidated SystemMessage header,
        followed by atomic, token-budgeted conversation history.

        Args:
            base_system_prompt: Core system prompt containing agent persona and instructions.
            messages: Full conversation dialogue history to be trimmed.
            profile_context: Pre-formatted XML-tagged profile block (Level 0).
            retrieved_memories: Collection of semantic memory items retrieved via RAG (Level 2).
            session_summary_context: Pre-formatted XML-tagged session summary block (Level 1).
            max_dialogue_tokens: Maximum token budget allocated for pruned dialogue history.
            memory_store_formatter: Optional callback function to format retrieved memories.

        Returns:
            List[BaseMessage]: Ordered message sequence ready for direct model invocation.
        """
        system_sections: List[str] = []
        if base_system_prompt and base_system_prompt.strip():
            system_sections.append(base_system_prompt.strip())

        # Layer 1: Structured User Profile (Level 0)
        if profile_context and profile_context.strip():
            system_sections.append(profile_context.strip())

        # Layer 2: Long-Term Semantic Memories (Level 2)
        if retrieved_memories:
            formatter = memory_store_formatter or _default_memory_formatter
            mem_str = formatter(retrieved_memories)
            if mem_str and mem_str.strip():
                system_sections.append(mem_str.strip())

        # Layer 3: Session Summary Synthesis (Level 1)
        if session_summary_context and session_summary_context.strip():
            system_sections.append(session_summary_context.strip())

        # Consolidate all system sections into a single initial SystemMessage
        full_system_message = SystemMessage(content="\n\n".join(system_sections))

        # Layer 4: Prune recent dialogue within token budget while preserving tool call atomicity (Level 1)
        trimmed_dialogue = trim_messages_token_budget(
            messages=messages,
            max_tokens=max_dialogue_tokens,
            keep_system_messages=False
        )

        return [full_system_message] + list(trimmed_dialogue)
