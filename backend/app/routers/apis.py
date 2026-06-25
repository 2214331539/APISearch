from __future__ import annotations

from fastapi import APIRouter, HTTPException

from typing import Optional

from app.models.schemas import ApiDoc, ApiListResponse, IndexStats
from app.services.container import api_store

router = APIRouter(prefix="/apis", tags=["apis"])


@router.get("", response_model=ApiListResponse)
def list_apis(
    cloud: Optional[str] = None,
    app: Optional[str] = None,
    api_type: Optional[str] = None,
    q: str = "",
    limit: int = 50,
    offset: int = 0,
) -> ApiListResponse:
    """Browse APIs with optional cloud/app/type filters and pagination."""
    result = api_store.list_filtered(
        cloud=cloud, app=app, api_type=api_type, q=q or None, limit=limit, offset=offset
    )
    return ApiListResponse(**result)


@router.get("/{api_id}", response_model=ApiDoc)
def get_api(api_id: str) -> ApiDoc:
    api = api_store.get(api_id)
    if api is None:
        raise HTTPException(status_code=404, detail="API not found")
    return api


@router.get("/../index/stats", response_model=IndexStats, include_in_schema=False)
def legacy_stats() -> IndexStats:
    return api_store.stats()
