from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.schemas import ApiDoc, IndexStats
from app.services.identity import count_by, make_content_hash, now_utc
from app.services.normalization import normalize_api


class ApiStore:
    def __init__(self, path: Path, seed_index_path: Path) -> None:
        self.path = path
        self.seed_index_path = seed_index_path
        self._lock = threading.Lock()
        self._apis: Dict[str, Dict[str, Any]] = {}
        self.load()

    def load(self) -> None:
        source = self.path if self.path.exists() else self.seed_index_path
        if not source.exists():
            return
        with source.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        apis = [normalize_api(item, source_type=item.get("source_type", "seed")) for item in payload]
        self._apis = {api["api_id"]: api for api in apis}
        if source == self.seed_index_path:
            self.save()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        apis = sorted(self._apis.values(), key=lambda item: (item.get("cloud", ""), item.get("name", "")))
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(apis, handle, ensure_ascii=False, indent=2, default=str)

    def all(self) -> List[Dict[str, Any]]:
        return list(self._apis.values())

    def get(self, api_id: str) -> Optional[ApiDoc]:
        api = self._apis.get(api_id)
        return ApiDoc(**api) if api else None

    def upsert_many(self, raw_apis: List[Dict[str, Any]], source_type: str, mode: str = "incremental") -> Dict[str, int]:
        stats = {"created": 0, "updated": 0, "skipped": 0, "total": 0}
        normalized = [normalize_api(item, source_type=source_type) for item in raw_apis]
        with self._lock:
            if mode == "rebuild":
                self._apis = {}
            for api in normalized:
                stats["total"] += 1
                api_id = api["api_id"]
                existing = self._apis.get(api_id)
                api["content_hash"] = make_content_hash(api)
                if existing is None:
                    api["created_at"] = now_utc()
                    api["updated_at"] = now_utc()
                    self._apis[api_id] = api
                    stats["created"] += 1
                elif existing.get("content_hash") != api.get("content_hash"):
                    api["created_at"] = existing.get("created_at") or now_utc()
                    api["updated_at"] = now_utc()
                    self._apis[api_id] = api
                    stats["updated"] += 1
                else:
                    stats["skipped"] += 1
            self.save()
        return stats

    def stats(self) -> IndexStats:
        apis = self.all()
        standard = sum(1 for api in apis if api.get("api_type") == "标准API")
        custom = sum(1 for api in apis if api.get("api_type") == "自定义API")
        partial = sum(1 for api in apis if api.get("partial"))
        last_updated: Optional[datetime] = None
        for api in apis:
            value = api.get("updated_at")
            if isinstance(value, str):
                value = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if isinstance(value, datetime) and (last_updated is None or value > last_updated):
                last_updated = value
        return IndexStats(
            total_apis=len(apis),
            standard_apis=standard,
            custom_apis=custom,
            partial_apis=partial,
            vector_chunks=len(apis) * 2,
            clouds=count_by(apis, "cloud"),
            apps=count_by(apis, "app"),
            last_updated_at=last_updated,
        )
