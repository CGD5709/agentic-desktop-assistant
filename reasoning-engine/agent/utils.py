"""
Utility functions for text processing, message history parsing, and conversational heuristics.
"""
from typing import Final, Sequence
from langchain_core.messages import BaseMessage, HumanMessage

# Minimum character length below which standalone non-technical tokens are deemed trivial
MIN_TRIVIAL_CHAR_LENGTH: Final[int] = 4

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
    return normalized_text in TRIVIAL_CONVERSATIONAL_PHRASES or len(normalized_text) < MIN_TRIVIAL_CHAR_LENGTH


__all__ = [
    "MIN_TRIVIAL_CHAR_LENGTH",
    "PUNCTUATION_TO_STRIP",
    "TRIVIAL_CONVERSATIONAL_PHRASES",
    "extract_last_human_text",
    "is_simple_greeting_or_trivial",
]
