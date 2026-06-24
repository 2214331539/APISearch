import { Search, SlidersHorizontal, X } from "lucide-react";
import { FormEvent } from "react";
import type { IndexStats, SearchFilters } from "../api/types";

type SearchPanelProps = {
  query: string;
  filters: SearchFilters;
  stats: IndexStats | null;
  loading: boolean;
  onQueryChange: (query: string) => void;
  onFiltersChange: (filters: SearchFilters) => void;
  onSubmit: () => void;
};

export function SearchPanel({
  query,
  filters,
  stats,
  loading,
  onQueryChange,
  onFiltersChange,
  onSubmit,
}: SearchPanelProps) {
  function submit(event: FormEvent) {
    event.preventDefault();
    onSubmit();
  }

  function clearFilters() {
    onFiltersChange({});
  }

  return (
    <form className="search-shell" onSubmit={submit}>
      <div className="search-input-wrap">
        <Search size={21} />
        <input
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="输入业务需求、接口名、编码或 URL"
        />
        <button className="primary-btn" type="submit" disabled={loading || !query.trim()}>
          {loading ? "检索中" : "检索"}
        </button>
      </div>

      <div className="filter-row">
        <span className="filter-label">
          <SlidersHorizontal size={15} />
          过滤
        </span>
        <select
          value={filters.cloud ?? ""}
          onChange={(event) => onFiltersChange({ ...filters, cloud: event.target.value || undefined })}
        >
          <option value="">全部云</option>
          {stats?.clouds.map((item) => (
            <option key={item.name} value={item.name}>
              {item.name} · {item.count}
            </option>
          ))}
        </select>
        <select
          value={filters.api_type ?? ""}
          onChange={(event) => onFiltersChange({ ...filters, api_type: event.target.value || undefined })}
        >
          <option value="">全部类型</option>
          <option value="标准API">标准 API</option>
          <option value="自定义API">自定义 API</option>
          <option value="OpenAPI">OpenAPI</option>
        </select>
        {(filters.cloud || filters.app || filters.api_type) && (
          <button className="ghost-btn" type="button" onClick={clearFilters}>
            <X size={14} />
            清除
          </button>
        )}
      </div>
    </form>
  );
}
