import os
import pytest
import asyncio
from agent.memory.profile_store import ProfileStore


@pytest.mark.asyncio
async def test_profile_store_crud(tmp_path):
    db_file = str(tmp_path / "test_profile.db")
    store = ProfileStore(db_path=db_file)
    await store.initialize()

    # Set and Get simple
    await store.set("usuario", "Josevi", category="general")
    val = await store.get("usuario")
    assert val == "Josevi"

    # Set and Get structured
    await store.set("preferencias_editor", {"theme": "dark", "tab_size": 4}, category="technical")
    val_dict = await store.get("preferencias_editor")
    assert isinstance(val_dict, dict)
    assert val_dict["theme"] == "dark"

    # Get by category
    tech_items = await store.get_by_category("technical")
    assert "preferencias_editor" in tech_items

    # Format for context
    formatted = await store.format_for_context()
    assert "<user_profile>" in formatted
    assert "Josevi" in formatted
    assert "</user_profile>" in formatted

    # Delete
    deleted = await store.delete("usuario")
    assert deleted is True
    assert await store.get("usuario") is None

    await store.close()
