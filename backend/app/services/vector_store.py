from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np


class LocalVectorStore:
    """In-memory brute-force cosine store, persisted to disk.

    Vectors are assumed L2-normalized, so cosine similarity is a plain dot
    product. At ~3.5k vectors x 512 dims this is a few MB and searches in well
    under a millisecond, so no ANN index is needed.

    Writes (``replace``/``upsert``/``remove``) are serialized by a lock and
    always swap in brand-new arrays/lists rather than mutating in place, so a
    concurrent reader that took a ``snapshot`` keeps a consistent view.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.payload_path = self.path.with_suffix(".json")
        self.vectors: Optional[np.ndarray] = None  # (N, dim) float32, normalized
        self.payloads: List[Dict] = []
        self._lock = threading.Lock()
        self.load()

    @property
    def ready(self) -> bool:
        return self.vectors is not None and len(self.payloads) > 0

    @property
    def size(self) -> int:
        return 0 if self.vectors is None else int(self.vectors.shape[0])

    def load(self) -> None:
        if not self.path.exists() or not self.payload_path.exists():
            return
        data = np.load(self.path)
        self.vectors = data["vectors"].astype(np.float32)
        self.payloads = json.loads(self.payload_path.read_text(encoding="utf-8"))

    def replace(self, vectors: np.ndarray, payloads: List[Dict]) -> None:
        """Full overwrite of the whole index (used by a from-scratch rebuild)."""
        with self._lock:
            self.vectors = np.asarray(vectors, dtype=np.float32)
            self.payloads = list(payloads)
            self.save()

    def snapshot(self) -> Tuple[Optional[np.ndarray], List[Dict]]:
        """Return a consistent (vectors, payloads) pair for a reader.

        Both refs are captured under the lock; writers never mutate these
        objects in place, so the returned pair stays aligned even if a write
        lands immediately afterwards.
        """
        with self._lock:
            return self.vectors, self.payloads

    def upsert(self, api_ids: Iterable[str], vectors: np.ndarray, payloads: List[Dict]) -> None:
        """Replace every chunk belonging to ``api_ids`` with the new ones.

        Existing rows for those api_ids are dropped first, then the freshly
        embedded rows are appended. Rows for all other APIs are kept untouched,
        so only the changed APIs pay the embedding cost.
        """
        ids = set(api_ids)
        new_vecs = np.asarray(vectors, dtype=np.float32)
        if new_vecs.ndim == 1 and new_vecs.size:
            new_vecs = new_vecs.reshape(1, -1)
        new_payloads = list(payloads)
        with self._lock:
            if self.vectors is None or not self.payloads:
                kept_vecs: Optional[np.ndarray] = None
                kept_payloads: List[Dict] = []
            else:
                keep = [i for i, p in enumerate(self.payloads) if p.get("api_id") not in ids]
                kept_vecs = self.vectors[keep] if keep else None
                kept_payloads = [self.payloads[i] for i in keep]
            parts = [v for v in (kept_vecs, new_vecs if new_payloads else None) if v is not None]
            self.vectors = (np.vstack(parts) if len(parts) > 1 else parts[0]) if parts else None
            self.payloads = kept_payloads + new_payloads
            self.save()

    def remove(self, api_ids: Iterable[str]) -> None:
        """Drop all chunks for the given api_ids (e.g. deleted APIs)."""
        self.upsert(api_ids, np.empty((0, 0), dtype=np.float32), [])

    def save(self) -> None:
        if self.vectors is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(self.path, vectors=self.vectors)
        # np.savez always appends .npz; normalize the filename back.
        produced = self.path if self.path.suffix == ".npz" else Path(str(self.path) + ".npz")
        if produced != self.path and produced.exists():
            produced.replace(self.path)
        self.payload_path.write_text(
            json.dumps(self.payloads, ensure_ascii=False), encoding="utf-8"
        )

    def cosine_all(self, query_vector: np.ndarray) -> np.ndarray:
        """Cosine similarity of the query against every stored vector."""
        if not self.ready:
            return np.empty(0, dtype=np.float32)
        # Inputs are L2-normalized and finite; numpy's vectorized matmul can still
        # raise spurious FP flags from unused SIMD lanes, so silence them here.
        with np.errstate(all="ignore"):
            return self.vectors @ np.asarray(query_vector, dtype=np.float32)
