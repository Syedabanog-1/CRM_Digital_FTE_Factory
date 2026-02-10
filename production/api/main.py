"""FastAPI application - main entry point for the Stage 2 production API.

Exposes 8 endpoints: health, webhooks (gmail, whatsapp), support (submit, ticket status),
customer lookup, conversation history, and channel metrics.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from production.config import settings
from production.database import queries
from production.logging_config import setup_logging, get_logger, bind_correlation_id, clear_contextvars
from production.channels.web_form_handler import router as web_form_router
from production.channels.gmail_handler import router as gmail_router
from production.channels.whatsapp_handler import router as whatsapp_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    setup_logging(settings.log_level)
    logger.info("api_starting", port=settings.api_port)

    # Create database pool
    await queries.create_pool()
    logger.info("database_pool_created")

    # Start Kafka producer
    try:
        from production.kafka_client import get_producer
        await get_producer()
        logger.info("kafka_producer_ready")
    except Exception as e:
        logger.warning("kafka_producer_startup_failed", error=str(e))

    yield

    # Shutdown
    logger.info("api_shutting_down")
    await queries.close_pool()

    try:
        from production.kafka_client import stop_producer
        await stop_producer()
    except Exception:
        pass


app = FastAPI(
    title="TechCorp Customer Success Digital FTE",
    description="Production-grade AI customer support across email, WhatsApp, and web form",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include channel routers
app.include_router(web_form_router)
app.include_router(gmail_router)
app.include_router(whatsapp_router)


# ---- Endpoints ----


@app.get("/health")
async def health_check():
    """Health check for liveness and readiness probes."""
    db_healthy = await queries.check_db_health()

    kafka_healthy = False
    try:
        from production.kafka_client import check_kafka_health
        kafka_healthy = await check_kafka_health()
    except Exception:
        pass

    status = "healthy" if db_healthy else "unhealthy"
    status_code = 200 if db_healthy else 503

    response = {
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "channels": {
            "email": "connected" if settings.gmail_credentials_json else "not_configured",
            "whatsapp": "connected" if settings.twilio_account_sid else "not_configured",
            "web": "active",
        },
        "database": "connected" if db_healthy else "disconnected",
        "kafka": "connected" if kafka_healthy else "disconnected",
    }

    if not db_healthy:
        from fastapi.responses import JSONResponse
        return JSONResponse(content=response, status_code=503)

    return response


@app.get("/customers/lookup")
async def customer_lookup(
    email: str | None = Query(None, description="Customer email"),
    phone: str | None = Query(None, description="Customer phone number"),
):
    """Look up a customer's unified profile across channels."""
    if not email and not phone:
        raise HTTPException(
            status_code=400, detail="At least one of email or phone is required"
        )

    customer = None
    if email:
        customer = await queries.get_customer_by_email(email)
    if not customer and phone:
        customer = await queries.get_customer_by_phone(phone)

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Get identifiers
    pool = await queries.get_pool()
    identifiers = await pool.fetch(
        "SELECT type, value, verified FROM customer_identifiers WHERE customer_id = $1",
        customer["id"],
    )

    conversations = await queries.get_conversations_by_customer(customer["id"])
    tickets = await queries.get_tickets_by_customer(customer["id"])

    channels_used = list(set(c["channel"] for c in conversations))

    return {
        "customer_id": str(customer["id"]),
        "name": customer.get("name"),
        "email": customer["email"],
        "phone": customer.get("phone"),
        "identifiers": [dict(i) for i in identifiers],
        "total_conversations": len(conversations),
        "total_tickets": len(tickets),
        "channels_used": channels_used,
        "created_at": customer["created_at"].isoformat(),
    }


@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get full conversation history with all messages."""
    try:
        conv_id = UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation ID format")

    conversation = await queries.get_conversation(conv_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    customer = await queries.get_customer_by_id(conversation["customer_id"])
    messages = await queries.get_conversation_messages(conv_id)

    return {
        "conversation_id": str(conversation["id"]),
        "customer": {
            "id": str(customer["id"]) if customer else None,
            "name": customer.get("name") if customer else None,
            "email": customer.get("email") if customer else None,
        },
        "channel": conversation["channel"],
        "status": conversation["status"],
        "sentiment_score": conversation.get("sentiment_score"),
        "messages": [
            {
                "id": str(m["id"]),
                "role": m["role"],
                "content": m["content"],
                "channel": m["channel"],
                "direction": m["direction"],
                "processing_time_ms": m.get("processing_time_ms"),
                "created_at": m["created_at"].isoformat(),
            }
            for m in messages
        ],
        "created_at": conversation["created_at"].isoformat(),
        "updated_at": conversation["updated_at"].isoformat(),
    }


@app.get("/metrics/channels")
async def channel_metrics(
    hours: int = Query(default=24, ge=1, le=720, description="Lookback hours"),
    channel: str | None = Query(None, description="Filter by channel"),
):
    """Get per-channel performance metrics for the given time period."""
    return await queries.get_channel_metrics(hours=hours, channel=channel)
