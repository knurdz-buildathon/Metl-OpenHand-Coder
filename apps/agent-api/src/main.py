"""FastAPI application entry point for the Metl Agent API."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import jobs, previews, reports, v0
from src.core.config import settings
from src.core.database import engine

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle handler."""
    logger.info("Starting Metl Agent API")
    # Auto-create tables for SQLite (harmless if tables exist)
    from src.models.database import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ensured")
    yield
    logger.info("Shutting down Metl Agent API")
    await engine.dispose()
    logger.info("Database engine disposed")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Metl Agent API",
        description="Backend API for the Metl autonomous coding agent",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://code.metl.run",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(jobs.router)
    app.include_router(previews.router)
    app.include_router(reports.router)
    app.include_router(v0.router)

    @app.get("/health", tags=["health"])
    async def health_check() -> dict:
        """Basic health check endpoint."""
        return {"status": "ok", "version": "0.1.0"}

    @app.get("/", tags=["root"])
    async def root() -> dict:
        """Root endpoint with API info."""
        return {
            "name": "Metl Agent API",
            "version": "0.1.0",
            "docs": "/docs",
        }

    return app


app = create_app()