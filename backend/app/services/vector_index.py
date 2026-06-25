from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np

from app.services.embedding_service import LocalEmbeddingProvider
from app.services.vector_store import LocalVectorStore


def _overview_text(api: Dict) -> str:
    parts = [
        api.get("name", ""),
        api.get("number", ""),
        api.get("method_name", ""),
        api.get("url", ""),
        api.get("http_method", ""),
        api.get("cloud", ""),
        api.get("app", ""),
        api.get("group", ""),
        api.get("description", ""),
    ]
    return " ".join(part for part in parts if part).strip()


def build_chunks(api: Dict) -> List[Tuple[str, str]]:
    """Return (chunk_type, text) pairs for one API.

    Minimal scheme per the design doc: an ``overview`` chunk for intent matching
    plus a ``full`` chunk (the precomputed search_text) for recall fallback.
    """
    chunks: List[Tuple[str, str]] = []
    overview = _overview_text(api)
    if overview:
        chunks.append(("overview", overview))
    full = (api.get("search_text") or "").strip()
    if full and full != overview:
        chunks.append(("full", full[:2000]))
    if not chunks:
        chunks.append(("overview", api.get("name", "") or api.get("number", "")))
    return chunks


class VectorIndexService:
    def __init__(
        self,
        embedder: LocalEmbeddingProvider,
        store: LocalVectorStore,
        query_prefix: str = "",
    ) -> None:
        self.embedder = embedder
        self.store = store
        self.query_prefix = query_prefix

    @property
    def is_ready(self) -> bool:
        return self.store.ready

    def _chunk_texts(self, apis: List[Dict]) -> Tuple[List[str], List[Dict]]:
        texts: List[str] = []
        payloads: List[Dict] = []
        for api in apis:
            for chunk_type, text in build_chunks(api):
                texts.append(text)
                payloads.append({"api_id": api["api_id"], "chunk_type": chunk_type})
        return texts, payloads

    def rebuild(self, apis: List[Dict], batch_log=None) -> int:
        texts, payloads = self._chunk_texts(apis)
        if not texts:
            return 0
        if batch_log:
            batch_log(f"embedding {len(texts)} chunks from {len(apis)} APIs ...")
        vectors = self.embedder.embed(texts)
        self.store.replace(vectors, payloads)
        if batch_log:
            batch_log(f"stored {self.store.size} vectors (dim={vectors.shape[1]})")
        return self.store.size

    def upsert_apis(self, apis: List[Dict]) -> int:
        """Re-embed only the given (created/updated) APIs and upsert them.

        Old chunks for these api_ids are dropped and replaced, so an API whose
        params shrank doesn't leave stale vectors behind. Everything else in the
        index is left untouched.
        """
        ids = [api["api_id"] for api in apis]
        if not ids:
            return self.store.size
        texts, payloads = self._chunk_texts(apis)
        vectors = (
            self.embedder.embed(texts) if texts else np.empty((0, 0), dtype=np.float32)
        )
        self.store.upsert(ids, vectors, payloads)
        return self.store.size

    def remove_apis(self, api_ids: List[str]) -> int:
        self.store.remove(api_ids)
        return self.store.size

    def api_scores(self, queries) -> Dict[str, float]:
        """Max cosine per api_id over one or more query variants.

        Passing both the raw and the LLM-normalized query lets clean intent and
        slang-to-domain mapping each contribute; we keep the best match per API.
        """
        if isinstance(queries, str):
            queries = [queries]
        variants = [self.query_prefix + q for q in queries if q and q.strip()]
        # Take one consistent snapshot so a concurrent incremental upsert can't
        # desync vectors from payloads mid-scoring.
        vectors, payloads = self.store.snapshot()
        if vectors is None or not payloads or not variants:
            return {}
        qvecs = self.embedder.embed(variants)  # (V, dim)
        # Best similarity across query variants for every stored vector.
        with np.errstate(all="ignore"):
            per_vector = vectors @ qvecs.T  # (N, V)
        best = per_vector.max(axis=1)
        scores: Dict[str, float] = {}
        for payload, cos in zip(payloads, best):
            api_id = payload["api_id"]
            value = float(cos)
            if value > scores.get(api_id, -1.0):
                scores[api_id] = value
        return scores
