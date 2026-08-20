import json
from typing import List, Optional, Sequence, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage

try:
    import tiktoken
    _enc = tiktoken.get_encoding("cl100k_base")

    def count_tokens(text: str) -> int:
        if not text:
            return 0
        return len(_enc.encode(str(text)))
except Exception:
    def count_tokens(text: str) -> int:
        if not text:
            return 0
        return max(1, len(str(text)) // 4)


def count_message_tokens(msg: BaseMessage) -> int:
    """Calcula el número aproximado de tokens de un mensaje de LangChain."""
    tokens = 4  # overhead por mensaje (rol, metadatos)
    
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

    if isinstance(msg, AIMessage) and msg.tool_calls:
        tokens += count_tokens(json.dumps(msg.tool_calls, ensure_ascii=False))
    elif isinstance(msg, ToolMessage) and msg.tool_call_id:
        tokens += count_tokens(str(msg.tool_call_id))

    return tokens


def count_total_tokens(messages: Sequence[BaseMessage]) -> int:
    return sum(count_message_tokens(m) for m in messages)


def group_atomic_message_blocks(messages: Sequence[BaseMessage]) -> List[List[BaseMessage]]:
    """
    Agrupa los mensajes en bloques atómicos indivisibles.
    Por ejemplo, un AIMessage con tool_calls y sus correspondientes ToolMessage(s)
    forman un único bloque atómico para no romper la gramática del LLM al podar.
    """
    blocks: List[List[BaseMessage]] = []
    i = 0
    n = len(messages)

    while i < n:
        msg = messages[i]
        
        # Si es un AIMessage con tool calls, agrupamos el AIMessage y todos sus ToolMessages consecuentes
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

                # Comprobamos coincidencia con tool_call_ids o agregamos si es consecutiva
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
    Nivel 1: Memoria a Corto Plazo.
    Recorta el historial de mensajes de la conversación respetando un presupuesto máximo de tokens.
    Garantiza que nunca se rompan llamadas a herramientas ni queden ToolMessages huérfanos.
    """
    if not messages:
        return []

    # Extraemos mensajes de sistema si se solicita conservarlos explícitamente
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

    # Agrupamos en bloques atómicos
    blocks = group_atomic_message_blocks(dialogue_msgs)
    
    # Recorremos desde el bloque más reciente hacia el más antiguo acumulando tokens
    selected_blocks: List[List[BaseMessage]] = []
    accumulated_tokens = 0

    for block in reversed(blocks):
        block_tokens = sum(count_message_tokens(m) for m in block)
        if accumulated_tokens + block_tokens <= available_tokens or not selected_blocks:
            # Siempre incluimos al menos el bloque más reciente
            selected_blocks.append(block)
            accumulated_tokens += block_tokens
        else:
            # Se excedió el presupuesto
            break

    # Invertimos para recuperar el orden cronológico original
    selected_blocks.reverse()

    flattened: List[BaseMessage] = []
    for block in selected_blocks:
        flattened.extend(block)

    # Limpieza estricta: eliminamos cualquier ToolMessage huérfano que no siga a un AIMessage con tool_calls
    cleaned: List[BaseMessage] = []
    for msg in flattened:
        if isinstance(msg, ToolMessage):
            if cleaned:
                prev_msg = cleaned[-1]
                if (isinstance(prev_msg, AIMessage) and prev_msg.tool_calls) or isinstance(prev_msg, ToolMessage):
                    cleaned.append(msg)
                else:
                    # Omitir ToolMessage huérfano
                    continue
            else:
                # Omitir ToolMessage huérfano
                continue
        else:
            cleaned.append(msg)

    # Aseguramos que la conversación no empiece con un ToolMessage
    while cleaned and isinstance(cleaned[0], ToolMessage):
        cleaned.pop(0)

    if keep_system_messages and system_msgs:
        return system_msgs + cleaned
    return cleaned


class SessionSummarizer:
    """
    Mantiene un resumen incremental de la sesión actual cuando se descartan
    mensajes antiguos para no perder contexto macro.
    """

    def __init__(self):
        self.summary: Optional[str] = None

    def update_summary(self, new_summary: str):
        if new_summary and new_summary.strip():
            self.summary = new_summary.strip()

    def get_summary_context(self) -> str:
        if not self.summary:
            return ""
        return f"<session_summary>\n{self.summary}\n</session_summary>"
