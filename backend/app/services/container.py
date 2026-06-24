from __future__ import annotations

from app.core.config import settings
from app.services.api_store import ApiStore
from app.services.ingestion_service import IngestionService
from app.services.job_store import JobStore
from app.services.search_service import SearchService


settings.ensure_dirs()
api_store = ApiStore(settings.api_store_path, settings.seed_index_path)
job_store = JobStore(settings.job_store_path)
ingestion_service = IngestionService(api_store, job_store)
search_service = SearchService(api_store)
