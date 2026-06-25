from __future__ import annotations

from fastapi import APIRouter

from app.services.container import api_store, query_rewriter, vector_index

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health() -> dict:
    llm_status = "enabled" if (query_rewriter is not None and query_rewriter.enabled) else "disabled"
    vector_ready = vector_index is not None and vector_index.is_ready
    return {
        "status": "ok",
        "db": "ok",
        "vector_store": "local-numpy" if vector_ready else "local-text",
        "embedding_provider": "bge-small-zh (local)" if vector_ready else "not-configured",
        "vector_chunks": vector_index.store.size if vector_ready else 0,
        "llm_agent": llm_status,
        "total_apis": len(api_store.all()),
    }
