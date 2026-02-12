"""FastAPI application - main entry point for the Stage 2 production API.

Exposes 8 endpoints: health, webhooks (gmail, whatsapp), support (submit, ticket status),
customer lookup, conversation history, and channel metrics.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import UUID

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from production.config import settings
from production.database import queries
from production.logging_config import setup_logging, get_logger, bind_correlation_id, clear_contextvars
from production.channels.web_form_handler import router as web_form_router
from production.channels.gmail_handler import router as gmail_router
from production.channels.whatsapp_handler import router as whatsapp_router
from production.api.auth_router import router as auth_router

try:
    from prometheus_fastapi_instrumentator import Instrumentator
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

# Import custom metrics (registers them with prometheus_client registry)
from production.metrics import METRICS_AVAILABLE as _CUSTOM_METRICS  # noqa: F401

logger = get_logger(__name__)


async def _apply_schema():
    """Apply database schema on startup (idempotent - uses IF NOT EXISTS).

    Executes each statement individually so pgvector extension failure
    doesn't block the rest of the schema.
    """
    schema_paths = [
        Path(__file__).resolve().parent.parent / "database" / "schema.sql",
        Path("/app/production/database/schema.sql"),
    ]
    for path in schema_paths:
        if path.is_file():
            pool = await queries.get_pool()
            sql = path.read_text()
            # Split on semicolons and execute each statement
            statements = [s.strip() for s in sql.split(";") if s.strip()]
            applied = 0
            for stmt in statements:
                try:
                    await pool.execute(stmt)
                    applied += 1
                except Exception as e:
                    # pgvector extension or vector columns may fail on free tiers
                    logger.warning("schema_stmt_skipped", error=str(e)[:120])
            logger.info("schema_applied", path=str(path), statements=applied, total=len(statements))
            return
    logger.warning("schema_file_not_found")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    setup_logging(settings.log_level)
    logger.info("api_starting", port=settings.api_port)

    # Create database pool
    await queries.create_pool()
    logger.info("database_pool_created")

    # Auto-apply schema (idempotent)
    await _apply_schema()

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

# Include routers
app.include_router(auth_router)
app.include_router(web_form_router)
app.include_router(gmail_router)
app.include_router(whatsapp_router)

# Prometheus metrics instrumentation
if PROMETHEUS_AVAILABLE:
    Instrumentator(
        should_group_status_codes=False,
        excluded_handlers=["/metrics"],
    ).instrument(app).expose(app, endpoint="/metrics")


# ---- Endpoints ----


@app.get("/ping")
async def ping():
    """Simple liveness probe - no dependencies required."""
    return {"status": "ok"}


@app.get("/debug/schema")
async def debug_schema():
    """Debug endpoint: check tables and apply schema."""
    results = {"tables_before": [], "schema_apply": [], "tables_after": [], "errors": []}
    try:
        pool = await queries.get_pool()
        rows = await pool.fetch("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        results["tables_before"] = [r["tablename"] for r in rows]

        # Try applying schema
        schema_paths = [
            Path(__file__).resolve().parent.parent / "database" / "schema.sql",
            Path("/app/production/database/schema.sql"),
        ]
        for path in schema_paths:
            if path.is_file():
                sql = path.read_text()
                statements = [s.strip() for s in sql.split(";") if s.strip()]
                for i, stmt in enumerate(statements):
                    try:
                        await pool.execute(stmt)
                        results["schema_apply"].append(f"OK[{i}]: {stmt[:60]}")
                    except Exception as e:
                        results["schema_apply"].append(f"FAIL[{i}]: {stmt[:60]} => {str(e)[:100]}")
                        results["errors"].append(str(e)[:200])
                break
        else:
            results["errors"].append("schema.sql not found")

        rows = await pool.fetch("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        results["tables_after"] = [r["tablename"] for r in rows]
    except Exception as e:
        results["errors"].append(f"pool_error: {str(e)[:200]}")
    return results


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


# ---- Static frontend serving ----
# Serve the React web form build if available
_STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "web-form" / "build"
_STATIC_DIR_ALT = Path("/app/web-form/build")

_frontend_dir = None
if _STATIC_DIR.is_dir():
    _frontend_dir = _STATIC_DIR
elif _STATIC_DIR_ALT.is_dir():
    _frontend_dir = _STATIC_DIR_ALT

if _frontend_dir:
    # Serve static assets (JS, CSS, etc.) under /static
    _static_assets = _frontend_dir / "static"
    if _static_assets.is_dir():
        app.mount("/static", StaticFiles(directory=str(_static_assets)), name="static-assets")

    @app.get("/", response_class=FileResponse)
    async def serve_frontend():
        """Serve the frontend web form."""
        return FileResponse(str(_frontend_dir / "index.html"))

    @app.get("/{path:path}")
    async def serve_frontend_fallback(path: str):
        """Serve frontend static files or fall back to index.html for SPA routing."""
        file_path = _frontend_dir / path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_frontend_dir / "index.html"))
