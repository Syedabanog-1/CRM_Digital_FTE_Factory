"""Conversation data model."""

import uuid
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator

from .channel import Channel


class Conversation(BaseModel):
    """A thread of messages between customer and agent."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: str
    initial_channel: Channel
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None
    status: str = "active"  # active, resolved, escalated
    sentiment_score: float | None = None
    resolution_type: str | None = None  # resolved, escalated, abandoned
    topics: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"active", "resolved", "escalated"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v

    @field_validator("resolution_type")
    @classmethod
    def validate_resolution_type(cls, v: str | None) -> str | None:
        if v is None:
            return v
        allowed = {"resolved", "escalated", "abandoned"}
        if v not in allowed:
            raise ValueError(f"resolution_type must be one of {allowed}")
        return v
