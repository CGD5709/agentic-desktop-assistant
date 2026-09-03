from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field


class MemoryCategory(str, Enum):
    PREFERENCE = "PREFERENCE"
    PROJECT = "PROJECT"
    SYSTEM_CONFIG = "SYSTEM_CONFIG"
    DECISION = "DECISION"
    FACT = "FACT"


class MemoryItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    category: MemoryCategory = MemoryCategory.FACT
    importance: int = Field(default=3, ge=1, le=5) #Upper limit may be changed to 10
    project: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_accessed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_id: Optional[str] = None
    similarity_score: Optional[float] = None


class MemoryOperationType(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    NOTHING = "NOTHING"


class MemoryOperation(BaseModel):
    op: MemoryOperationType
    memory_id: Optional[str] = None
    text: Optional[str] = None
    category: Optional[MemoryCategory] = None
    importance: Optional[int] = Field(default=3, ge=1, le=5)
    project: Optional[str] = None
    reason: Optional[str] = None


class MemoryExtractionPlan(BaseModel):
    operations: List[MemoryOperation] = Field(default_factory=list)


class UserProfile(BaseModel):
    user_name: Optional[str] = "Usuario"
    response_style: Optional[str] = "Conciso, elegante y técnico cuando proceda"
    preferences: Dict[str, Any] = Field(default_factory=dict)
    system_environment: Dict[str, Any] = Field(default_factory=dict)
    technical_preferences: Dict[str, Any] = Field(default_factory=dict)
