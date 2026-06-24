from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from app.services.identity import make_api_id, make_content_hash, now_utc


def _optional_str(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def normalize_param(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": raw.get("name", "") or raw.get("paramname", "") or raw.get("respparamname", ""),
        "type": raw.get("type", "") or raw.get("paramtype", "") or raw.get("respparamtype", ""),
        "desc": raw.get("desc", "") or raw.get("bodyparamdes", "") or raw.get("respdes", ""),
        "required": bool(raw.get("required", False)),
        "level": int(raw.get("level", 1) or 1),
        "is_list": bool(raw.get("is_list", False)),
        "example": raw.get("example", "") or "",
        "id": _optional_str(raw.get("id") or raw.get("_id")),
        "parent_id": _optional_str(raw.get("parent_id") or raw.get("_pid")),
    }


def build_search_text(api: Dict[str, Any]) -> str:
    lines: List[str] = [
        f"接口名称: {api.get('name', '')}",
        f"接口编码: {api.get('number', '')}",
        f"URL: {api.get('url', '')} 方法: {api.get('http_method', '')}",
        f"所属模块: {api.get('cloud', '')} / {api.get('app', '')}",
    ]
    if api.get("group"):
        lines.append(f"分组: {api.get('group')}")
    if api.get("description"):
        lines.append(f"说明: {api.get('description')}")

    def add_params(title: str, params: List[Dict[str, Any]]) -> None:
        if not params:
            return
        lines.append(title + ":")
        for param in params:
            indent = "  " * max(0, int(param.get("level", 1)) - 1)
            required = "必填" if param.get("required") else "可选"
            suffix = "[]" if param.get("is_list") else ""
            lines.append(
                f"  {indent}- {param.get('name', '')}{suffix} "
                f"({param.get('type', '')}, {required}): {param.get('desc', '')}"
            )

    add_params("请求参数", api.get("request_params", []))
    add_params("返回参数", api.get("response_params", []))
    return "\n".join(lines)


def normalize_api(raw: Dict[str, Any], source_type: str = "dts", namespace: str = "default") -> Dict[str, Any]:
    created_at = raw.get("created_at")
    updated_at = raw.get("updated_at")
    if isinstance(created_at, str):
        created_at_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    else:
        created_at_dt = now_utc()
    if isinstance(updated_at, str):
        updated_at_dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    else:
        updated_at_dt = now_utc()

    api = {
        "file": raw.get("file", ""),
        "api_type": raw.get("api_type", ""),
        "partial": bool(raw.get("partial", False)),
        "name": raw.get("name", "") or "未命名接口",
        "number": raw.get("number", ""),
        "method_name": raw.get("method_name", ""),
        "url": raw.get("url", ""),
        "http_method": raw.get("http_method", "POST") or "POST",
        "app": raw.get("app", ""),
        "cloud": raw.get("cloud", ""),
        "group": raw.get("group", ""),
        "description": raw.get("description", ""),
        "class_name": raw.get("class_name", ""),
        "version": raw.get("version", ""),
        "request_params": [normalize_param(item) for item in raw.get("request_params", [])],
        "response_params": [normalize_param(item) for item in raw.get("response_params", [])],
        "source_type": raw.get("source_type", source_type),
        "created_at": created_at_dt,
        "updated_at": updated_at_dt,
    }
    api["search_text"] = raw.get("search_text") or build_search_text(api)
    api["api_id"] = raw.get("api_id") or make_api_id(api, namespace)
    api["content_hash"] = raw.get("content_hash") or make_content_hash(api)
    return api
