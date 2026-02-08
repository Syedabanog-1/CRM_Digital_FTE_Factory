"""KnowledgeBaseEntry data model."""

import uuid
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class KnowledgeBaseEntry(BaseModel):
    """A product documentation article."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    content: str
    category: str | None = None
    keywords: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
