from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ApiParam(BaseModel):
    name: str = ""
    type: str = ""
    desc: str = ""
    required: bool = False
    level: int = 1
    is_list: bool = False
    example: str = ""
    id: Optional[str] = None
    parent_id: Optional[str] = None


class ApiDoc(BaseModel):
    api_id: str
    file: str = ""
    api_type: str = ""
    partial: bool = False
    name: str
    number: str = ""
    method_name: str = ""
    url: str
    http_method: str = "POST"
    app: str = ""
    cloud: str = ""
    group: str = ""
    description: str = ""
    class_name: str = ""
    version: str = ""
    request_params: List[ApiParam] = Field(default_factory=list)
    response_params: List[ApiParam] = Field(default_factory=list)
    search_text: str = ""
    content_hash: str
    source_type: str = "dts"
    created_at: datetime
    updated_at: datetime


class UploadJob(BaseModel):
    job_id: str
    status: Literal["queued", "parsing", "indexing", "completed", "failed"]
    mode: Literal["incremental", "rebuild"] = "incremental"
    total_files: int
    parsed_files: int = 0
    total_apis: int = 0
    created_apis: int = 0
    updated_apis: int = 0
    skipped_apis: int = 0
    failed_files: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class UploadResponse(BaseModel):
    job_id: str
    status: str
    total_files: int


class SearchFilters(BaseModel):
    cloud: Optional[str] = None
    app: Optional[str] = None
    api_type: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    filters: SearchFilters = Field(default_factory=SearchFilters)
    include_detail: bool = True


class SearchCandidate(BaseModel):
    api_id: str
    name: str
    number: str = ""
    url: str
    http_method: str = "POST"
    cloud: str = ""
    app: str = ""
    api_type: str = ""
    score: float
    reason: str


class SearchTrace(BaseModel):
    normalized_query: str
    retrieval_methods: List[str]
    rewritten_query: Optional[str] = None
    expanded_terms: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class SearchDoc(BaseModel):
    api_id: str
    name: str
    number: str = ""
    url: str
    http_method: str = "POST"
    description: str = ""
    cloud: str = ""
    app: str = ""
    api_type: str = ""
    request_params: List[ApiParam] = Field(default_factory=list)
    response_params: List[ApiParam] = Field(default_factory=list)
    request_template: Dict[str, Any] = Field(default_factory=dict)
    response_template: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    answer_type: Literal["single", "multiple", "not_found"]
    summary: str
    selected_api_id: Optional[str] = None
    candidates: List[SearchCandidate] = Field(default_factory=list)
    doc: Optional[SearchDoc] = None
    trace: SearchTrace


class IndexStats(BaseModel):
    total_apis: int
    standard_apis: int
    custom_apis: int
    partial_apis: int
    vector_chunks: int
    clouds: List[Dict[str, Any]]
    apps: List[Dict[str, Any]]
    last_updated_at: Optional[datetime] = None
