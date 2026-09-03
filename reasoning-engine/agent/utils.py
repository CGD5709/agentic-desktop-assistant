"""
Utility functions for text processing, message history parsing, and greeting heuristics.
"""
from typing import Sequence
from langchain_core.messages import BaseMessage, HumanMessage


def extract_last_human_text(messages: Sequence[BaseMessage]) -> str:
    """
    Traverses dialogue messages in reverse order to find and extract the text content
    of the most recent HumanMessage. Supports both string and multipart list content.
    
    Args:
        messages: A sequence of BaseMessage instances representing conversation history.
        
    Returns:
        The extracted string content of the last human message, or empty string if none found.
    """
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            if isinstance(msg.content, str):
                return msg.content
            elif isinstance(msg.content, list):
                return " ".join(c if isinstance(c, str) else "" for c in msg.content)
    return ""


def is_simple_greeting_or_trivial(text: str) -> bool:
    """
    Determines whether the provided text is a simple greeting, acknowledgement,
    farewell, or otherwise trivial conversational phrase that does not warrant semantic retrieval.
    
    Args:
        text: Input string from the user.
        
    Returns:
        True if the text is classified as trivial or a simple greeting; False otherwise.
    """
    t = text.strip().lower()
    trivial_words = {
        "hola", "buenas", "buenos días", "buenas tardes", "buenas noches",
        "hey", "hi", "gracias", "adiós", "chao", "bye", "ok", "vale", "jaja"
    }
    return t in trivial_words or len(t) < 4
