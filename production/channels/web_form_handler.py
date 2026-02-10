"""Web form channel handler - FastAPI router for support form submissions.

Handles POST /support/submit and GET /support/ticket/{ticket_id}.
"""

import json
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from production.database import queries
from production.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/support", tags=["support"])


# ---- Request/Response Models ----


class SupportFormInput(BaseModel):
    """Web support form submission input with validation."""

    name: str = Field(..., min_length=2, description="Customer name")
    email: str = Field(..., description="Customer email")
    subject: str = Field(..., min_length=5, description="Issue subject")
    category: str = Field(
        default="General Inquiry",
        description="Support category",
    )
    priority: str = Field(default="medium", description="Priority level")
    message: str = Field(..., min_length=10, description="Detailed message")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        import re

        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Invalid email format")
        return v.lower()

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        valid = [
            "Technical Support",
            "Billing",
            "Feature Request",
            "Bug Report",
            "General Inquiry",
        ]
        if v not in valid:
            raise ValueError(f"Category must be one of: {', '.join(valid)}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        valid = ["low", "medium", "high", "urgent"]
        if v not in valid:
            raise ValueError(f"Priority must be one of: {', '.join(valid)}")
        return v


class SubmitResponse(BaseModel):
    """Response after successful form submission."""

    ticket_id: str
    status: str
    message: str
    estimated_response_time: str


class TicketStatusResponse(BaseModel):
    """Ticket status response."""

    ticket_id: str
    status: str
    subject: str
    category: str | None
    priority: str
    created_at: str
    updated_at: str
    messages: list[dict]


# ---- Endpoints ----


@router.post("/submit", response_model=SubmitResponse, status_code=201)
async def submit_support_form(form: SupportFormInput):
    """Submit a web support form. Creates customer, ticket, and publishes to Kafka."""
    try:
        # Resolve or create customer
        customer = await queries.get_customer_by_email(form.email)
        if not customer:
            customer = await queries.insert_customer(
                email=form.email, name=form.name
            )
        # Update name if changed
        elif not customer.get("name") and form.name:
            pool = await queries.get_pool()
            await pool.execute(
                "UPDATE customers SET name = $1, updated_at = NOW() WHERE id = $2",
                form.name,
                customer["id"],
            )

        # Get or create conversation
        conversation = await queries.get_active_conversation(
            customer["id"], "web"
        )
        if not conversation:
            conversation = await queries.insert_conversation(
                customer_id=customer["id"],
                channel="web",
                subject=form.subject,
            )

        # Create ticket
        ticket = await queries.insert_ticket(
            customer_id=customer["id"],
            channel="web",
            subject=form.subject,
            category=form.category,
            priority=form.priority,
            conversation_id=conversation["id"],
        )

        # Store inbound message
        await queries.insert_message(
            conversation_id=conversation["id"],
            channel="web",
            direction="inbound",
            role="customer",
            content=form.message,
        )

        # Publish to Kafka (non-blocking)
        try:
            from production.kafka_client import get_producer

            producer = await get_producer()
            if producer:
                msg = json.dumps({
                    "ticket_id": str(ticket["id"]),
                    "channel": "web",
                    "customer_email": form.email,
                    "customer_name": form.name,
                    "subject": form.subject,
                    "content": form.message,
                    "category": form.category,
                    "priority": form.priority,
                }).encode("utf-8")
                await producer.send_and_wait("fte.channels.webform.inbound", msg)
                await producer.send_and_wait("fte.tickets.incoming", msg)
        except Exception as e:
            logger.warning("kafka_publish_failed", error=str(e))

        logger.info(
            "form_submitted",
            ticket_id=str(ticket["id"]),
            customer_email=form.email,
        )

        return SubmitResponse(
            ticket_id=str(ticket["id"]),
            status="open",
            message="Your support request has been received. Our AI assistant will respond within minutes.",
            estimated_response_time="< 5 minutes",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("form_submission_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/ticket/{ticket_id}", response_model=TicketStatusResponse)
async def get_ticket_status(ticket_id: str):
    """Check ticket status and view agent response."""
    try:
        tid = UUID(ticket_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ticket ID format")

    ticket = await queries.get_ticket(tid)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Get messages if conversation exists
    messages = []
    if ticket.get("conversation_id"):
        raw_messages = await queries.get_conversation_messages(
            ticket["conversation_id"]
        )
        messages = [
            {
                "role": m["role"],
                "content": m["content"],
                "timestamp": m["created_at"].isoformat(),
            }
            for m in raw_messages
        ]

    return TicketStatusResponse(
        ticket_id=str(ticket["id"]),
        status=ticket["status"],
        subject=ticket["subject"],
        category=ticket.get("category"),
        priority=ticket["priority"],
        created_at=ticket["created_at"].isoformat(),
        updated_at=ticket["updated_at"].isoformat(),
        messages=messages,
    )
