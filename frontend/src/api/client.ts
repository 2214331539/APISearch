import type { ApiDoc, ApiListResponse, IndexStats, SearchFilters, SearchResponse, UploadJob } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function getStats(): Promise<IndexStats> {
  return request<IndexStats>("/index/stats");
}

export async function uploadDocs(files: File[], mode: "incremental" | "rebuild"): Promise<UploadJob> {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));
  return request<UploadJob>(`/uploads?mode=${mode}`, {
    method: "POST",
    body: form,
  });
}

export async function getUploadJob(jobId: string): Promise<UploadJob> {
  return request<UploadJob>(`/uploads/${jobId}`);
}

export async function searchApis(query: string, filters: SearchFilters, topK = 6): Promise<SearchResponse> {
  return request<SearchResponse>("/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      top_k: topK,
      filters,
      include_detail: true,
    }),
  });
}

export async function getApiDetail(apiId: string): Promise<ApiDoc> {
  return request<ApiDoc>(`/apis/${apiId}`);
}

export async function listApis(params: {
  cloud?: string;
  app?: string;
  api_type?: string;
  q?: string;
  limit?: number;
  offset?: number;
}): Promise<ApiListResponse> {
  const search = new URLSearchParams();
  if (params.cloud) search.set("cloud", params.cloud);
  if (params.app) search.set("app", params.app);
  if (params.api_type) search.set("api_type", params.api_type);
  if (params.q) search.set("q", params.q);
  search.set("limit", String(params.limit ?? 50));
  search.set("offset", String(params.offset ?? 0));
  return request<ApiListResponse>(`/apis?${search.toString()}`);
}
