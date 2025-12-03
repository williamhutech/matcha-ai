"""FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.llm import is_llm_warmed, warm_llm
from app.telemetry import setup_logging
from app.whatsapp import router as whatsapp_router
from app.api import router as api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI application."""
    # Startup
    setup_logging()
    yield
    # Shutdown
    pass


app = FastAPI(
    title="Matcha AI",
    description="Multi-agent job matching via WhatsApp Business API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for Chainlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(whatsapp_router, prefix="/webhooks")
app.include_router(api_router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return JSONResponse(
        content={
            "service": "Matcha AI",
            "status": "healthy",
            "environment": settings.environment,
        }
    )


@app.get("/health")
async def health():
    """Detailed health check endpoint."""
    return JSONResponse(
        content={
            "status": "healthy",
            "checks": {
                "api": "ok",
                "llm_warmed": is_llm_warmed(),
            },
        }
    )


async def _warm_in_background():
    """Background task to warm the LLM client."""
    try:
        await warm_llm()
    except Exception as e:
        logger.error(f"Background warming failed: {e}")


@app.get("/warm")
async def warm(background_tasks: BackgroundTasks):
    """
    Warm endpoint to pre-initialize the server.

    This endpoint serves two purposes:
    1. Triggers Fly.io to start a stopped machine (auto_start_machines=true)
    2. Pre-warms the LLM client in the background to reduce first-request latency

    Returns immediately so the frontend knows the server is warming.
    """
    already_warm = is_llm_warmed()

    if not already_warm:
        background_tasks.add_task(_warm_in_background)

    return JSONResponse(
        content={
            "status": "warm" if already_warm else "warming",
            "machine_started": True,
            "llm_cached": already_warm,
            "llm_warming": not already_warm,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
