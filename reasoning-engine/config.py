"""
Configuration settings for the Reasoning Engine using Pydantic Settings.

Reads configuration parameters from environment variables or a local .env file,
providing sensible defaults for local development environments.
"""
import json
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application runtime configuration schema.

    Attributes:
        HOST: Host network interface address for the HTTP/WebSocket server.
        PORT: Port number on which the server listens.
        ALLOWED_ORIGINS: Permitted CORS origins for browser/desktop clients.
    """

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """
        Parse and sanitize allowed CORS origins.

        Supports comma-separated strings (e.g. from standard .env files),
        JSON-encoded array strings, or raw Python list sequences.

        Args:
            v: Raw origin input from environment or direct initialization.

        Returns:
            A cleaned list of origin URLs.
        """
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                try:
                    return json.loads(v_stripped)
                except json.JSONDecodeError:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, (list, tuple)):
            return [str(origin).strip() for origin in v if str(origin).strip()]
        return v


settings = Settings()
