import { AlertTriangle, Boxes, Clock3, Compass, Database, FileJson2, Layers3, RefreshCw, Search, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { getApiDetail, getStats, getUploadJob, searchApis, uploadDocs } from "./api/client";
import type { ApiDoc, IndexStats, SearchDoc, SearchFilters, SearchResponse, UploadJob } from "./api/types";
import { ApiDetailDrawer } from "./components/ApiDetailDrawer";
import { BrowsePanel } from "./components/BrowsePanel";
import { JsonTemplate } from "./components/JsonTemplate";
import { ParamTable } from "./components/ParamTable";
import { ResultList } from "./components/ResultList";
import { SearchPanel } from "./components/SearchPanel";
import { UploadPanel } from "./components/UploadPanel";

type Mode = "search" | "browse";

function formatDate(value?: string | null) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function App() {
  const [stats, setStats] = useState<IndexStats | null>(null);
  const [query, setQuery] = useState("即时库存查询接口");
  const [filters, setFilters] = useState<SearchFilters>({});
  const [searchResult, setSearchResult] = useState<SearchResponse | null>(null);
  const [selectedApi, setSelectedApi] = useState<ApiDoc | null>(null);
  const [selectedSearchDoc, setSelectedSearchDoc] = useState<SearchDoc | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [mode, setMode] = useState<Mode>("search");
  const [browseCloud, setBrowseCloud] = useState<string | null>(null);
  const [activeJob, setActiveJob] = useState<UploadJob | null>(null);
  const [loadingSearch, setLoadingSearch] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refreshStats() {
    setStats(await getStats());
  }

  useEffect(() => {
    refreshStats().catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!activeJob || activeJob.status === "completed" || activeJob.status === "failed") return;
    const handle = window.setInterval(async () => {
      const job = await getUploadJob(activeJob.job_id);
      setActiveJob(job);
      if (job.status === "completed") refreshStats().catch((err) => setError(err.message));
    }, 1200);
    return () => window.clearInterval(handle);
  }, [activeJob]);

  async function runSearch() {
    setLoadingSearch(true);
    setError(null);
    try {
      const result = await searchApis(query, filters, 6);
      setSearchResult(result);
      setSelectedSearchDoc(result.doc ?? null);
      if (result.selected_api_id) {
        const detail = await getApiDetail(result.selected_api_id);
        setSelectedApi(detail);
      } else {
        setSelectedApi(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoadingSearch(false);
    }
  }

  async function handleCandidateSelect(apiId: string) {
    const detail = await getApiDetail(apiId);
    setSelectedApi(detail);
    setSelectedSearchDoc(searchResult?.doc?.api_id === apiId ? searchResult.doc : null);
    setDrawerOpen(true);
  }

  async function openApiDetail(apiId: string) {
    try {
      const detail = await getApiDetail(apiId);
      setSelectedApi(detail);
      setSelectedSearchDoc(null);
      setDrawerOpen(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载详情失败");
    }
  }

  function browseByCloud(cloud: string) {
    setBrowseCloud(cloud);
    setMode("browse");
  }

  async function handleUpload(files: File[], mode: "incremental" | "rebuild") {
    setUploading(true);
    setError(null);
    try {
      const job = await uploadDocs(files, mode);
      setActiveJob(job);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  const selectedCandidate = useMemo(
    () => searchResult?.candidates.find((candidate) => candidate.api_id === selectedApi?.api_id),
    [searchResult, selectedApi],
  );

  return (
    <div className="app-shell">
      <aside className="left-rail">
        <div className="brand-lockup">
          <div className="brand-mark">
            <Layers3 size={19} />
          </div>
          <div>
            <h1>API Search Agent</h1>
            <span>文档索引与接口检索</span>
          </div>
        </div>

        <section className="stat-panel">
          <div className="stat-tile total">
            <Database size={18} />
            <span>总接口</span>
            <strong>{stats?.total_apis ?? "-"}</strong>
          </div>
          <div className="stat-split">
            <div>
              <span>标准</span>
              <strong>{stats?.standard_apis ?? "-"}</strong>
            </div>
            <div>
              <span>自定义</span>
              <strong>{stats?.custom_apis ?? "-"}</strong>
            </div>
          </div>
          <div className="mini-meter">
            <span>partial</span>
            <strong>{stats?.partial_apis ?? "-"}</strong>
            <FileJson2 size={15} />
          </div>
        </section>

        <UploadPanel activeJob={activeJob} uploading={uploading} onUpload={handleUpload} />

        <section className="cloud-panel">
          <div className="panel-head">
            <h2>云分布</h2>
            <Boxes size={17} />
          </div>
          <p className="panel-hint">点击任一云，浏览其下全部接口</p>
          <div className="cloud-list">
            {stats?.clouds.slice(0, 10).map((item) => (
              <button
                type="button"
                key={item.name}
                className={mode === "browse" && browseCloud === item.name ? "active" : ""}
                onClick={() => browseByCloud(item.name)}
              >
                <span>{item.name}</span>
                <strong>{item.count}</strong>
              </button>
            ))}
          </div>
        </section>
      </aside>

      <main className="workspace">
        <section className="main-stage">
          <header className="topbar">
            <div>
              <span className="eyebrow">
                <Sparkles size={14} />
                API 文档助手
              </span>
              <h2>{mode === "search" ? "用自然语言查找接口文档" : "按云浏览全部接口文档"}</h2>
            </div>
            <div className="topbar-actions">
              <div className="mode-toggle">
                <button
                  type="button"
                  className={mode === "search" ? "active" : ""}
                  onClick={() => setMode("search")}
                >
                  <Search size={14} />
                  检索
                </button>
                <button
                  type="button"
                  className={mode === "browse" ? "active" : ""}
                  onClick={() => setMode("browse")}
                >
                  <Compass size={14} />
                  浏览
                </button>
              </div>
              <span className="time-chip">
                <Clock3 size={14} />
                {formatDate(stats?.last_updated_at)}
              </span>
              <button className="ghost-btn" type="button" onClick={() => refreshStats().catch((err) => setError(err.message))}>
                <RefreshCw size={14} />
                刷新
              </button>
            </div>
          </header>

          {error && (
            <div className="error-banner">
              <AlertTriangle size={16} />
              {error}
            </div>
          )}

          {mode === "browse" ? (
            <BrowsePanel
              cloud={browseCloud}
              clouds={stats?.clouds ?? []}
              onCloudChange={setBrowseCloud}
              onOpenApi={openApiDetail}
            />
          ) : (
            <>
          <SearchPanel
            query={query}
            filters={filters}
            stats={stats}
            loading={loadingSearch}
            onQueryChange={setQuery}
            onFiltersChange={setFilters}
            onSubmit={runSearch}
          />

          <section className="result-layout">
            <div className="candidate-pane">
              <div className="panel-head">
                <h2>候选接口</h2>
                <span className={`answer-pill ${searchResult?.answer_type ?? "idle"}`}>
                  {searchResult?.answer_type ?? "idle"}
                </span>
              </div>
              <ResultList
                candidates={searchResult?.candidates ?? []}
                selectedId={selectedApi?.api_id}
                onSelect={handleCandidateSelect}
              />
            </div>

            <div className="doc-pane">
              {selectedApi ? (
                <>
                  <div className="doc-hero">
                    <div>
                      <span className="eyebrow">{selectedApi.cloud || "未分类"} / {selectedApi.app || "未分类"}</span>
                      <h2>{selectedApi.name}</h2>
                      <p>{searchResult?.summary ?? selectedApi.description}</p>
                    </div>
                    <button className="primary-btn" type="button" onClick={() => setDrawerOpen(true)}>
                      查看详情
                    </button>
                  </div>

                  <div className="endpoint-strip in-flow">
                    <span>{selectedApi.http_method}</span>
                    <code>{selectedApi.url}</code>
                  </div>

                  {selectedCandidate && <div className="match-line">{selectedCandidate.reason}</div>}

                  <div className="doc-grid">
                    <div>
                      <div className="panel-head compact">
                        <h3>请求参数</h3>
                        <span>{selectedApi.request_params.length}</span>
                      </div>
                      <ParamTable params={selectedApi.request_params.slice(0, 16)} emptyLabel="无请求参数" />
                    </div>
                    <div>
                      <div className="panel-head compact">
                        <h3>返回参数</h3>
                        <span>{selectedApi.response_params.length}</span>
                      </div>
                      <ParamTable params={selectedApi.response_params.slice(0, 16)} emptyLabel="无返回参数" />
                    </div>
                  </div>

                  {selectedSearchDoc && (
                    <div className="template-grid in-main">
                      <JsonTemplate title="请求模板" value={selectedSearchDoc.request_template} />
                      <JsonTemplate title="返回模板" value={selectedSearchDoc.response_template} />
                    </div>
                  )}
                </>
              ) : (
                <div className="empty-canvas">
                  <Database size={38} />
                  <span>等待检索</span>
                </div>
              )}
            </div>
          </section>
            </>
          )}
        </section>
      </main>

      <ApiDetailDrawer
        api={selectedApi}
        searchDoc={selectedSearchDoc}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />
    </div>
  );
}

export default App;
