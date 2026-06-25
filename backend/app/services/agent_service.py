from __future__ import annotations

import logging
import threading
from typing import Dict, List, Optional, TypedDict

from app.services.llm_client import GeminiClient

logger = logging.getLogger(__name__)


REWRITE_SCHEMA = {
    "type": "object",
    "properties": {
        "normalized_query": {"type": "string"},
        "keywords": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["normalized_query", "keywords"],
}

PROMPT_TEMPLATE = (
    "你在帮助用户检索金蝶云苍穹/星瀚 ERP 系统的 API 文档。\n"
    "用户的自然语言查询可能口语化、含糊或用了同义说法。请把它改写成更利于检索的形式，"
    "并扩展出相关的检索关键词。\n"
    "要求：\n"
    "- normalized_query：一句规范的中文检索意图。\n"
    "- keywords：业务对象、业务术语的中文同义词，以及可能出现在接口编码/URL 里的英文动作词"
    "（如 query、getList、add、save、update、audit、batch、submit 等）。最多 12 个，去重。\n"
    "- 不要编造与查询无关的业务对象。\n\n"
    "用户查询：{query}"
)


class RewriteResult(TypedDict):
    normalized_query: str
    keywords: List[str]


class QueryRewriter:
    """LLM-backed query rewrite/expansion with caching and graceful fallback."""

    def __init__(self, client: GeminiClient) -> None:
        self.client = client
        self._cache: Dict[str, Optional[RewriteResult]] = {}
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self.client.configured

    def rewrite(self, query: str) -> Optional[RewriteResult]:
        """Return rewrite result, or ``None`` if disabled/unavailable.

        Failures never raise — the caller falls back to rule-based retrieval.
        """
        key = query.strip()
        if not key or not self.enabled:
            return None
        with self._lock:
            if key in self._cache:
                return self._cache[key]

        result: Optional[RewriteResult] = None
        try:
            raw = self.client.generate_json(PROMPT_TEMPLATE.format(query=key), REWRITE_SCHEMA)
            keywords = [str(item).strip() for item in raw.get("keywords", []) if str(item).strip()]
            result = {
                "normalized_query": str(raw.get("normalized_query", "")).strip(),
                "keywords": keywords[:12],
            }
        except Exception as exc:  # network / parsing / proxy errors are non-fatal
            logger.warning("Query rewrite failed, falling back to rules: %s", exc)
            result = None

        with self._lock:
            self._cache[key] = result
        return result
