from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np


class LocalVectorStore:
    """In-memory brute-force cosine store, persisted to disk.

    Vectors are assumed L2-normalized, so cosine similarity is a plain dot
    product. At ~3.5k vectors x 512 dims this is a few MB and searches in well
    under a millisecond, so no ANN index is needed.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.payload_path = self.path.with_suffix(".json")
        self.vectors: Optional[np.ndarray] = None  # (N, dim) float32, normalized
        self.payloads: List[Dict] = []
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
        self.vectors = np.asarray(vectors, dtype=np.float32)
        self.payloads = list(payloads)
        self.save()

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
