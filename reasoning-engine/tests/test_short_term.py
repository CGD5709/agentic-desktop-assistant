import pytest
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from memory.short_term import (
    trim_messages_token_budget,
    count_message_tokens,
    count_total_tokens,
    group_atomic_message_blocks,
    SessionSummarizer
)


def test_count_message_tokens():
    msg = HumanMessage(content="Hola mundo")
    tokens = count_message_tokens(msg)
    assert tokens > 0


def test_atomic_blocks_grouping_with_tool_calls():
    ai_tool = AIMessage(
        content="",
        tool_calls=[{"name": "kill_process", "args": {"pid": 1234}, "id": "call_abc"}]
    )
    tool_resp = ToolMessage(content="Proceso 1234 terminado", tool_call_id="call_abc")
    human_msg = HumanMessage(content="Gracias")

    messages = [ai_tool, tool_resp, human_msg]
    blocks = group_atomic_message_blocks(messages)

    assert len(blocks) == 2
    assert len(blocks[0]) == 2  # [AIMessage, ToolMessage] juntos
    assert blocks[0][0] == ai_tool
    assert blocks[0][1] == tool_resp
    assert blocks[1] == [human_msg]


def test_trim_messages_within_budget():
    msg1 = HumanMessage(content="Mensaje 1")
    msg2 = AIMessage(content="Respuesta 1")
    msg3 = HumanMessage(content="Mensaje 2")

    trimmed = trim_messages_token_budget([msg1, msg2, msg3], max_tokens=1000)
    assert len(trimmed) == 3


def test_trim_messages_preserves_atomic_tool_calls_when_cutting():
    # Creamos un mensaje antiguo muy largo
    old_msg = HumanMessage(content="Texto antiguo muy largo " * 50)
    
    # Bloque de herramienta
    ai_tool = AIMessage(
        content="",
        tool_calls=[{"name": "list_files", "args": {"path": "."}, "id": "call_xyz"}]
    )
    tool_resp = ToolMessage(content="file1.txt, file2.txt", tool_call_id="call_xyz")
    recent_msg = HumanMessage(content="¿Qué archivos hay?")

    messages = [old_msg, ai_tool, tool_resp, recent_msg]
    
    # Ajustamos presupuesto para que quepan el bloque de tool y el mensaje reciente pero no el old_msg
    budget = count_total_tokens([ai_tool, tool_resp, recent_msg]) + 10
    trimmed = trim_messages_token_budget(messages, max_tokens=budget)

    # Debe descartar old_msg pero mantener intacto el bloque tool call + recent_msg
    assert old_msg not in trimmed
    assert ai_tool in trimmed
    assert tool_resp in trimmed
    assert recent_msg in trimmed


def test_session_summarizer():
    summarizer = SessionSummarizer()
    assert summarizer.get_summary_context() == ""

    summarizer.update_summary("El usuario está depurando un error en Java.")
    ctx = summarizer.get_summary_context()
    assert "<session_summary>" in ctx
    assert "El usuario está depurando un error en Java." in ctx
