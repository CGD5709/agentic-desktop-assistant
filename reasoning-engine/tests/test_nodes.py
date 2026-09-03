"""
Unit tests for the modular graph nodes, routing logic, models, and prompts.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

from agent.models import (
    AgentState,
    EventType,
    EventMetadata,
    ToolExecutionRequestPayload,
    ToolExecutionResponsePayload,
    EventEnvelope,
)
from agent.prompts import (
    JARVIS_SYSTEM_PROMPT,
    ROUTER_PROMPT,
    COMMAND_PROMPT,
    SUMMARIZE_PROMPT,
    EXTRACTION_PROMPT,
)
from agent.utils import extract_last_human_text, is_simple_greeting_or_trivial
from agent.nodes.router import RouterNode
from agent.nodes.chat import ChatNode
from agent.nodes.command import CommandNode
from agent.nodes.action import ActionNode
from agent.nodes.summarize import SummarizeNode
from agent.nodes.routing import route_intent, should_use_tools
from agent.memory.models import MemoryItem, MemoryCategory


def test_prompts_integrity():
    """Verifies that all required system prompts exist and are non-empty."""
    assert len(JARVIS_SYSTEM_PROMPT.strip()) > 0
    assert "Jarvis" in JARVIS_SYSTEM_PROMPT
    assert "REGLA CRÍTICA DE VERACIDAD" in JARVIS_SYSTEM_PROMPT

    assert len(ROUTER_PROMPT.strip()) > 0
    assert "CHAT" in ROUTER_PROMPT
    assert "COMMAND" in ROUTER_PROMPT

    assert len(COMMAND_PROMPT.strip()) > 0
    assert len(SUMMARIZE_PROMPT.strip()) > 0
    assert len(EXTRACTION_PROMPT.strip()) > 0


def test_models_schema():
    """Verifies event models, payloads, and state schemas."""
    metadata = EventMetadata(
        eventId="ev-1",
        correlationId="corr-1",
        timestamp=1000,
        source="unit-test",
        eventType=EventType.EXECUTION_REQUEST,
    )
    req_payload = ToolExecutionRequestPayload(toolName="test_tool", arguments={"x": 1})
    envelope = EventEnvelope(metadata=metadata, payload=req_payload.model_dump(by_alias=True))
    assert envelope.metadata.event_id == "ev-1"
    assert envelope.payload["toolName"] == "test_tool"

    res_payload = ToolExecutionResponsePayload(toolName="test_tool", status="SUCCESS", output="done")
    assert res_payload.status == "SUCCESS"

    state: AgentState = {
        "messages": [HumanMessage(content="test")],
        "intent": "CHAT",
        "correlation_id": "c-1",
        "retrieved_memories": [],
    }
    assert state["intent"] == "CHAT"


def test_utils_heuristics():
    """Tests message parsing and greeting heuristics."""
    msgs = [
        SystemMessage(content="sys"),
        HumanMessage(content="Hello assistant"),
        AIMessage(content="Hi there!"),
        HumanMessage(content="What is the weather?"),
    ]
    assert extract_last_human_text(msgs) == "What is the weather?"
    assert is_simple_greeting_or_trivial("hola") is True
    assert is_simple_greeting_or_trivial("ok") is True
    assert is_simple_greeting_or_trivial("dime qué procesos consumen más RAM") is False


def test_routing_functions():
    """Tests conditional routing logic."""
    chat_state: AgentState = {"intent": "CHAT", "messages": []}
    assert route_intent(chat_state) == "chat_node"

    cmd_state: AgentState = {"intent": "COMMAND", "messages": []}
    assert route_intent(cmd_state) == "command_node"

    no_tool_msg = AIMessage(content="Regular text")
    assert should_use_tools({"messages": [no_tool_msg]}) == "end"

    tool_msg = AIMessage(
        content="",
        tool_calls=[{"name": "kill_process", "args": {"pid": 123}, "id": "tc-1"}],
    )
    assert should_use_tools({"messages": [tool_msg]}) == "action_node"


@pytest.mark.asyncio
async def test_router_node():
    """Tests RouterNode intent classification and conditional retrieval."""
    llm_mock = AsyncMock()
    vector_mock = AsyncMock()

    # Case 1: Classified as COMMAND
    llm_mock.ainvoke.return_value = AIMessage(content="COMMAND")
    vector_mock.search_memories.return_value = [
        MemoryItem(text="Memory 1", category=MemoryCategory.PROJECT)
    ]

    router = RouterNode(llm=llm_mock, vector_store=vector_mock)
    state: AgentState = {
        "messages": [HumanMessage(content="kill process 1234 on port 8080")]
    }

    result = await router(state)
    assert result["intent"] == "COMMAND"
    assert len(result["retrieved_memories"]) == 1

    # Case 2: Trivial greeting skips vector search
    llm_mock.ainvoke.return_value = AIMessage(content="CHAT")
    state_trivial: AgentState = {"messages": [HumanMessage(content="hola")]}
    result_trivial = await router(state_trivial)
    assert result_trivial["intent"] == "CHAT"
    assert len(result_trivial["retrieved_memories"]) == 0


@pytest.mark.asyncio
async def test_chat_node():
    """Tests ChatNode dialogue generation and memory recording."""
    llm_mock = AsyncMock()
    llm_mock.ainvoke.return_value = AIMessage(content="Hello, sir. How may I assist?")
    profile_mock = AsyncMock()
    profile_mock.format_for_context.return_value = "<user_profile></user_profile>"
    summarizer_mock = MagicMock()
    summarizer_mock.get_summary_context.return_value = ""
    vector_mock = MagicMock()
    vector_mock.format_for_context.return_value = ""
    memory_manager_mock = MagicMock()

    chat = ChatNode(
        llm=llm_mock,
        profile_store=profile_mock,
        session_summarizer=summarizer_mock,
        vector_store=vector_mock,
        memory_manager=memory_manager_mock,
    )

    state: AgentState = {
        "messages": [HumanMessage(content="Hello Jarvis")]
    }
    result = await chat(state)

    assert len(result["messages"]) == 1
    assert result["messages"][0].content == "Hello, sir. How may I assist?"
    assert memory_manager_mock.record_turn.call_count == 2


@pytest.mark.asyncio
async def test_command_node_with_tools():
    """Tests CommandNode tool binding and execution request generation."""
    llm_mock = MagicMock()
    bound_llm_mock = AsyncMock()
    tool_call_resp = AIMessage(
        content="",
        tool_calls=[{"name": "system_stats", "args": {}, "id": "call-1"}]
    )
    bound_llm_mock.ainvoke.return_value = tool_call_resp
    llm_mock.bind_tools.return_value = bound_llm_mock

    profile_mock = AsyncMock()
    profile_mock.format_for_context.return_value = ""
    summarizer_mock = MagicMock()
    summarizer_mock.get_summary_context.return_value = ""
    vector_mock = MagicMock()
    vector_mock.format_for_context.return_value = ""
    memory_manager_mock = MagicMock()

    tools = [{"type": "function", "function": {"name": "system_stats"}}]

    command = CommandNode(
        llm=llm_mock,
        profile_store=profile_mock,
        session_summarizer=summarizer_mock,
        vector_store=vector_mock,
        memory_manager=memory_manager_mock,
        tools=tools,
    )

    state: AgentState = {"messages": [HumanMessage(content="Dime el uso de RAM")]}
    result = await command(state)

    assert len(result["messages"]) == 1
    assert result["messages"][0].tool_calls[0]["name"] == "system_stats"
    llm_mock.bind_tools.assert_called_once_with(tools)


@pytest.mark.asyncio
async def test_action_node():
    """Tests ActionNode dispatching RPC calls via RabbitMQClient."""
    mq_mock = AsyncMock()
    mq_mock.send_and_wait.return_value = {
        "payload": {"status": "SUCCESS", "output": "CPU: 15%, RAM: 45%"}
    }

    action = ActionNode(mq_client=mq_mock)

    state: AgentState = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[{"name": "get_system_metrics", "args": {}, "id": "tc-99"}],
            )
        ]
    }

    result = await action(state)
    assert len(result["messages"]) == 1
    tool_msg = result["messages"][0]
    assert isinstance(tool_msg, ToolMessage)
    assert tool_msg.tool_call_id == "tc-99"
    assert "CPU: 15%" in tool_msg.content
    assert mq_mock.send_and_wait.called


@pytest.mark.asyncio
async def test_summarize_node():
    """Tests SummarizeNode conversational translation of technical outputs."""
    llm_mock = AsyncMock()
    llm_mock.ainvoke.return_value = AIMessage(
        content="He consultado los datos del sistema. Actualmente la CPU está al 15% y la RAM al 45%."
    )
    profile_mock = AsyncMock()
    profile_mock.format_for_context.return_value = ""
    summarizer_mock = MagicMock()
    summarizer_mock.get_summary_context.return_value = ""
    vector_mock = MagicMock()
    vector_mock.format_for_context.return_value = ""
    memory_manager_mock = MagicMock()

    summarize = SummarizeNode(
        llm=llm_mock,
        profile_store=profile_mock,
        session_summarizer=summarizer_mock,
        vector_store=vector_mock,
        memory_manager=memory_manager_mock,
    )

    state: AgentState = {
        "messages": [
            HumanMessage(content="Dime las métricas del sistema"),
            ToolMessage(content="CPU: 15%, RAM: 45%", tool_call_id="tc-99"),
        ]
    }

    result = await summarize(state)
    assert len(result["messages"]) == 1
    assert "CPU está al 15%" in result["messages"][0].content
    assert memory_manager_mock.record_turn.call_count == 2
