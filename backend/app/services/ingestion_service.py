from __future__ import annotations

import shutil
import traceback
from pathlib import Path
from typing import Iterable, List

from app.services.api_store import ApiStore
from app.services.identity import now_utc
from app.services.job_store import JobStore
from app.services.parsers.registry import ParserRegistry


class IngestionService:
    def __init__(self, api_store: ApiStore, job_store: JobStore) -> None:
        self.api_store = api_store
        self.job_store = job_store
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


def save_upload_file(src, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as handle:
        shutil.copyfileobj(src, handle)
