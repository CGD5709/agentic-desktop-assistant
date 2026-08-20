import os
import json
import aiosqlite
from typing import Any, Dict, Optional
from datetime import datetime, timezone


class ProfileStore:
    """
    Nivel 0: Perfil Estructurado
    Almacena información estable, preferencias explícitas y configuración del usuario
    de forma persistente en una base de datos SQLite asíncrona.
    """

    def __init__(self, db_path: str = "./data/assistant_profile.db"):
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def initialize(self):
        """Crea el directorio si no existe e inicializa la tabla de perfiles."""
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
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

    async def _ensure_connected(self):
        if self._db is None:
            await self.initialize()

    async def get(self, key: str, default: Any = None) -> Any:
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
        await self._ensure_connected()
        assert self._db is not None
        cursor = await self._db.execute("DELETE FROM user_profile WHERE key = ?", (key,))
        await self._db.commit()
        return cursor.rowcount > 0

    async def get_all(self) -> Dict[str, Any]:
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
        """Formatea el perfil estructurado como bloque de contexto para el LLM."""
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

    async def close(self):
        if self._db is not None:
            await self._db.close()
            self._db = None
