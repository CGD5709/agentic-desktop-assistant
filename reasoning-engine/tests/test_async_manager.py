import pytest
from unittest.mock import AsyncMock, MagicMock
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
async def test_apply_memory_operations():
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
