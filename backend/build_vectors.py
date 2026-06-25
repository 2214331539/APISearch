"""Build the local vector index for all APIs in the store.

Run from the repo root:

    PYTHONPATH=backend backend/.venv/bin/python backend/build_vectors.py
    # or: npm run backend:build-vectors
"""
from __future__ import annotations

import time

from app.core.config import settings
from app.services.api_store import ApiStore
from app.services.embedding_service import LocalEmbeddingProvider
from app.services.vector_index import VectorIndexService
from app.services.vector_store import LocalVectorStore


def main() -> None:
    settings.ensure_dirs()
    embedder = LocalEmbeddingProvider(settings.embedding_model, settings.embedding_cache_dir)
    if not embedder.available:
        raise SystemExit(
            f"Embedding model not found in {settings.embedding_cache_dir}. "
            f"Seed it first (model: {settings.embedding_model})."
        )
    api_store = ApiStore(settings.api_store_path, settings.seed_index_path)
    store = LocalVectorStore(settings.vectors_path)
    index = VectorIndexService(embedder, store)

    apis = api_store.all()
    started = time.time()
    count = index.rebuild(apis, batch_log=lambda message: print(f"[build] {message}"))
    print(f"[build] done: {count} vectors for {len(apis)} APIs in {time.time() - started:.1f}s")
    print(f"[build] saved to {settings.vectors_path}")


if __name__ == "__main__":
    main()
