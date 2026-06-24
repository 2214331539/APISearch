from __future__ import annotations

import os
from pathlib import Path


class Settings:
    def __init__(self) -> None:
        self.root_dir = Path(__file__).resolve().parents[3]
        self.storage_dir = self.root_dir / "storage"
        self.upload_dir = Path(os.getenv("UPLOAD_DIR", self.storage_dir / "uploads"))
        self.snapshot_dir = Path(os.getenv("SNAPSHOT_DIR", self.storage_dir / "snapshots"))
        self.api_store_path = Path(os.getenv("API_STORE_PATH", self.storage_dir / "apis.json"))
        self.job_store_path = Path(os.getenv("JOB_STORE_PATH", self.storage_dir / "jobs.json"))
        self.seed_index_path = Path(os.getenv("SEED_INDEX_PATH", self.root_dir / "api_index.json"))
        self.max_upload_mb = int(os.getenv("MAX_UPLOAD_MB", "100"))
        self.cors_origins = [
            origin.strip()
            for origin in os.getenv(
                "CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            ).split(",")
            if origin.strip()
        ]

    def ensure_dirs(self) -> None:
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
