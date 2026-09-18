"""
Voice cleaner and text sanitizer module.

Transforms formatted Markdown and technical outputs into clean, natural,
and fluent phrasing optimized for Text-to-Speech (TTS) voice engines.
"""
import re
from typing import Final

# Regex pattern matching Markdown fenced code blocks (```lang ... ```)
CODE_BLOCK_PATTERN: Final[re.Pattern[str]] = re.compile(r"```[\s\S]*?```", re.MULTILINE)

# Regex matching inline code spans (`code`)
INLINE_CODE_PATTERN: Final[re.Pattern[str]] = re.compile(r"`([^`]+)`")

# Regex matching Markdown table structures (| col | col |)
TABLE_PATTERN: Final[re.Pattern[str]] = re.compile(r"(\|[^\n]+\|\r?\n)+", re.MULTILINE)

# Regex matching Markdown links [text](url) -> text
LINK_PATTERN: Final[re.Pattern[str]] = re.compile(r"\[([^\]]+)\]\([^\)]+\)")

# Regex matching Markdown headers (#, ##, ###)
HEADER_PATTERN: Final[re.Pattern[str]] = re.compile(r"^#{1,6}\s*", re.MULTILINE)

# Regex matching list bullets (- *, 1.)
BULLET_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\s*[-*+]\s+", re.MULTILINE)
NUMBERED_LIST_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\s*\d+\.\s+", re.MULTILINE)

# Regex matching bold/italic/strikethrough markers (**, *, ~~, __)
STYLE_PATTERN: Final[re.Pattern[str]] = re.compile(r"[*_~]{1,3}")

# Regex matching common emojis and non-alphanumeric pictographs
EMOJI_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"[\U00010000-\U0010ffff\u2600-\u26FF\u2700-\u27BF]",
    flags=re.UNICODE,
)

# Regex matching multiple consecutive whitespace/newlines
MULTI_SPACE_PATTERN: Final[re.Pattern[str]] = re.compile(r"[ \t]+")
MULTI_NEWLINE_PATTERN: Final[re.Pattern[str]] = re.compile(r"\n{2,}")


def clean_text_for_speech(raw_text: str) -> str:
    """
    Sanitize a rich Markdown assistant response into natural spoken dialogue.

    Args:
        raw_text: Full response string containing potential Markdown, code blocks,
                  tables, emojis, and styling artifacts.

    Returns:
        Spoken-ready string suitable for TTS audio engines.
    """
    if not raw_text or not raw_text.strip():
        return ""

    text = raw_text

    # 1. Replace multiline code blocks with a brief spoken notice
    if CODE_BLOCK_PATTERN.search(text):
        text = CODE_BLOCK_PATTERN.sub(". He generado el código correspondiente en pantalla. ", text)

    # 2. Simplify inline code
    text = INLINE_CODE_PATTERN.sub(r"\1", text)

    # 3. Replace markdown tables with a spoken reference notice
    if TABLE_PATTERN.search(text):
        text = TABLE_PATTERN.sub(". Los datos detallados se muestran en la tabla en pantalla. ", text)

    # 4. Extract link texts, discard URLs
    text = LINK_PATTERN.sub(r"\1", text)

    # 5. Remove markdown headers and list formatting
    text = HEADER_PATTERN.sub("", text)
    text = BULLET_PATTERN.sub("", text)
    text = NUMBERED_LIST_PATTERN.sub("", text)

    # 6. Remove styling tags (*, **, _, ~~)
    text = STYLE_PATTERN.sub("", text)

    # 7. Remove visual emojis
    text = EMOJI_PATTERN.sub("", text)

    # 8. Clean up extra whitespaces and punctuation artifacts
    text = MULTI_SPACE_PATTERN.sub(" ", text)
    text = MULTI_NEWLINE_PATTERN.sub(". ", text)

    # 9. Clean up repetitive periods or commas
    text = re.sub(r"\.{2,}", ".", text)
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)

    return text.strip()
