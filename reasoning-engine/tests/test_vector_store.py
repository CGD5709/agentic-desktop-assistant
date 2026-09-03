import pytest
from agent.memory.vector_store import VectorMemoryStore
from agent.memory.models import MemoryItem, MemoryCategory


def test_vector_store_format_for_context():
    store = VectorMemoryStore()
    
    memories = [
        MemoryItem(
            text="El backend de ejecución está desarrollado en Spring Boot 3",
            category=MemoryCategory.SYSTEM_CONFIG,
            project="desktop-assistant"
        ),
        MemoryItem(
            text="El usuario prefiere respuestas en formato conciso",
            category=MemoryCategory.PREFERENCE
        )
    ]

    formatted = store.format_for_context(memories)
    assert "<auxiliary_context>" in formatted
    assert "[SYSTEM_CONFIG]" in formatted
    assert "(Proyecto: desktop-assistant)" in formatted
    assert "Spring Boot 3" in formatted
    assert "[PREFERENCE]" in formatted
    assert "</auxiliary_context>" in formatted


def test_vector_store_format_empty():
    store = VectorMemoryStore()
    assert store.format_for_context([]) == ""
