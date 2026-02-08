"""Ticket data model."""

import uuid
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator

from .channel import Channel


class Ticket(BaseModel):
    """A logged support interaction."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str | None = None
    customer_id: str
    source_channel: Channel
    category: str | None = None  # general, technical, billing, feedback, bug_report
    priority: str = "medium"  # low, medium, high
    status: str = "open"  # open, in_progress, escalated, resolved, closed
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = None
    resolution_notes: str | None = None
    escalation_reason: str | None = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        if v is None:
            return v
        allowed = {"general", "technical", "billing", "feedback", "bug_report"}
        if v not in allowed:
            raise ValueError(f"category must be one of {allowed}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        allowed = {"low", "medium", "high"}
        if v not in allowed:
            raise ValueError(f"priority must be one of {allowed}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"open", "in_progress", "escalated", "resolved", "closed"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v
