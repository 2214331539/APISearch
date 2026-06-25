import { ArrowRight, Boxes, Layers, Link2 } from "lucide-react";
import { useEffect, useState } from "react";
import { listApis } from "../api/client";
import type { ApiSummary } from "../api/types";

type BrowsePanelProps = {
  cloud: string | null;
  clouds: Array<{ name: string; count: number }>;
  onCloudChange: (cloud: string) => void;
  onOpenApi: (apiId: string) => void;
};

const PAGE = 50;

export function BrowsePanel({ cloud, clouds, onCloudChange, onOpenApi }: BrowsePanelProps) {
  const [apiType, setApiType] = useState("");
  const [q, setQ] = useState("");
  const [items, setItems] = useState<ApiSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listApis({ cloud: cloud ?? undefined, api_type: apiType || undefined, q: q || undefined, limit: PAGE, offset: 0 })
      .then((res) => {
        if (!cancelled) {
          setItems(res.items);
          setTotal(res.total);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "加载失败");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [cloud, apiType, q]);

  async function loadMore() {
    setLoading(true);
    try {
      const res = await listApis({
        cloud: cloud ?? undefined,
        api_type: apiType || undefined,
        q: q || undefined,
        limit: PAGE,
        offset: items.length,
      });
      setItems((prev) => [...prev, ...res.items]);
      setTotal(res.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="browse-panel">
      <div className="browse-clouds">
        {clouds.map((item) => (
          <button
            type="button"
            key={item.name}
            className={cloud === item.name ? "active" : ""}
            onClick={() => onCloudChange(item.name)}
          >
            <Boxes size={13} />
            {item.name}
            <strong>{item.count}</strong>
          </button>
        ))}
      </div>

      <div className="browse-toolbar">
        <div className="browse-title">
          <Layers size={16} />
          <h2>{cloud ?? "全部云"}</h2>
          <span className="browse-count">{total} 个接口</span>
        </div>
        <div className="browse-controls">
          <input
            className="browse-search"
            value={q}
            placeholder="按名称 / 编码 / URL 过滤"
            onChange={(event) => setQ(event.target.value)}
          />
          <select value={apiType} onChange={(event) => setApiType(event.target.value)}>
            <option value="">全部类型</option>
            <option value="标准API">标准 API</option>
            <option value="自定义API">自定义 API</option>
          </select>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {items.length === 0 && !loading ? (
        <div className="empty-canvas">
          <Layers size={34} />
          <span>该范围下暂无接口</span>
        </div>
      ) : (
        <div className="browse-list">
          {items.map((api, index) => {
            const showAppHead = index === 0 || api.app !== items[index - 1].app;
            return (
              <div key={api.api_id} className="browse-item">
                {showAppHead && <div className="browse-app-head">{api.app || "未分类应用"}</div>}
                <button className="browse-row" type="button" onClick={() => onOpenApi(api.api_id)}>
                  <span className="method">{api.http_method}</span>
                  <span className="browse-row-main">
                    <span className="browse-row-title">{api.name}</span>
                    <span className="browse-row-url">
                      <Link2 size={12} />
                      {api.url}
                    </span>
                  </span>
                  <span className="browse-row-meta">
                    {api.number && <code>{api.number}</code>}
                    <span className="tag">{api.api_type || "API"}</span>
                    <ArrowRight size={15} />
                  </span>
                </button>
              </div>
            );
          })}
        </div>
      )}

      {items.length < total && (
        <button className="ghost-btn load-more" type="button" disabled={loading} onClick={loadMore}>
          {loading ? "加载中…" : `加载更多（剩余 ${total - items.length}）`}
        </button>
      )}
    </section>
  );
}
