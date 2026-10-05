from unittest.mock import AsyncMock

import pytest
from agent.memory.async_manager import AsyncMemoryManager
from agent.memory.models import MemoryCategory, MemoryItem
from langchain_core.messages import AIMessage


def test_trivial_filter_heuristics():
    vector_mock = AsyncMock()
    profile_mock = AsyncMock()
    manager = AsyncMemoryManager(vector_store=vector_mock, profile_store=profile_mock)

    # Bloques triviales
    assert manager._is_trivial_block([{"role": "user", "content": "hola"}]) is True
    assert manager._is_trivial_block([{"role": "user", "content": "gracias!"}]) is True
    assert manager._is_trivial_block([{"role": "user", "content": "ok, adiós"}]) is True
    assert manager._is_trivial_block([{"role": "user", "content": "jajaja"}]) is True

    # Blocks with substantial content
    assert (
        manager._is_trivial_block(
            [
                {
                    "role": "user",
                    "content": "Mi repositorio de trabajo se encuentra en D:/Proyectos/Jarvis",
                }
            ]
        )
        is False
    )
    assert (
        manager._is_trivial_block(
            [
                {
                    "role": "user",
                    "content": "Prefiero que uses typescript en vez de javascript para los scripts",
                }
            ]
        )
        is False
    )


@pytest.mark.asyncio
async def test_apply_memory_operations_create():
    vector_mock = AsyncMock()
    profile_mock = AsyncMock()

    # Simulate no prior duplicates
    vector_mock.search_memories.return_value = []
    vector_mock.add_memory.return_value = True

    manager = AsyncMemoryManager(vector_store=vector_mock, profile_store=profile_mock)

    json_response = """
    {
      "operations": [
        {
          "op": "CREATE",
          "memory_id": null,
          "text": "El usuario prefiere respuestas breves y en español",
          "category": "PREFERENCE",
          "importance": 4,
          "reason": "Preferencia explícita del usuario"
        }
      ]
    }
    """

    await manager._apply_memory_operations(json_response)

    # Verify add_memory was called on vector store
    assert vector_mock.add_memory.called
    added_item = vector_mock.add_memory.call_args[0][0]
    assert isinstance(added_item, MemoryItem)
    assert added_item.text == "El usuario prefiere respuestas breves y en español"
    assert added_item.category == MemoryCategory.PREFERENCE

    # Verify it was also persisted in profile_store as it is a PREFERENCE
    assert profile_mock.set.called


@pytest.mark.asyncio
async def test_apply_memory_operations_update():
    vector_mock = AsyncMock()
    profile_mock = AsyncMock()
    vector_mock.update_memory.return_value = True

    manager = AsyncMemoryManager(vector_store=vector_mock, profile_store=profile_mock)

    json_response = """
    {
      "operations": [
        {
          "op": "UPDATE",
          "memory_id": "mem-uuid-1234",
          "text": "El usuario prefiere escribir scripts en Python",
          "category": "PREFERENCE",
          "importance": 5,
          "reason": "Cambio de preferencia comunicado por el usuario"
        }
      ]
    }
    """

    await manager._apply_memory_operations(json_response)

    # Verify update_memory was called with the correct ID
    assert vector_mock.update_memory.called
    kwargs = vector_mock.update_memory.call_args.kwargs
    assert kwargs.get("memory_id") == "mem-uuid-1234"
    assert kwargs.get("new_text") == "El usuario prefiere escribir scripts en Python"
    assert kwargs.get("category") == MemoryCategory.PREFERENCE
    assert kwargs.get("importance") == 5

    # Verify it was also updated in profile_store
    assert profile_mock.set.called


@pytest.mark.asyncio
async def test_apply_memory_operations_delete():
    vector_mock = AsyncMock()
    profile_mock = AsyncMock()
    vector_mock.delete_memory.return_value = True

    manager = AsyncMemoryManager(vector_store=vector_mock, profile_store=profile_mock)

    json_response = """
    {
      "operations": [
        {
          "op": "DELETE",
          "memory_id": "mem-uuid-5678",
          "reason": "El usuario solicitó olvidar este hecho"
        }
      ]
    }
    """

    await manager._apply_memory_operations(json_response)

    # Verify delete_memory was called with the correct ID
    assert vector_mock.delete_memory.called
    args = vector_mock.delete_memory.call_args.args
    assert args[0] == "mem-uuid-5678"


@pytest.mark.asyncio
async def test_process_pending_buffer_injects_existing_memories():
    vector_mock = AsyncMock()
    profile_mock = AsyncMock()

    # Simulate an existing memory in ChromaDB
    existing_mem = MemoryItem(
        id="mem-existing-999",
        text="El usuario usa Windows 11",
        category=MemoryCategory.FACT,
    )
    vector_mock.search_memories.return_value = [existing_mem]
    vector_mock.update_memory.return_value = True

    manager = AsyncMemoryManager(vector_store=vector_mock, profile_store=profile_mock)

    # Mock the LLM
    manager.llm = AsyncMock()
    manager.llm.ainvoke.return_value = AIMessage(
        content="""
    {
      "operations": [
        {
          "op": "UPDATE",
          "memory_id": "mem-existing-999",
          "text": "El usuario usa Arch Linux",
          "category": "FACT",
          "importance": 4,
          "reason": "El usuario ha migrado de sistema operativo"
        }
      ]
    }
    """
    )

    # Agregar turnos pendientes
    manager._pending_turns = [
        {"role": "user", "content": "Me he instalado Arch Linux y ya no uso Windows"},
        {
            "role": "assistant",
            "content": "Entendido, tomo nota de tu nuevo sistema operativo.",
        },
    ]

    await manager._process_pending_buffer()

    # Verify ChromaDB was queried to fetch existing memories
    assert vector_mock.search_memories.called

    # Verify the LLM was invoked with the memory ID in the HumanMessage
    assert manager.llm.ainvoke.called
    messages_sent = manager.llm.ainvoke.call_args[0][0]
    human_msg = messages_sent[1]
    assert "mem-existing-999" in human_msg.content
    assert "El usuario usa Windows 11" in human_msg.content

    # Verify the UPDATE was applied with the ID extracted by the LLM
    assert vector_mock.update_memory.called
    assert (
        vector_mock.update_memory.call_args.kwargs.get("memory_id")
        == "mem-existing-999"
    )
    assert (
        vector_mock.update_memory.call_args.kwargs.get("new_text")
        == "El usuario usa Arch Linux"
    )


@pytest.mark.asyncio
async def test_apply_memory_operations_filters_low_importance():
    vector_mock = AsyncMock()
    profile_mock = AsyncMock()
    manager = AsyncMemoryManager(
        vector_store=vector_mock, profile_store=profile_mock, min_importance=3
    )

    json_response = """
    {
      "operations": [
        {
          "op": "CREATE",
          "memory_id": null,
          "text": "Dato poco importante",
          "category": "FACT",
          "importance": 1,
          "reason": "Detalle menor"
        },
        {
          "op": "CREATE",
          "memory_id": null,
          "text": "Dato de importancia media-baja",
          "category": "FACT",
          "importance": 2,
          "reason": "Detalle secundario"
        }
      ]
    }
    """

    await manager._apply_memory_operations(json_response)

    # Verify NO memory with importance < 3 was saved
    assert not vector_mock.add_memory.called
    assert not profile_mock.set.called


@pytest.mark.asyncio
async def test_apply_memory_operations_filters_transient_action_logs():
    vector_mock = AsyncMock()
    profile_mock = AsyncMock()
    manager = AsyncMemoryManager(vector_store=vector_mock, profile_store=profile_mock)

    json_response = """
    {
      "operations": [
        {
          "op": "CREATE",
          "memory_id": null,
          "text": "El usuario ha pedido cerrar el proceso de Google Chrome.",
          "category": "PROJECT",
          "importance": 3,
          "reason": "Comando ejecutado"
        },
        {
          "op": "CREATE",
          "memory_id": null,
          "text": "El asistente ha cerrado el proceso 5678",
          "category": "FACT",
          "importance": 4,
          "reason": "Resultado de comando"
        },
        {
          "op": "CREATE",
          "memory_id": null,
          "text": "Se ha cerrado el proceso de terminal",
          "category": "FACT",
          "importance": 3,
          "reason": "Acción efímera"
        }
      ]
    }
    """

    await manager._apply_memory_operations(json_response)

    # Verify operational action logs/transient commands were discarded
    assert not vector_mock.add_memory.called
