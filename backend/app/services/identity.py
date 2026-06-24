from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def sha1_text(value: str) -> str:
    return "sha1:" + hashlib.sha1(value.encode("utf-8")).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def make_api_id(api: Dict[str, Any], namespace: str = "default") -> str:
    stable = "|".join(
        [
            namespace,
            str(api.get("url") or ""),
            str(api.get("number") or ""),
            str(api.get("name") or ""),
            str(api.get("file") or ""),
        ]
    )
    return sha1_text(stable)


def make_content_hash(api: Dict[str, Any]) -> str:
    payload = {
        "name": api.get("name", ""),
        "number": api.get("number", ""),
        "url": api.get("url", ""),
        "http_method": api.get("http_method", ""),
        "cloud": api.get("cloud", ""),
        "app": api.get("app", ""),
        "group": api.get("group", ""),
        "description": api.get("description", ""),
        "request_params": api.get("request_params", []),
        "response_params": api.get("response_params", []),
    }
    return sha1_text(canonical_json(payload))


def count_by(items: Iterable[Dict[str, Any]], field: str, limit: int = 12) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for item in items:
        key = str(item.get(field) or "未分类")
        counts[key] = counts.get(key, 0) + 1
    return [
        {"name": key, "count": count}
        for key, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[:limit]
    ]
