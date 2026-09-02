import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import AIMessage
from memory.async_manager import AsyncMemoryManager
from memory.models import MemoryCategory, MemoryItem


def test_trivial_filter_heuristics():
    vector_mock = AsyncMock()
    profile_mock = AsyncMock()
    manager = AsyncMemoryManager(vector_store=vector_mock, profile_store=profile_mock)

    # Bloques triviales
    assert manager._is_trivial_block([{"role": "user", "content": "hola"}]) is True
    assert manager._is_trivial_block([{"role": "user", "content": "gracias!"}]) is True
    assert manager._is_trivial_block([{"role": "user", "content": "ok, adiós"}]) is True
    assert manager._is_trivial_block([{"role": "user", "content": "jajaja"}]) is True

    # Bloques con contenido sustancial
    assert manager._is_trivial_block([
        {"role": "user", "content": "Mi repositorio de trabajo se encuentra en D:/Proyectos/Jarvis"}
    ]) is False
    assert manager._is_trivial_block([
        {"role": "user", "content": "Prefiero que uses typescript en vez de javascript para los scripts"}
    ]) is False


@pytest.mark.asyncio
async def test_apply_memory_operations_create():
    vector_mock = AsyncMock()
    profile_mock = AsyncMock()
    
    # Simular que no hay duplicados previos
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

    # Verificar que se llamó a add_memory en vector store
    assert vector_mock.add_memory.called
    added_item = vector_mock.add_memory.call_args[0][0]
    assert isinstance(added_item, MemoryItem)
    assert added_item.text == "El usuario prefiere respuestas breves y en español"
    assert added_item.category == MemoryCategory.PREFERENCE

    # Verificar que también se persistió en profile_store al ser de categoría PREFERENCE
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

    # Verificar que se llamó a update_memory con el ID correcto
    assert vector_mock.update_memory.called
    kwargs = vector_mock.update_memory.call_args.kwargs
    assert kwargs.get("memory_id") == "mem-uuid-1234"
    assert kwargs.get("new_text") == "El usuario prefiere escribir scripts en Python"
    assert kwargs.get("category") == MemoryCategory.PREFERENCE
    assert kwargs.get("importance") == 5

    # Verificar que se actualizó también en profile_store
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

    # Verificar que se llamó a delete_memory con el ID correcto
    assert vector_mock.delete_memory.called
    args = vector_mock.delete_memory.call_args.args
    assert args[0] == "mem-uuid-5678"


@pytest.mark.asyncio
async def test_process_pending_buffer_injects_existing_memories():
    vector_mock = AsyncMock()
    profile_mock = AsyncMock()
    
    # Simular una memoria existente en ChromaDB
    existing_mem = MemoryItem(
        id="mem-existing-999",
        text="El usuario usa Windows 11",
        category=MemoryCategory.FACT
    )
    vector_mock.search_memories.return_value = [existing_mem]
    vector_mock.update_memory.return_value = True

    manager = AsyncMemoryManager(vector_store=vector_mock, profile_store=profile_mock)
    
    # Mockear el LLM
    manager.llm = AsyncMock()
    manager.llm.ainvoke.return_value = AIMessage(content="""
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
    """)

    # Agregar turnos pendientes
    manager._pending_turns = [
        {"role": "user", "content": "Me he instalado Arch Linux y ya no uso Windows"},
        {"role": "assistant", "content": "Entendido, tomo nota de tu nuevo sistema operativo."}
    ]

    await manager._process_pending_buffer()

    # Verificar que se consultó ChromaDB para traer recuerdos existentes
    assert vector_mock.search_memories.called

    # Verificar que el LLM fue invocado con el ID de la memoria en el HumanMessage
    assert manager.llm.ainvoke.called
    messages_sent = manager.llm.ainvoke.call_args[0][0]
    human_msg = messages_sent[1]
    assert "mem-existing-999" in human_msg.content
    assert "El usuario usa Windows 11" in human_msg.content

    # Verificar que se aplicó el UPDATE con el ID extraído por el LLM
    assert vector_mock.update_memory.called
    assert vector_mock.update_memory.call_args.kwargs.get("memory_id") == "mem-existing-999"
    assert vector_mock.update_memory.call_args.kwargs.get("new_text") == "El usuario usa Arch Linux"
