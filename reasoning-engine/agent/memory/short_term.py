import json
from typing import List, Optional, Sequence, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage


MESSAGE_OVERHEAD_TOKENS = 4
FALLBACK_CHARS_PER_TOKEN = 4

try:
    import tiktoken
    _enc = tiktoken.get_encoding("cl100k_base")

    def count_tokens(text: str) -> int:
        if not text:
            return 0
        return len(_enc.encode(str(text)))
except ImportError:
    def count_tokens(text: str) -> int:
        if not text:
            return 0
        return max(1, len(str(text)) // FALLBACK_CHARS_PER_TOKEN)


def count_message_tokens(msg: BaseMessage) -> int:
    """
    Estimates the token count of a LangChain message.
    Accounts for content length, nested tool calls, and ChatML formatting overhead.
    """
    tokens = MESSAGE_OVERHEAD_TOKENS
    
    if isinstance(msg.content, str):
        tokens += count_tokens(msg.content)
    elif isinstance(msg.content, list):
        for part in msg.content:
            if isinstance(part, str):
                tokens += count_tokens(part)
            elif isinstance(part, dict):
                tokens += count_tokens(json.dumps(part, ensure_ascii=False))
            else:
                tokens += count_tokens(str(part))
    elif msg.content is not None:
        tokens += count_tokens(str(msg.content))

    # Account for tool invocation overhead
    if isinstance(msg, AIMessage) and msg.tool_calls:
        tokens += count_tokens(json.dumps(msg.tool_calls, ensure_ascii=False))
    elif isinstance(msg, ToolMessage) and msg.tool_call_id:
        tokens += count_tokens(str(msg.tool_call_id))

    return tokens


def count_total_tokens(messages: Sequence[BaseMessage]) -> int:
    """
    Calculates the aggregate token count for a sequence of messages.
    """
    return sum(count_message_tokens(m) for m in messages)


def group_atomic_message_blocks(messages: Sequence[BaseMessage]) -> List[List[BaseMessage]]:
    """
    Groups messages into indivisible atomic blocks to maintain structural integrity.
    Ensures that an AIMessage containing tool_calls and its subsequent ToolMessages
    are treated as a single cohesive unit during context pruning.
    """
    blocks: List[List[BaseMessage]] = []
    i = 0
    n = len(messages)

    while i < n:
        msg = messages[i]
        
        # Identify an AI tool invocation and group it with its responses
        if isinstance(msg, AIMessage) and msg.tool_calls:
            block: List[BaseMessage] = [msg]
            tool_call_ids = set()
            for tc in msg.tool_calls:
                if isinstance(tc, dict) and tc.get("id"):
                    tool_call_ids.add(tc["id"])
                elif hasattr(tc, "id") and getattr(tc, "id", None):
                    tool_call_ids.add(getattr(tc, "id"))

            j = i + 1
            while j < n:
                next_msg = messages[j]
                if not isinstance(next_msg, ToolMessage):
                    break

                # Match tool responses by ID and append consecutively
                tool_call_id = getattr(next_msg, "tool_call_id", None)
                if not tool_call_ids or (tool_call_id and tool_call_id in tool_call_ids):
                    block.append(next_msg)
                    j += 1
                else:
                    break
            blocks.append(block)
            i = j
        else:
            blocks.append([msg])
            i += 1

    return blocks


def trim_messages_token_budget(
    messages: Sequence[BaseMessage],
    max_tokens: int = 3000,
    keep_system_messages: bool = False
) -> List[BaseMessage]:
    """
    Level 1 Memory: Short-Term Working Memory.
    Truncates the conversation history strictly adhering to a token budget limit.
    Guarantees that tool call sequences remain unbroken and prevents orphaned tool responses.
    """
    if not messages:
        return []

    # Isolate system instructions if they need to be preserved
    system_msgs: List[BaseMessage] = []
    dialogue_msgs: List[BaseMessage] = []

    for msg in messages:
        if isinstance(msg, SystemMessage):
            if keep_system_messages:
                system_msgs.append(msg)
        else:
            dialogue_msgs.append(msg)

    system_tokens = count_total_tokens(system_msgs)
    available_tokens = max(1, max_tokens - system_tokens)

    # Segment dialogue into unbreakable constraints
    blocks = group_atomic_message_blocks(dialogue_msgs)
    
    selected_blocks: List[List[BaseMessage]] = []
    accumulated_tokens = 0

    # Traverse LIFO (Last-In, First-Out) to prioritize recent context
    for block in reversed(blocks):
        block_tokens = count_total_tokens(block)

        # Always force-include the most recent block even if it breaches the limit slightly
        if accumulated_tokens + block_tokens <= available_tokens or not selected_blocks:
            selected_blocks.append(block)
            accumulated_tokens += block_tokens
        else:
            # TODO: Collect discarded historical message blocks to feed an incremental summarization
            # pipeline updating SessionSummarizer instead of silently dropping historical context.
            break

    selected_blocks.reverse()

    # Flatten the list of blocks using a list comprehension
    flattened: List[BaseMessage] = [msg for block in selected_blocks for msg in block]

    # Strict relational cleanup: Purge orphaned ToolMessages
    cleaned: List[BaseMessage] = []
    for msg in flattened:
        if isinstance(msg, ToolMessage):
            if not cleaned:
                continue  # Discard if it's the very first message with no parent
            
            prev_msg = cleaned[-1]
            is_valid_parent = isinstance(prev_msg, AIMessage) and getattr(prev_msg, "tool_calls", None)
            is_consecutive_tool = isinstance(prev_msg, ToolMessage)
            
            if is_valid_parent or is_consecutive_tool:
                cleaned.append(msg)
        else:
            cleaned.append(msg)

    if keep_system_messages and system_msgs:
        return system_msgs + cleaned
    
    return cleaned


class SessionSummarizer:
    """
    State holder for the current session's macro context.
    Stores an incremental summary of discarded historical messages to prevent context loss.
    """

    # TODO: Implement active dialogue summarization service.
    # Currently, SessionSummarizer provides the passive state container and XML context injection,
    # but relies on external manual calls to update_summary(). An automated summarization routine
    # should be integrated (either synchronously when trim_messages_token_budget evicts turns,
    # or asynchronously via AsyncMemoryManager during idle periods) using an LLM to distill
    # discarded dialogue into self.summary.

    def __init__(self) -> None:
        self.summary: Optional[str] = None

    def update_summary(self, new_summary: str) -> None:
        """Updates the internal summary state if the provided text is valid."""
        if new_summary and new_summary.strip():
            self.summary = new_summary.strip()

    def get_summary_context(self) -> str:
        """Formats the stored summary as an XML-tagged block for LLM prompt injection."""
        if not self.summary:
            return ""
        return f"<session_summary>\n{self.summary}\n</session_summary>"
