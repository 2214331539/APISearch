from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import IndexStats
from app.services.container import api_store

router = APIRouter(prefix="/index", tags=["index"])


@router.get("/stats", response_model=IndexStats)
def index_stats() -> IndexStats:
    return api_store.stats()
