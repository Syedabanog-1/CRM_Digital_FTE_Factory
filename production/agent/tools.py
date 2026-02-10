"""OpenAI Agents SDK @function_tool definitions for the Customer Success Agent.

Transforms Stage 1 MCP tools into production-grade tools with:
- Pydantic BaseModel input schemas
- Detailed docstrings for LLM consumption
- Try/catch error handling
- PostgreSQL persistence via queries.py
- Kafka event publishing
"""

import json
import time
from uuid import UUID

from agents import function_tool
from openai import OpenAI
from pydantic import BaseModel, Field

from production.config import settings
from production.database import queries
from production.agent.formatters import formatter
from production.logging_config import get_logger

logger = get_logger(__name__)

# Lazy-initialized OpenAI client for embeddings
_openai_client: OpenAI | None = None


def _get_openai_client() -> OpenAI:
    """Get or create the OpenAI client."""
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=settings.openai_api_key)
    return _openai_client


# ---- Sentiment Analysis (keyword-based, matching Stage 1) ----

POSITIVE_WORDS = {
    "thank", "thanks", "great", "wonderful", "excellent", "love", "amazing",
    "helpful", "perfect", "awesome", "good", "fantastic", "appreciate",
    "pleased", "happy", "satisfied", "brilliant",
}
NEGATIVE_WORDS = {
    "bad", "terrible", "frustrating", "broken", "fail", "failed", "worst",
    "awful", "horrible", "disappointed", "useless", "annoying", "slow",
    "crash", "bug", "error", "problem", "issue",
}
PROFANITY_WORDS = {
    "damn", "hell", "garbage", "stupid", "idiot", "scam", "crap", "sucks",
    "ridiculous", "pathetic",
}
LEGAL_WORDS = {"lawyer", "attorney", "lawsuit", "sue", "litigation", "legal"}

import re

def _compute_sentiment(text: str) -> tuple[float, str]:
    """Compute sentiment score and label from text."""
    if not text or not text.strip():
        return 0.5, "neutral"

    words = set(re.findall(r"[a-zA-Z]{3,}", text.lower()))
    score = 0.5  # neutral base

    score += len(words & POSITIVE_WORDS) * 0.1
    score -= len(words & NEGATIVE_WORDS) * 0.1
    score -= len(words & PROFANITY_WORDS) * 0.3
    score -= len(words & LEGAL_WORDS) * 0.5

    score = max(0.0, min(1.0, score))

    if score >= 0.8:
        label = "very_positive"
    elif score >= 0.6:
        label = "positive"
    elif score >= 0.4:
        label = "neutral"
    elif score >= 0.2:
        label = "negative"
    else:
        label = "very_negative"

    return round(score, 2), label


# ---- Kafka publisher (lazy import to avoid circular deps) ----

async def _publish_to_kafka(topic: str, message: dict) -> None:
    """Publish a message to Kafka topic. Gracefully handles unavailability."""
    try:
        from production.kafka_client import get_producer
        producer = await get_producer()
        if producer:
            await producer.send_and_wait(
                topic, json.dumps(message).encode("utf-8")
            )
    except Exception as e:
        logger.warning("kafka_publish_failed", topic=topic, error=str(e))


# ---- Tool Input Schemas ----


class SearchKBInput(BaseModel):
    """Input for searching the knowledge base."""
    query: str = Field(..., description="The search query from the customer")
    max_results: int = Field(default=3, ge=1, le=10, description="Maximum results to return")


class CreateTicketInput(BaseModel):
    """Input for creating a support ticket."""
    subject: str = Field(..., description="Brief description of the issue")
    category: str = Field(
        default="General Inquiry",
        description="One of: Technical Support, Billing, Feature Request, Bug Report, General Inquiry",
    )
    priority: str = Field(default="medium", description="One of: low, medium, high, urgent")
    customer_email: str = Field(..., description="Customer's email address")
    channel: str = Field(..., description="Source channel: email, whatsapp, web")


class GetHistoryInput(BaseModel):
    """Input for getting customer history."""
    customer_email: str = Field(..., description="Customer's email address")
    max_conversations: int = Field(default=5, ge=1, le=20, description="Maximum conversations to return")


class EscalateInput(BaseModel):
    """Input for escalating to human support."""
    reason: str = Field(..., description="Why escalation is needed")
    ticket_id: str = Field(..., description="The ticket ID to escalate")
    urgency: str = Field(default="normal", description="One of: normal, high, critical")


class SendResponseInput(BaseModel):
    """Input for sending a response to the customer."""
    message: str = Field(..., description="The response message content")
    channel: str = Field(..., description="Target channel: email, whatsapp, web")
    ticket_id: str = Field(..., description="Associated ticket ID")


class SentimentInput(BaseModel):
    """Input for analyzing sentiment."""
    text: str = Field(..., description="The text to analyze for sentiment")


# ---- Tool Implementations ----


@function_tool
async def search_knowledge_base(input: SearchKBInput) -> str:
    """Search the product knowledge base for relevant articles using semantic similarity.
    Use this tool to find answers to customer questions about CloudSync Pro features,
    troubleshooting, and documentation. Returns ranked results with similarity scores.
    If no results are found after 2 searches, escalate to human support."""
    try:
        # Generate query embedding
        client = _get_openai_client()
        embedding_response = client.embeddings.create(
            model=settings.openai_embedding_model,
            input=input.query[:8000],
        )
        query_embedding = embedding_response.data[0].embedding

        results = await queries.search_knowledge_base(
            query_embedding=query_embedding,
            max_results=input.max_results,
        )

        if not results:
            return json.dumps({"results": [], "total_found": 0})

        formatted_results = []
        for r in results:
            formatted_results.append({
                "title": r["title"],
                "content": r["content"][:500],  # Truncate for LLM context
                "category": r.get("category", "general"),
                "similarity_score": round(r.get("similarity_score", 0), 2),
            })

        return json.dumps({
            "results": formatted_results,
            "total_found": len(formatted_results),
        })
    except Exception as e:
        logger.error("search_kb_failed", error=str(e))
        return json.dumps({"error": str(e), "results": [], "total_found": 0})


@function_tool
async def create_ticket(input: CreateTicketInput) -> str:
    """Create a support ticket for the current customer interaction.
    This MUST be called FIRST before any other tool in every interaction.
    Creates a ticket in the database linked to the customer and returns the ticket ID."""
    try:
        # Resolve or create customer
        customer = await queries.get_customer_by_email(input.customer_email)
        if not customer:
            customer = await queries.insert_customer(email=input.customer_email)

        # Get or create active conversation
        conversation = await queries.get_active_conversation(
            customer["id"], input.channel
        )
        if not conversation:
            conversation = await queries.insert_conversation(
                customer_id=customer["id"],
                channel=input.channel,
                subject=input.subject,
            )

        ticket = await queries.insert_ticket(
            customer_id=customer["id"],
            channel=input.channel,
            subject=input.subject,
            category=input.category,
            priority=input.priority,
            conversation_id=conversation["id"],
        )

        return json.dumps({
            "ticket_id": str(ticket["id"]),
            "status": ticket["status"],
            "created_at": ticket["created_at"].isoformat(),
        })
    except Exception as e:
        logger.error("create_ticket_failed", error=str(e))
        return json.dumps({"error": f"Failed to create ticket: {e}"})


@function_tool
async def get_customer_history(input: GetHistoryInput) -> str:
    """Get unified customer history across all channels.
    Use this to understand the customer's previous interactions, check if they are
    a returning customer, and provide personalized support."""
    try:
        customer = await queries.get_customer_by_email(input.customer_email)
        if not customer:
            return json.dumps({
                "customer": None,
                "conversations": [],
                "total_tickets": 0,
                "total_conversations": 0,
            })

        conversations = await queries.get_conversations_by_customer(
            customer["id"], limit=input.max_conversations
        )
        tickets = await queries.get_tickets_by_customer(customer["id"])

        conv_list = []
        for conv in conversations:
            messages = await queries.get_conversation_messages(conv["id"], limit=3)
            last_msg = messages[-1]["content"][:100] if messages else ""
            conv_list.append({
                "id": str(conv["id"]),
                "channel": conv["channel"],
                "status": conv["status"],
                "subject": conv.get("subject", ""),
                "message_count": len(messages),
                "created_at": conv["created_at"].isoformat(),
                "last_message": last_msg,
            })

        return json.dumps({
            "customer": {
                "name": customer.get("name", ""),
                "email": customer["email"],
            },
            "conversations": conv_list,
            "total_tickets": len(tickets),
            "total_conversations": len(conversations),
        })
    except Exception as e:
        logger.error("get_history_failed", error=str(e))
        return json.dumps({"error": str(e), "customer": None, "conversations": []})


@function_tool
async def escalate_to_human(input: EscalateInput) -> str:
    """Escalate the current conversation to a human support agent.
    Use this when escalation triggers are detected: legal language, profanity/low sentiment,
    pricing questions, failed knowledge base searches (2+), or explicit human requests.
    This updates the ticket status and publishes an escalation event."""
    try:
        ticket_id = UUID(input.ticket_id)

        # Update ticket status
        await queries.update_ticket_status(
            ticket_id, "escalated", f"Escalated: {input.reason}"
        )

        # Record escalation metric
        ticket = await queries.get_ticket(ticket_id)
        channel = ticket["channel"] if ticket else None
        await queries.insert_metric(
            "escalation", 1.0, channel=channel,
            dimensions={"ticket_id": input.ticket_id, "reason": input.reason},
        )

        # Publish to Kafka escalation topic
        await _publish_to_kafka("fte.escalations", {
            "ticket_id": input.ticket_id,
            "reason": input.reason,
            "urgency": input.urgency,
            "channel": channel,
        })

        # Update conversation status if available
        if ticket and ticket.get("conversation_id"):
            await queries.update_conversation_status(
                ticket["conversation_id"], "escalated", "human"
            )

        return json.dumps({
            "escalated": True,
            "escalation_id": input.ticket_id,
            "message": f"This conversation has been escalated to our support team. Reference: {input.ticket_id}",
        })
    except Exception as e:
        logger.error("escalation_failed", error=str(e))
        return json.dumps({"error": str(e), "escalated": False})


@function_tool
async def send_response(input: SendResponseInput) -> str:
    """Send a channel-formatted response to the customer.
    This MUST be called LAST after all other tools have been used.
    Applies channel-specific formatting (email: formal, whatsapp: concise, web: semi-formal)
    and stores the response in the database."""
    try:
        start_time = time.time()
        ticket_id = UUID(input.ticket_id)

        # Get ticket for context
        ticket = await queries.get_ticket(ticket_id)
        customer_name = None
        conversation_id = None

        if ticket:
            customer = await queries.get_customer_by_id(ticket["customer_id"])
            customer_name = customer.get("name") if customer else None
            conversation_id = ticket.get("conversation_id")

        # Apply channel-specific formatting
        formatted = formatter.format(
            message=input.message,
            channel=input.channel,
            customer_name=customer_name,
            ticket_id=input.ticket_id,
        )

        # Store outbound message
        processing_time = int((time.time() - start_time) * 1000)
        if conversation_id:
            await queries.insert_message(
                conversation_id=conversation_id,
                channel=input.channel,
                direction="outbound",
                role="agent",
                content=formatted,
                processing_time_ms=processing_time,
            )

        # Record response time metric
        await queries.insert_metric(
            "response_time", float(processing_time), channel=input.channel,
            dimensions={"ticket_id": input.ticket_id},
        )

        # Publish to channel-specific outbound topic
        outbound_topic = f"fte.channels.{input.channel}.outbound"
        if input.channel == "web":
            outbound_topic = "fte.channels.webform.outbound"
        await _publish_to_kafka(outbound_topic, {
            "ticket_id": input.ticket_id,
            "channel": input.channel,
            "content": formatted,
        })

        return json.dumps({
            "sent": True,
            "channel": input.channel,
            "formatted_length": len(formatted),
            "message_id": str(conversation_id) if conversation_id else "no_conversation",
        })
    except Exception as e:
        logger.error("send_response_failed", error=str(e))
        return json.dumps({"error": str(e), "sent": False})


@function_tool
async def analyze_sentiment(input: SentimentInput) -> str:
    """Analyze the sentiment of a customer message.
    Returns a score from 0.0 (very negative) to 1.0 (very positive).
    If sentiment is below 0.3, the conversation should be escalated.
    Sentiment MUST be checked before closing any conversation."""
    try:
        score, label = _compute_sentiment(input.text)

        # Record sentiment metric
        await queries.insert_metric("sentiment", score)

        return json.dumps({
            "score": score,
            "label": label,
            "confidence": 0.8,
        })
    except Exception as e:
        logger.error("sentiment_failed", error=str(e))
        return json.dumps({"error": str(e), "score": 0.5, "label": "neutral"})
