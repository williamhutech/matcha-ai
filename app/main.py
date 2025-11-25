"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.telemetry import setup_logging
from app.whatsapp import router as whatsapp_router
from app.api import router as api_router


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
                # Add more health checks as needed (db, external APIs, etc.)
            },
        }
    )
