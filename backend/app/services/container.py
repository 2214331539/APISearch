from __future__ import annotations

from app.core.config import settings
from app.services.agent_service import QueryRewriter
from app.services.api_store import ApiStore
from app.services.ingestion_service import IngestionService
from app.services.job_store import JobStore
from app.services.llm_client import GeminiClient
from app.services.embedding_service import LocalEmbeddingProvider
from app.services.search_service import SearchService
from app.services.vector_index import VectorIndexService
from app.services.vector_store import LocalVectorStore


settings.ensure_dirs()
api_store = ApiStore(settings.api_store_path, settings.seed_index_path)
job_store = JobStore(settings.job_store_path)

query_rewriter = None
if settings.enable_llm_agent:
    gemini_client = GeminiClient(
        api_key=settings.gemini_api_key,
        base_url=settings.gemini_base_url,
        model=settings.gemini_model,
        timeout=settings.llm_timeout,
    )
    query_rewriter = QueryRewriter(gemini_client)

embedder = LocalEmbeddingProvider(settings.embedding_model, settings.embedding_cache_dir)
vector_store = LocalVectorStore(settings.vectors_path)
vector_index = None
if settings.enable_vector_search and embedder.available:
    vector_index = VectorIndexService(
        embedder, vector_store, query_prefix=settings.embedding_query_prefix
    )

# Ingestion keeps the vector index in step incrementally on every upload.
ingestion_service = IngestionService(api_store, job_store, vector_index=vector_index)

search_service = SearchService(
    api_store, query_rewriter=query_rewriter, vector_index=vector_index
)
