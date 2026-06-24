from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import apis, health, index, search, uploads


def create_app() -> FastAPI:
    app = FastAPI(
        title="API Search Agent",
        version="0.1.0",
        description="Single-page API documentation search and ingestion backend.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, prefix="/api")
    app.include_router(uploads.router, prefix="/api")
    app.include_router(search.router, prefix="/api")
    app.include_router(apis.router, prefix="/api")
    app.include_router(index.router, prefix="/api")
    return app


app = create_app()
