from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.middleware import install_middleware
from app.api.v1 import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import engine

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings.validate_runtime_safety()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("database_connection_ok")
    except Exception as exc: 
        logger.error("database_connection_failed", extra={"extra_fields": {"error": type(exc).__name__}})
    if not settings.audit_checkpoint_private_key:
        logger.warning("audit_checkpoint_signature_disabled")
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="ArtBid API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={"name": "ArtBid Backend"},
    )

    if settings.cors_origins_list:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins_list,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-Id", "Last-Event-ID"],
            expose_headers=["X-Request-Id", "Retry-After"],
            max_age=600,
        )

    install_middleware(application)
    application.include_router(api_router, prefix=settings.api_prefix)

    @application.get("/health", tags=["ops"], summary="Health check")
    def health() -> dict:
        database_ok = True
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception as e:
            database_ok = False
        return {"data": {"status": "ok" if database_ok else "degraded", "database": database_ok}}

    @application.get("/health/ready", tags=["ops"], summary="Readiness (base de dados)")
    def readiness() -> dict:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"data": {"status": "ready"}}

    return application


app = create_app()

