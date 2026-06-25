from __future__ import annotations

import logging
import shutil
import traceback
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from app.services.api_store import ApiStore
from app.services.identity import now_utc
from app.services.job_store import JobStore
from app.services.parsers.registry import ParserRegistry

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(
        self,
        api_store: ApiStore,
        job_store: JobStore,
        vector_index=None,
    ) -> None:
        self.api_store = api_store
        self.job_store = job_store
        self.vector_index = vector_index
        self.parsers = ParserRegistry()

    def process_files(self, job_id: str, paths: Iterable[Path], mode: str = "incremental") -> None:
        parsed_files = 0
        failed_files = 0
        all_apis: List[dict] = []
        self.job_store.update(job_id, status="parsing", started_at=now_utc())
        try:
            for path in paths:
                try:
                    docs = self.parsers.parse_file(path)
                    all_apis.extend(docs)
                    parsed_files += 1
                    self.job_store.update(
                        job_id,
                        parsed_files=parsed_files,
                        failed_files=failed_files,
                        total_apis=len(all_apis),
                    )
                except Exception:
                    failed_files += 1
                    self.job_store.update(job_id, failed_files=failed_files)

            self.job_store.update(job_id, status="indexing", total_apis=len(all_apis))
            stats = self.api_store.upsert_many(all_apis, source_type="upload", mode=mode)
            self._sync_vectors(stats, mode)
            self.job_store.update(
                job_id,
                status="completed",
                parsed_files=parsed_files,
                failed_files=failed_files,
                total_apis=stats["total"],
                created_apis=stats["created"],
                updated_apis=stats["updated"],
                skipped_apis=stats["skipped"],
                finished_at=now_utc(),
            )
        except Exception as exc:
            self.job_store.update(
                job_id,
                status="failed",
                error_message=f"{exc}\n{traceback.format_exc(limit=3)}",
                finished_at=now_utc(),
            )

    def _sync_vectors(self, stats: Dict[str, Any], mode: str) -> None:
        """Keep the vector index in step with the metadata that just landed.

        - rebuild  -> re-embed everything (the index is being reset anyway).
        - incremental -> embed only the created/updated APIs and upsert them,
          but only when a full base index already exists; bootstrapping the
          index from scratch still goes through ``build_vectors.py`` so we never
          ship a half-populated index where most APIs have no vector.

        Best-effort: metadata is already persisted, so a vector failure (e.g.
        the embedding model isn't available) must not fail the upload job.
        """
        index = self.vector_index
        if index is None:
            return
        try:
            if mode == "rebuild":
                count = index.rebuild(self.api_store.all())
                logger.info("vector index rebuilt: %s vectors", count)
            elif index.is_ready:
                changed = self.api_store.raw_many(stats.get("changed_ids", []))
                if changed:
                    count = index.upsert_apis(changed)
                    logger.info("vector index upserted %s APIs -> %s vectors", len(changed), count)
            else:
                logger.info(
                    "vector index not built yet; skipping incremental sync "
                    "(run build_vectors.py to bootstrap)"
                )
        except Exception:
            logger.warning("vector sync failed; metadata is saved, vectors are stale", exc_info=True)


def save_upload_file(src, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as handle:
        shutil.copyfileobj(src, handle)
