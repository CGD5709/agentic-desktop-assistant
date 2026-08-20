import pytest
import asyncio
from memory.vector_store import VectorMemoryStore
from memory.models import MemoryItem, MemoryCategory


@pytest.mark.asyncio
async def test_real_chromadb_with_nomic_embed_text(tmp_path):
    chroma_dir = str(tmp_path / "test_chroma")
    store = VectorMemoryStore(
        persist_directory=chroma_dir,
        collection_name="test_integration_memories",
        embedding_model="nomic-embed-text"
    )
    await store.initialize()

    item1 = MemoryItem(
        text="El proyecto se compila con Java 21 y Maven",
        category=MemoryCategory.PROJECT,
        project="execution-service",
        importance=5
    )
    item2 = MemoryItem(
        text="Al usuario le gusta la pizza con piña",
        category=MemoryCategory.FACT,
        importance=1
    )

    success1 = await store.add_memory(item1)
    success2 = await store.add_memory(item2)

    assert success1 is True
    assert success2 is True

    # Búsqueda semántica sobre tecnología/Java
    results_tech = await store.search_memories(
        query="¿Qué versión de JDK o herramientas de build usamos?",
        limit=2,
        score_threshold=0.50
    )

    assert len(results_tech) >= 1
    assert "Java 21" in results_tech[0].text
    assert results_tech[0].project == "execution-service"

    # Actualización de memoria
    updated = await store.update_memory(
        memory_id=item1.id,
        new_text="El proyecto se compila con Java 22 y Gradle",
        category=MemoryCategory.PROJECT,
        importance=4
    )
    assert updated is True

    # Eliminación de memoria
    deleted = await store.delete_memory(item2.id)
    assert deleted is True
