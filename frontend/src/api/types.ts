export type ApiParam = {
  name: string;
  type: string;
  desc: string;
  required: boolean;
  level: number;
  is_list: boolean;
  example: string;
  id?: string | null;
  parent_id?: string | null;
};

export type ApiDoc = {
  api_id: string;
  file: string;
  api_type: string;
  partial: boolean;
  name: string;
  number: string;
  method_name: string;
  url: string;
  http_method: string;
  app: string;
  cloud: string;
  group: string;
  description: string;
  class_name: string;
  version: string;
  request_params: ApiParam[];
  response_params: ApiParam[];
  search_text: string;
  content_hash: string;
  source_type: string;
  created_at: string;
  updated_at: string;
};

export type UploadJob = {
  job_id: string;
  status: "queued" | "parsing" | "indexing" | "completed" | "failed";
  mode: "incremental" | "rebuild";
  total_files: number;
  parsed_files: number;
  total_apis: number;
  created_apis: number;
  updated_apis: number;
  skipped_apis: number;
  failed_files: number;
  error_message?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
};

export type IndexStats = {
  total_apis: number;
  standard_apis: number;
  custom_apis: number;
  partial_apis: number;
  vector_chunks: number;
  clouds: Array<{ name: string; count: number }>;
  apps: Array<{ name: string; count: number }>;
  last_updated_at?: string | null;
};

export type SearchFilters = {
  cloud?: string;
  app?: string;
  api_type?: string;
};

export type SearchCandidate = {
  api_id: string;
  name: string;
  number: string;
  url: string;
  http_method: string;
  cloud: string;
  app: string;
  api_type: string;
  score: number;
  reason: string;
};

export type SearchDoc = {
  api_id: string;
  name: string;
  number: string;
  url: string;
  http_method: string;
  description: string;
  cloud: string;
  app: string;
  api_type: string;
  request_params: ApiParam[];
  response_params: ApiParam[];
  request_template: Record<string, unknown>;
  response_template: Record<string, unknown>;
};

export type SearchResponse = {
  answer_type: "single" | "multiple" | "not_found";
  summary: string;
  selected_api_id?: string | null;
  candidates: SearchCandidate[];
  doc?: SearchDoc | null;
  trace: {
    normalized_query: string;
    retrieval_methods: string[];
    warnings: string[];
  };
};
