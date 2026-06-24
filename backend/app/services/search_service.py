from __future__ import annotations

import math
import re
from typing import Any, Dict, Iterable, List, Set, Tuple

from app.models.schemas import SearchCandidate, SearchRequest, SearchResponse, SearchTrace
from app.services.api_store import ApiStore
from app.services.doc_render_service import to_search_doc


ACTION_SYNONYMS = {
    "查询": ["query", "getlist", "batchquery", "queryby", "info", "list"],
    "列表": ["getlist", "list"],
    "详情": ["query", "queryby", "info"],
    "新增": ["add", "batchadd", "save"],
    "保存": ["save", "add", "update"],
    "修改": ["update", "batchupdate"],
    "更新": ["update", "batchupdate"],
    "删除": ["delete", "batchdelete"],
    "提交": ["submit", "batchsubmit"],
    "撤销": ["unsubmit", "batchunsubmit"],
    "审核": ["audit", "batchaudit"],
    "反审核": ["unaudit", "batchunaudit", "unaudit"],
    "禁用": ["disable", "batchdisable"],
    "启用": ["enable", "batchenable"],
    "批量": ["batch"],
}


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()


def char_ngrams(value: str, size: int = 2) -> Set[str]:
    compact = re.sub(r"\s+", "", normalize_text(value))
    if len(compact) <= size:
        return {compact} if compact else set()
    return {compact[index : index + size] for index in range(len(compact) - size + 1)}


def query_terms(query: str) -> Set[str]:
    lowered = normalize_text(query)
    terms = set(re.findall(r"[a-zA-Z0-9_./-]+|[\u4e00-\u9fff]{2,}", lowered))
    for token in list(terms):
        if re.fullmatch(r"[\u4e00-\u9fff]+", token) and len(token) > 2:
            terms.update(token[index : index + 2] for index in range(len(token) - 1))
    for phrase, synonyms in ACTION_SYNONYMS.items():
        if phrase in query:
            terms.add(phrase)
            terms.update(synonyms)
    return {term for term in terms if term}


def token_score(terms: Iterable[str], text: str) -> float:
    normalized = normalize_text(text)
    if not normalized:
        return 0.0
    score = 0.0
    for term in terms:
        if not term:
            continue
        if term in normalized:
            score += 1.0 + min(len(term), 8) / 10.0
    return score


def cosine_ngram_score(query: str, text: str) -> float:
    q = char_ngrams(query)
    t = char_ngrams(text[:4000])
    if not q or not t:
        return 0.0
    overlap = len(q & t)
    return overlap / math.sqrt(len(q) * len(t))


class SearchService:
    def __init__(self, api_store: ApiStore) -> None:
        self.api_store = api_store

    def search(self, request: SearchRequest) -> SearchResponse:
        query = request.query.strip()
        if not query:
            return SearchResponse(
                answer_type="not_found",
                summary="请输入要查找的 API 需求。",
                candidates=[],
                trace=SearchTrace(normalized_query="", retrieval_methods=[]),
            )

        filters = request.filters
        terms = query_terms(query)
        scored: List[Tuple[float, Dict[str, Any], str]] = []
        for api in self.api_store.all():
            if filters.cloud and api.get("cloud") != filters.cloud:
                continue
            if filters.app and api.get("app") != filters.app:
                continue
            if filters.api_type and api.get("api_type") != filters.api_type:
                continue

            primary = " ".join(
                [
                    api.get("name", ""),
                    api.get("number", ""),
                    api.get("url", ""),
                    api.get("cloud", ""),
                    api.get("app", ""),
                    api.get("description", ""),
                ]
            )
            full = primary + "\n" + api.get("search_text", "")
            exact = self._exact_score(query, api)
            keyword = min(token_score(terms, primary) * 0.08 + token_score(terms, full) * 0.015, 1.0)
            semantic = cosine_ngram_score(query, full)
            field = self._field_score(query, api)
            score = min(1.0, 0.38 * exact + 0.28 * keyword + 0.24 * semantic + 0.10 * field)
            if score > 0.045:
                scored.append((score, api, self._reason(query, terms, api, exact, keyword, semantic)))

        scored.sort(key=lambda item: item[0], reverse=True)
        top = scored[: max(1, min(request.top_k, 20))]
        candidates = [
            SearchCandidate(
                api_id=api["api_id"],
                name=api.get("name", ""),
                number=api.get("number", ""),
                url=api.get("url", ""),
                http_method=api.get("http_method", "POST"),
                cloud=api.get("cloud", ""),
                app=api.get("app", ""),
                api_type=api.get("api_type", ""),
                score=round(score, 4),
                reason=reason,
            )
            for score, api, reason in top
        ]

        warnings: List[str] = []
        if not candidates:
            return SearchResponse(
                answer_type="not_found",
                summary="没有找到足够匹配的 API。可以换一个业务对象、动作词，或先上传对应文档。",
                candidates=[],
                trace=SearchTrace(
                    normalized_query=normalize_text(query),
                    retrieval_methods=["exact", "keyword", "local-semantic"],
                    warnings=warnings,
                ),
            )

        answer_type = "single"
        if len(candidates) > 1 and candidates[0].score - candidates[1].score < 0.08:
            answer_type = "multiple"
            warnings.append("Top candidates are close; user confirmation is recommended.")

        selected_api = self.api_store.get(candidates[0].api_id)
        doc = to_search_doc(selected_api) if selected_api and request.include_detail else None
        summary = (
            f"最匹配的是「{candidates[0].name}」，接口编码 {candidates[0].number or '未提供'}。"
            if answer_type == "single"
            else "找到多个相近接口，建议先确认业务对象和操作类型。"
        )
        return SearchResponse(
            answer_type=answer_type,
            summary=summary,
            selected_api_id=candidates[0].api_id,
            candidates=candidates,
            doc=doc,
            trace=SearchTrace(
                normalized_query=normalize_text(query),
                retrieval_methods=["exact", "keyword", "local-semantic"],
                warnings=warnings,
            ),
        )

    def _exact_score(self, query: str, api: Dict[str, Any]) -> float:
        q = normalize_text(query)
        if not q:
            return 0.0
        values = {
            "url": normalize_text(api.get("url", "")),
            "number": normalize_text(api.get("number", "")),
            "name": normalize_text(api.get("name", "")),
            "description": normalize_text(api.get("description", "")),
        }
        if values["url"] and values["url"] in q:
            return 1.0
        if values["number"] and values["number"] in q:
            return 0.95
        if values["name"] and values["name"] in q:
            return 0.9
        if any(token and token in values["name"] for token in re.findall(r"[\u4e00-\u9fff]{2,}|[a-z0-9_]+", q)):
            return 0.45
        return 0.0

    def _field_score(self, query: str, api: Dict[str, Any]) -> float:
        score = 0.0
        name_number = normalize_text(api.get("name", "") + " " + api.get("number", ""))
        if "批量" in query and "batch" in name_number:
            score += 0.35
        for phrase, synonyms in ACTION_SYNONYMS.items():
            if phrase in query and any(synonym in name_number for synonym in synonyms):
                score += 0.2
        if api.get("cloud") and api.get("cloud") in query:
            score += 0.2
        if api.get("app") and api.get("app") in query:
            score += 0.2
        return min(score, 1.0)

    def _reason(
        self,
        query: str,
        terms: Iterable[str],
        api: Dict[str, Any],
        exact: float,
        keyword: float,
        semantic: float,
    ) -> str:
        reasons = []
        haystack = normalize_text(" ".join([api.get("name", ""), api.get("number", ""), api.get("description", "")]))
        matched = [term for term in terms if term in haystack][:3]
        if exact >= 0.9:
            reasons.append("精确命中接口名称、编码或 URL")
        if matched:
            reasons.append("关键词命中：" + "、".join(matched))
        if "批量" in query and "batch" in normalize_text(api.get("number", "") + api.get("name", "")):
            reasons.append("匹配批量操作")
        if semantic > 0.08:
            reasons.append("参数和说明语义相近")
        return "；".join(reasons) or "综合文本相似度较高"
