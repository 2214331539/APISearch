from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


class JsonParserAdapter:
    supported_extensions = {".json"}

    def parse_file(self, path: Path) -> List[Dict]:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, list):
            return [dict(item, source_type=item.get("source_type", "json")) for item in payload]
        if isinstance(payload, dict) and "paths" in payload:
            return self._parse_openapi(payload, path.name)
        if isinstance(payload, dict) and "url" in payload:
            return [dict(payload, source_type=payload.get("source_type", "json"))]
        raise ValueError("Unsupported JSON API document format")

    def _parse_openapi(self, payload: Dict[str, Any], filename: str) -> List[Dict]:
        docs: List[Dict] = []
        title = payload.get("info", {}).get("title", "")
        version = payload.get("info", {}).get("version", "")
        for url, path_item in payload.get("paths", {}).items():
            if not isinstance(path_item, dict):
                continue
            for method, operation in path_item.items():
                if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                    continue
                operation = operation or {}
                request_params = []
                response_params = []
                for param in operation.get("parameters", []) or []:
                    request_params.append(
                        {
                            "name": param.get("name", ""),
                            "type": param.get("schema", {}).get("type", ""),
                            "desc": param.get("description", ""),
                            "required": bool(param.get("required", False)),
                            "level": 1,
                            "is_list": False,
                            "example": "",
                        }
                    )
                docs.append(
                    {
                        "file": filename,
                        "api_type": "OpenAPI",
                        "partial": False,
                        "name": operation.get("summary") or operation.get("operationId") or url,
                        "number": operation.get("operationId", ""),
                        "method_name": operation.get("operationId", ""),
                        "url": url,
                        "http_method": method.upper(),
                        "app": title,
                        "cloud": "OpenAPI",
                        "group": ",".join(operation.get("tags", []) or []),
                        "description": operation.get("description", ""),
                        "class_name": "",
                        "version": version,
                        "request_params": request_params,
                        "response_params": response_params,
                        "source_type": "openapi",
                    }
                )
        return docs
