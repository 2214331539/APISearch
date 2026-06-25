from __future__ import annotations

import os
from pathlib import Path


def _load_env_file() -> None:
    """Lightweight .env loader so we don't add a runtime dependency.

    Reads backend/.env (and backend/.env.local) and populates os.environ for any
    key that is not already set in the real environment.
    """
    backend_dir = Path(__file__).resolve().parents[2]
    for name in (".env", ".env.local"):
        env_path = backend_dir / name
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_env_file()


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


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

        # LLM agent (query rewrite). Gemini-compatible proxy endpoint.
        self.enable_llm_agent = _as_bool(os.getenv("ENABLE_LLM_AGENT", "false"))
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.gemini_base_url = os.getenv(
            "GEMINI_BASE_URL", "https://aicenter.thyseed.com/v1beta"
        ).rstrip("/")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
        self.llm_timeout = float(os.getenv("LLM_TIMEOUT", "20"))

        # Local embedding / vector search.
        self.enable_vector_search = _as_bool(os.getenv("ENABLE_VECTOR_SEARCH", "false"))
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
        self.embedding_cache_dir = Path(
            os.getenv("EMBEDDING_CACHE_DIR", self.storage_dir / "models")
        )
        self.vectors_path = Path(os.getenv("VECTORS_PATH", self.storage_dir / "vectors.npz"))
        # bge-zh retrieval works best with an instruction prefix on the QUERY side
        # only (documents are embedded as-is).
        self.embedding_query_prefix = os.getenv(
            "EMBEDDING_QUERY_PREFIX", "为这个句子生成表示以用于检索相关文章："
        )

    def ensure_dirs(self) -> None:
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
