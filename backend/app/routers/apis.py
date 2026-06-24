from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import ApiDoc, IndexStats
from app.services.container import api_store

router = APIRouter(prefix="/apis", tags=["apis"])


@router.get("/{api_id}", response_model=ApiDoc)
def get_api(api_id: str) -> ApiDoc:
    api = api_store.get(api_id)
    if api is None:
        raise HTTPException(status_code=404, detail="API not found")
    return api


@router.get("", response_model=list[ApiDoc])
def list_apis(limit: int = 50, offset: int = 0, q: str = "") -> list[ApiDoc]:
    items = api_store.all()
    if q:
        q_norm = q.lower()
        items = [
            api
            for api in items
            if q_norm in (api.get("name", "") + api.get("number", "") + api.get("url", "")).lower()
        ]
    return [ApiDoc(**item) for item in items[offset : offset + min(limit, 200)]]


@router.get("/../index/stats", response_model=IndexStats, include_in_schema=False)
def legacy_stats() -> IndexStats:
    return api_store.stats()
