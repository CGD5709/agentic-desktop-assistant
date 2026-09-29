"""
Utility functions for text processing, message history parsing, and conversational heuristics.
"""
from typing import Final, Sequence
from langchain_core.messages import BaseMessage, HumanMessage

# Punctuation marks stripped during trivial text normalization
PUNCTUATION_TO_STRIP: Final[str] = ".!¡?¿,;:…"

# Normalized set of conversational greetings, acknowledgements, and farewells
TRIVIAL_CONVERSATIONAL_PHRASES: Final[frozenset[str]] = frozenset({
    # Greetings
    "hola", "buenas", "buenos días", "buenos dias", "buenas tardes", "buenas noches",
    "hey", "hi", "hello", "holis", "qué tal", "que tal", "alo", "aló", "saludos",
    
    # Farewells
    "adiós", "adios", "chao", "chau", "bye", "bye bye", "nos vemos", 
    "hasta luego", "hasta pronto", "hasta mañana", "ciao", "chao chao",
    
    # Gratitude & Courtesy
    "gracias", "muchas gracias", "mil gracias", "te lo agradezco", "thx", "ty", "thanks",
    "de nada", "no hay de qué", "no hay de que", "un placer",
    
    # Acknowledgements & Affirmations
    "ok", "oki", "okis", "okey", "vale", "perfecto", "genial", "guay", "entendido", 
    "de acuerdo", "claro", "exacto", "eso es", "sí", "si", "sip", "sisi", "yes", 
    "yep", "yup", "obvio", "estupendo", "maravilloso", "listo", "perfe",
    
    # Negations
    "no", "nop", "nah", "nanai",
    
    # Laughter & Reactions
    "jaja", "jajaja", "jajajaja", "jeje", "jejeje", "xd", "xdd", "xddd", "lol", "lmao",
    
    # Fillers & Politeness markers
    "bueno", "pues", "a ver", "hmm", "umm", "eh", "por favor", "plis", "pls", "porfa"
})


def extract_last_human_text(messages: Sequence[BaseMessage]) -> str:
    """
    Traverse dialogue messages in reverse order to extract the text content of the most recent HumanMessage.

    Supports both standard string payloads and multipart list structures (including dict blocks with a 'text' key).

    Args:
        messages: Sequence of BaseMessage instances representing conversational history.

    Returns:
        The extracted string content of the latest human message, or an empty string if none is found.
    """
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            if isinstance(msg.content, str):
                return msg.content
            if isinstance(msg.content, list):
                extracted_parts: list[str] = []
                for item in msg.content:
                    if isinstance(item, str):
                        extracted_parts.append(item)
                    elif isinstance(item, dict) and "text" in item and isinstance(item["text"], str):
                        extracted_parts.append(item["text"])
                return " ".join(part for part in extracted_parts if part)
    return ""


def is_simple_greeting_or_trivial(text: str) -> bool:
    """
    Determine whether the provided text is a greeting, farewell, acknowledgement, or trivial utterance.

    Trivial conversational inputs do not warrant semantic vector memory retrieval.

    Args:
        text: Raw input string from the user.

    Returns:
        True if the text is classified as trivial conversational filler; False otherwise.
    """
    normalized_text = text.strip().lower().strip(PUNCTUATION_TO_STRIP)
    if not normalized_text:
        return True
    return normalized_text in TRIVIAL_CONVERSATIONAL_PHRASES


def format_recent_history(
    messages: Sequence[BaseMessage],
    max_messages: int = 6,
    max_content_length: int = 300,
) -> str:
    """
    Format recent conversational history leading up to the current turn into a dialogue string.

    Excludes system messages and the final HumanMessage (the active input being classified).

    Args:
        messages: Full sequence of messages from the agent state.
        max_messages: Maximum number of preceding dialogue messages to include.
        max_content_length: Truncation threshold for lengthy assistant/tool responses.

    Returns:
        Formatted multi-turn dialogue string, or empty string if no preceding history exists.
    """
    from langchain_core.messages import AIMessage, SystemMessage, ToolMessage

    if not messages:
        return ""

    # Find the index of the last HumanMessage in the sequence
    last_human_idx = -1
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], HumanMessage):
            last_human_idx = i
            break

    if last_human_idx <= 0:
        # No prior messages before the active human prompt
        return ""

    # Filter out SystemMessages and slice the most recent dialogue turns
    prior_messages = [
        msg for msg in messages[:last_human_idx]
        if not isinstance(msg, SystemMessage)
    ]

    if not prior_messages:
        return ""

    selected = prior_messages[-max_messages:]
    formatted_lines: list[str] = []

    for msg in selected:
        if isinstance(msg, HumanMessage):
            text = extract_last_human_text([msg])
            if text:
                formatted_lines.append(f"Usuario: {text}")
        elif isinstance(msg, AIMessage):
            content = msg.content if isinstance(msg.content, str) else ""
            if msg.tool_calls:
                tool_names = ", ".join(
                    tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
                    for tc in msg.tool_calls
                )
                if content:
                    content_preview = (
                        content[:max_content_length] + "..."
                        if len(content) > max_content_length
                        else content
                    )
                    formatted_lines.append(f"Asistente: {content_preview} [Llamada a herramienta: {tool_names}]")
                else:
                    formatted_lines.append(f"Asistente: [Llamada a herramienta: {tool_names}]")
            elif content:
                content_preview = (
                    content[:max_content_length] + "..."
                    if len(content) > max_content_length
                    else content
                )
                formatted_lines.append(f"Asistente: {content_preview}")
        elif isinstance(msg, ToolMessage):
            tool_content = str(msg.content or "")
            preview = (
                tool_content[:max_content_length] + "..."
                if len(tool_content) > max_content_length
                else tool_content
            )
            formatted_lines.append(f"[Resultado de herramienta: {preview}]")

    return "\n".join(formatted_lines)


__all__ = [
    "PUNCTUATION_TO_STRIP",
    "TRIVIAL_CONVERSATIONAL_PHRASES",
    "extract_last_human_text",
    "format_recent_history",
    "is_simple_greeting_or_trivial",
]

