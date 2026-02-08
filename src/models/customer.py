"""Customer and CustomerIdentifier data models."""

import uuid
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator
import re


class Customer(BaseModel):
    """A person contacting support, unified across channels."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    phone: str | None = None
    name: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = Field(default_factory=dict)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, v):
            raise ValueError(f"Invalid email format: {v}")
        return v.lower()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v.startswith("+"):
            raise ValueError("Phone must include country code (start with +)")
        return v


class CustomerIdentifier(BaseModel):
    """Maps alternative identifiers to a primary customer."""

    identifier_type: str  # email, phone, whatsapp
    identifier_value: str
    customer_id: str
    verified: bool = False

    @field_validator("identifier_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed = {"email", "phone", "whatsapp"}
        if v not in allowed:
            raise ValueError(f"identifier_type must be one of {allowed}")
        return v
