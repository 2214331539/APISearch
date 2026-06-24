from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Dict, List, Optional

from app.models.schemas import UploadJob


class JobStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._jobs: Dict[str, UploadJob] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        self._jobs = {item["job_id"]: UploadJob(**item) for item in payload}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump([job.dict() for job in self._jobs.values()], handle, ensure_ascii=False, indent=2, default=str)

    def create(self, job: UploadJob) -> UploadJob:
        with self._lock:
            self._jobs[job.job_id] = job
            self.save()
            return job

    def get(self, job_id: str) -> Optional[UploadJob]:
        return self._jobs.get(job_id)

    def list_recent(self, limit: int = 20) -> List[UploadJob]:
        return sorted(self._jobs.values(), key=lambda job: job.job_id, reverse=True)[:limit]

    def update(self, job_id: str, **changes) -> Optional[UploadJob]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            data = job.dict()
            data.update(changes)
            self._jobs[job_id] = UploadJob(**data)
            self.save()
            return self._jobs[job_id]
