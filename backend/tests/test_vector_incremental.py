"""Incremental vector-index maintenance (no embedding model required).

Uses a tiny deterministic fake embedder so the contract is tested without the
~52MB bge model: created/updated APIs are re-embedded and upserted, stale
chunks from a shrunk API are dropped, and the store stays consistent and
durable across reloads.
"""
import os
import tempfile

import numpy as np

from app.services.vector_index import VectorIndexService
from app.services.vector_store import LocalVectorStore


class _FakeEmbedder:
    def embed(self, texts):
        out = []
        for text in texts:
            vec = np.zeros(8, dtype=np.float32)
            vec[hash(text) % 8] = 1.0
            out.append(vec)
        return np.asarray(out, dtype=np.float32)


def _api(i, search_text):
    return {
        "api_id": f"id{i}",
        "name": f"接口{i}",
        "number": f"num{i}",
        "url": f"/u/{i}",
        "http_method": "POST",
        "cloud": "供应链",
        "app": "库存",
        "group": "",
        "description": "",
        "method_name": "",
        "search_text": search_text,
    }


def _ids(store):
    return {p["api_id"] for p in store.payloads}


def test_incremental_upsert_add_update_remove(tmp_path=None):
    work = tempfile.mkdtemp()
    store = LocalVectorStore(os.path.join(work, "v.npz"))
    index = VectorIndexService(_FakeEmbedder(), store)

    # Bootstrap: full rebuild with two overview+full APIs.
    index.rebuild([_api(1, "full text one"), _api(2, "full text two")])
    assert _ids(store) == {"id1", "id2"}

    # Add a brand-new API -> appended, others untouched.
    index.upsert_apis([_api(3, "full text three")])
    assert _ids(store) == {"id1", "id2", "id3"}

    # Update id2 so it now yields only an overview chunk -> stale full chunk gone.
    chunks_before = sum(1 for p in store.payloads if p["api_id"] == "id2")
    index.upsert_apis([_api(2, "")])  # empty search_text drops the 'full' chunk
    chunks_after = sum(1 for p in store.payloads if p["api_id"] == "id2")
    assert chunks_before == 2 and chunks_after == 1

    # Snapshot is always aligned: one payload per vector row.
    vectors, payloads = store.snapshot()
    assert vectors is not None and vectors.shape[0] == len(payloads)

    # Remove an API entirely.
    index.remove_apis(["id1"])
    assert "id1" not in _ids(store)

    # Durable across reloads.
    reloaded = LocalVectorStore(os.path.join(work, "v.npz"))
    assert reloaded.size == store.size and _ids(reloaded) == _ids(store)
