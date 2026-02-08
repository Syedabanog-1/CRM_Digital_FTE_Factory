"""Message data model."""

import uuid
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator

from .channel import Channel


class Message(BaseModel):
    """A single communication unit within a conversation."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    channel: Channel
    direction: str  # inbound, outbound
    role: str  # customer, agent, system
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tokens_used: int | None = None
    latency_ms: int | None = None

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v: str) -> str:
        allowed = {"inbound", "outbound"}
        if v not in allowed:
            raise ValueError(f"direction must be one of {allowed}")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"customer", "agent", "system"}
        if v not in allowed:
            raise ValueError(f"role must be one of {allowed}")
        return v

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Message content must not be empty")
        return v
