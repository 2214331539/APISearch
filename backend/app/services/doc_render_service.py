from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.models.schemas import ApiDoc, ApiParam, SearchDoc


def _sample_value(param: ApiParam) -> Any:
    if param.example:
        return param.example
    param_type = (param.type or "").lower()
    if any(key in param_type for key in ["long", "int", "integer"]):
        return 0
    if any(key in param_type for key in ["decimal", "double", "float", "number"]):
        return 0
    if "bool" in param_type:
        return False
    if "date" in param_type or "time" in param_type:
        return "2026-01-01"
    return ""


def build_template(params: List[ApiParam], required_only: bool = False) -> Dict[str, Any]:
    if not params:
        return {}

    root: Dict[str, Any] = {}
    node_values: Dict[str, Any] = {}
    stack: List[tuple[int, str, Dict[str, Any]]] = [(0, "__root__", root)]

    for index, param in enumerate(params):
        if not param.name:
            continue
        if required_only and not param.required:
            child_required = any(child.level > param.level and child.required for child in params[index + 1 :])
            if not child_required:
                continue

        is_container = (param.type or "").lower() in {"entries", "entry", "object", "array"} or param.is_list
        value: Any = {} if is_container else _sample_value(param)
        if param.is_list:
            value = [{}] if is_container else [_sample_value(param)]

        while stack and stack[-1][0] >= param.level:
            stack.pop()
        parent = stack[-1][2] if stack else root
        if isinstance(parent, list):
            parent = parent[0]
        parent[param.name] = value

        object_value: Optional[Dict[str, Any]] = None
        if isinstance(value, dict):
            object_value = value
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            object_value = value[0]
        if object_value is not None:
            stack.append((param.level, param.name, object_value))
            if param.id:
                node_values[param.id] = object_value

    return root


def to_search_doc(api: ApiDoc) -> SearchDoc:
    return SearchDoc(
        api_id=api.api_id,
        name=api.name,
        number=api.number,
        url=api.url,
        http_method=api.http_method,
        description=api.description,
        cloud=api.cloud,
        app=api.app,
        api_type=api.api_type,
        request_params=api.request_params,
        response_params=api.response_params,
        request_template=build_template(api.request_params),
        response_template=build_template(api.response_params),
    )
