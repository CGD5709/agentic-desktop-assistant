import os
import json
import aiosqlite
from typing import Any, Dict, Optional
from datetime import datetime, timezone


class ProfileStore:
    """
    Level 0 Memory: Structured Profile Store.
    An asynchronous key-value persistence layer built on SQLite.
    Designed to store stable user preferences, configuration data, and deterministic facts
    without requiring vector-based semantic search.
    """

    def __init__(self, db_path: str = "./data/assistant_profile.db"):
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        """
        Bootstraps the database infrastructure. 
        Ensures the target directory exists and executes the DDL schema. 
        This operation is idempotent.
        """
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        # Override default tuple factory to access columns by name (e.g., row["value"])
        self._db.row_factory = aiosqlite.Row

        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS user_profile (
                key TEXT PRIMARY KEY,
                category TEXT NOT NULL DEFAULT 'general',
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        await self._db.commit()

    async def _ensure_connected(self) -> None:
        """
        Implements lazy initialization for the database connection.
        Ensures the I/O bottleneck only occurs exactly when the first query is dispatched.
        """
        if self._db is None:
            await self.initialize()

    async def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a value by its exact key.
        Applies defensive JSON deserialization: falls back to raw string if parsing fails.
        """
        await self._ensure_connected()
        assert self._db is not None
        async with self._db.execute("SELECT value FROM user_profile WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            if row:
                try:
                    return json.loads(row["value"])
                except Exception:
                    return row["value"]
        return default

    async def set(self, key: str, value: Any, category: str = "general") -> None:
        """
        Performs an atomic UPSERT (Insert or Update) for a given key-value pair.
        Complex objects (dicts, lists) are automatically serialized to JSON strings.
        """
        await self._ensure_connected()
        assert self._db is not None
        serialized_val = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
        now = datetime.now(timezone.utc).isoformat()

        await self._db.execute("""
            INSERT INTO user_profile (key, category, value, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                category = excluded.category,
                value = excluded.value,
                updated_at = excluded.updated_at
        """, (key, category, serialized_val, now))
        await self._db.commit()

    async def delete(self, key: str) -> bool:
        """
        Removes a specific record from the store.
        
        Returns:
            bool: True if a row was successfully deleted, False if the key did not exist.
        """
        await self._ensure_connected()
        assert self._db is not None
        cursor = await self._db.execute("DELETE FROM user_profile WHERE key = ?", (key,))
        await self._db.commit()
        return cursor.rowcount > 0

    async def get_all(self) -> Dict[str, Any]:
        """
        Fetches the entire profile dataset, deserializing values where applicable.
        """
        await self._ensure_connected()
        assert self._db is not None
        result = {}
        async with self._db.execute("SELECT key, value FROM user_profile") as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                k = row["key"]
                v_raw = row["value"]
                try:
                    result[k] = json.loads(v_raw)
                except Exception:
                    result[k] = v_raw
        return result

    async def get_by_category(self, category: str) -> Dict[str, Any]:
        """
        Fetches all profile records grouped under a specific category tag.
        """
        await self._ensure_connected()
        assert self._db is not None
        result = {}
        async with self._db.execute("SELECT key, value FROM user_profile WHERE category = ?", (category,)) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                k = row["key"]
                v_raw = row["value"]
                try:
                    result[k] = json.loads(v_raw)
                except Exception:
                    result[k] = v_raw
        return result

    async def format_for_context(self) -> str:
        """
        Serializes the relational data into an XML-tagged text block.
        Designed for direct injection into the LLM's system prompt context window.
        """
        data = await self.get_all()
        if not data:
            return ""

        lines = ["<user_profile>"]
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                lines.append(f"- {k}: {json.dumps(v, ensure_ascii=False)}")
            else:
                lines.append(f"- {k}: {v}")
        lines.append("</user_profile>")
        return "\n".join(lines)

    async def close(self) -> None:
        """Gracefully closes the SQLite connection and releases file locks."""
        if self._db is not None:
            await self._db.close()
            self._db = None
