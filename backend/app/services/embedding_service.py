from __future__ import annotations

import threading
from pathlib import Path
from typing import List

import numpy as np


class LocalEmbeddingProvider:
    """Local ONNX embedding via fastembed (no torch, offline).

    The model is loaded lazily from a pre-populated cache directory with
    ``local_files_only=True`` so it never reaches out to HuggingFace (which is
    unreachable here — the model was seeded from the Qdrant GCS tarball).
    """

    def __init__(self, model_name: str, cache_dir: Path) -> None:
        self.model_name = model_name
        self.cache_dir = Path(cache_dir)
        self._model = None
        self._dim: int | None = None
        self._load_lock = threading.Lock()

    @property
    def available(self) -> bool:
        """True when the model files are present on disk."""
        local_name = "fast-" + self.model_name.split("/")[-1]
        return (self.cache_dir / local_name).exists() or (
            self.cache_dir / f"models--{self.model_name.replace('/', '--')}"
        ).exists()

    def _ensure_model(self):
        # Double-checked locking: the model is loaded once even if a search and a
        # background ingestion both reach for it at the same time.
        if self._model is None:
            with self._load_lock:
                if self._model is None:
                    from fastembed import TextEmbedding

                    self._model = TextEmbedding(
                        model_name=self.model_name,
                        cache_dir=str(self.cache_dir),
                        local_files_only=True,
                    )
        return self._model

    def embed(self, texts: List[str]) -> np.ndarray:
        """Return L2-normalized embeddings as a (N, dim) float32 array."""
        model = self._ensure_model()
        vectors = np.asarray(list(model.embed(texts)), dtype=np.float32)
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)
        vectors = np.nan_to_num(vectors, nan=0.0, posinf=0.0, neginf=0.0)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized = np.nan_to_num(vectors / norms, nan=0.0, posinf=0.0, neginf=0.0)
        self._dim = normalized.shape[1]
        return normalized.astype(np.float32)

    def embed_one(self, text: str) -> np.ndarray:
        return self.embed([text])[0]

    @property
    def dim(self) -> int | None:
        return self._dim
