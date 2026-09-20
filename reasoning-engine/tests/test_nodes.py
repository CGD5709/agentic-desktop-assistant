"""
Unit tests for the modular graph nodes, routing logic, models, and prompts.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

from agent.models import (
    AgentState,
    ConfirmationRequestPayload,
    ConfirmationResponsePayload,
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
from agent.hitl import generate_confirmation_context
from services.confirmation_manager import ConfirmationManager


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

    conf_req = ConfirmationRequestPayload(
        confirmation_id="c-100",
        tool_name="matar_proceso",
        arguments={"nombre_proceso": "calc.exe"},
        title="Autorización",
        message="¿Cerrar calc.exe?",
    )
    assert conf_req.type == "confirmation_request"
    assert conf_req.confirmation_id == "c-100"
    assert conf_req.severity == "CRITICAL"

    conf_res = ConfirmationResponsePayload(
        confirmation_id="c-100",
        confirmed=True,
    )
    assert conf_res.type == "confirmation_response"
    assert conf_res.confirmed is True

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
async def test_action_node_critical_tool_approved():
    """Tests ActionNode requesting confirmation for a critical tool and executing upon approval."""
    import asyncio
    mq_mock = AsyncMock()
    mq_mock.send_and_wait.return_value = {
        "payload": {"status": "SUCCESS", "output": "Proceso 'notepad.exe' cerrado exitosamente."}
    }
    ws_mock = AsyncMock()
    confirmation_manager = ConfirmationManager()

    action = ActionNode(
        mq_client=mq_mock,
        confirmation_manager=confirmation_manager,
        ws_manager=ws_mock,
    )

    state: AgentState = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[{"name": "matar_proceso", "args": {"nombre_proceso": "notepad.exe"}, "id": "tc-kill-1"}],
            )
        ]
    }

    # Asynchronously simulate user approving the request in the frontend
    async def simulate_user_approval():
        await asyncio.sleep(0.01)
        # Find the registered confirmation
        for conf_id in list(confirmation_manager._pending_confirmations.keys()):
            confirmation_manager.resolve_confirmation(conf_id, True)

    asyncio.create_task(simulate_user_approval())

    result = await action(state)
    assert len(result["messages"]) == 1
    tool_msg = result["messages"][0]
    assert isinstance(tool_msg, ToolMessage)
    assert tool_msg.tool_call_id == "tc-kill-1"
    assert "cerrado exitosamente" in tool_msg.content
    assert ws_mock.broadcast.called
    assert mq_mock.send_and_wait.called


@pytest.mark.asyncio
async def test_action_node_critical_tool_rejected():
    """Tests ActionNode safely aborting execution and skipping RabbitMQ when user rejects confirmation."""
    import asyncio
    mq_mock = AsyncMock()
    ws_mock = AsyncMock()
    confirmation_manager = ConfirmationManager()

    action = ActionNode(
        mq_client=mq_mock,
        confirmation_manager=confirmation_manager,
        ws_manager=ws_mock,
    )

    state: AgentState = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[{"name": "matar_proceso", "args": {"nombre_proceso": "notepad.exe"}, "id": "tc-kill-2"}],
            )
        ]
    }

    # Asynchronously simulate user denying the request in the frontend
    async def simulate_user_denial():
        await asyncio.sleep(0.01)
        for conf_id in list(confirmation_manager._pending_confirmations.keys()):
            confirmation_manager.resolve_confirmation(conf_id, False)

    asyncio.create_task(simulate_user_denial())

    result = await action(state)
    assert len(result["messages"]) == 1
    tool_msg = result["messages"][0]
    assert isinstance(tool_msg, ToolMessage)
    assert tool_msg.tool_call_id == "tc-kill-2"
    assert "Operación cancelada por el usuario" in tool_msg.content
    assert ws_mock.broadcast.called
    # Critical guarantee: RabbitMQ / Java was NOT called!
    assert not mq_mock.send_and_wait.called


@pytest.mark.asyncio
async def test_action_node_dynamic_criticality_flag():
    """Tests ActionNode correctly detecting dynamic criticality flag from tool manifest."""
    action = ActionNode(
        mq_client=AsyncMock(),
        dynamic_tools=[
            {"function": {"name": "custom_safe_tool"}, "critical": False},
            {"function": {"name": "custom_dangerous_tool"}, "critical": True},
        ],
    )

    assert action.is_tool_critical("custom_safe_tool") is False
    assert action.is_tool_critical("custom_dangerous_tool") is True
    assert action.is_tool_critical("matar_proceso") is True  # Built-in fallback


def test_hitl_context_generation_with_template():
    """Tests dynamic placeholder interpolation in confirmation templates without hardcoded tool checks."""
    tool_def = {
        "function": {"name": "borrar_archivo"},
        "critical": True,
        "confirmation_template": "¿Desea eliminar permanentemente el archivo '{ruta_archivo}' de la ruta '{directorio}'?",
    }
    args = {"ruta_archivo": "data.csv", "directorio": "/var/log", "extra_param": 100}

    context = generate_confirmation_context("borrar_archivo", args, tool_def=tool_def)
    assert context["title"] == "Autorización: Borrar Archivo"
    assert "data.csv" in context["message"]
    assert "/var/log" in context["message"]
    assert context["severity"] == "CRITICAL"
    assert context["target"] == "data.csv"
    assert context["details"]["Ruta Archivo"] == "data.csv"
    assert context["details"]["Directorio"] == "/var/log"
    assert context["details"]["Extra Param"] == "100"


def test_hitl_context_generation_generic_fallback():
    """Tests generic confirmation message construction when no template is provided."""
    args = {"servicio": "nginx", "forzar": True}
    context = generate_confirmation_context("reiniciar_servicio", args, tool_def=None)

    assert context["title"] == "Autorización: Reiniciar Servicio"
    assert "Reiniciar Servicio" in context["message"]
    assert context["target"] == "nginx"
    assert context["details"]["Servicio"] == "nginx"
    assert context["details"]["Forzar"] == "True"


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


@pytest.mark.asyncio
async def test_action_node_validation_and_null_safety():
    """Verifies that ActionNode raises TypeError for non-AIMessage and handles None RPC response gracefully."""
    mq_mock = AsyncMock()
    action = ActionNode(mq_client=mq_mock)

    # Empty messages state returns empty list
    assert await action({"messages": []}) == {"messages": []}

    # Non-AIMessage raises TypeError
    with pytest.raises(TypeError, match="Expected last message in state to be an AIMessage"):
        await action({"messages": [HumanMessage(content="run command")]})

    # Null response from RPC returns error tool message without crashing
    mq_mock.send_and_wait.return_value = None
    state: AgentState = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[{"name": "test_tool", "args": {}, "id": "tc-null"}],
            )
        ]
    }
    result = await action(state)
    assert len(result["messages"]) == 1
    assert "Error: No response received" in result["messages"][0].content


def test_utils_multipart_dict_content():
    """Verifies extract_last_human_text supports multipart list containing dict blocks."""
    msgs = [
        HumanMessage(content=[{"type": "text", "text": "hello"}, {"type": "text", "text": "world"}])
    ]
    assert extract_last_human_text(msgs) == "hello world"


def test_agent_graph_factory():
    """Verifies create_agent_graph builds a valid LangGraph StateGraph instance."""
    from agent.agent import create_agent_graph
    from agent.nodes import NodeName

    router = MagicMock()
    chat = MagicMock()
    command = MagicMock()
    action = MagicMock()
    summarize = MagicMock()

    graph = create_agent_graph(
        router_node=router,
        chat_node=chat,
        command_node=command,
        action_node=action,
        summarize_node=summarize,
    )

    nodes = graph.nodes
    assert NodeName.ROUTER.value in nodes
    assert NodeName.CHAT.value in nodes
    assert NodeName.COMMAND.value in nodes
    assert NodeName.ACTION.value in nodes
    assert NodeName.SUMMARIZE.value in nodes


@pytest.mark.asyncio
async def test_agent_runtime_factory_and_lifecycle(tmp_path):
    """Verifies create_agent_runtime builds an isolated container and handles lifecycle without errors."""
    from agent.agent import create_agent_runtime, AgentRuntime

    mq_mock = AsyncMock()
    llm_mock = AsyncMock()
    db_path = str(tmp_path / "test_profile.db")
    chroma_path = str(tmp_path / "test_chroma")

    runtime = create_agent_runtime(
        profile_db_path=db_path,
        chroma_dir=chroma_path,
        mq_client=mq_mock,
        llm=llm_mock,
    )

    assert isinstance(runtime, AgentRuntime)
    assert runtime.graph is not None
    assert runtime.dynamic_tools == []

    # Mock vector store and memory manager to isolate lifecycle test
    runtime.vector_store.initialize = AsyncMock()
    runtime.memory_manager.flush_and_close = AsyncMock()

    await runtime.initialize()
    assert mq_mock.connect.called
    assert runtime.vector_store.initialize.called

    await runtime.close()
    assert mq_mock.close.called
    assert runtime.memory_manager.flush_and_close.called


