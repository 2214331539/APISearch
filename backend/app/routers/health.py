from __future__ import annotations

from fastapi import APIRouter

from app.services.container import api_store

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health() -> dict:
    return {
        "status": "ok",
        "db": "ok",
        "vector_store": "local-text",
        "embedding_provider": "not-configured",
        "total_apis": len(api_store.all()),
    }
