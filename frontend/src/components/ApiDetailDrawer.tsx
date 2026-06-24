import { BookOpen, Clipboard, ExternalLink, X } from "lucide-react";
import { useMemo, useState } from "react";
import type { ApiDoc, ApiParam, SearchDoc } from "../api/types";
import { JsonTemplate } from "./JsonTemplate";
import { ParamTable } from "./ParamTable";

type ApiDetailDrawerProps = {
  api: ApiDoc | null;
  searchDoc?: SearchDoc | null;
  open: boolean;
  onClose: () => void;
};

type Tab = "request" | "response" | "templates" | "raw";

function sampleValue(param: ApiParam): unknown {
  if (param.example) return param.example;
  const type = param.type.toLowerCase();
  if (type.includes("bool")) return false;
  if (type.includes("int") || type.includes("long") || type.includes("decimal") || type.includes("number")) return 0;
  if (type.includes("date") || type.includes("time")) return "2026-01-01";
  return "";
}

function buildTemplate(params: ApiParam[]) {
  const root: Record<string, unknown> = {};
  const stack: Array<{ level: number; value: Record<string, unknown> }> = [{ level: 0, value: root }];

  params.forEach((param) => {
    if (!param.name) return;
    const isContainer = ["entries", "entry", "object", "array"].includes(param.type.toLowerCase()) || param.is_list;
    let value: unknown = isContainer ? {} : sampleValue(param);
    if (param.is_list) value = isContainer ? [{}] : [sampleValue(param)];

    while (stack.length && stack[stack.length - 1].level >= param.level) stack.pop();
    const parent = stack[stack.length - 1]?.value ?? root;
    parent[param.name] = value;
    const objectValue = Array.isArray(value) ? value[0] : value;
    if (objectValue && typeof objectValue === "object" && !Array.isArray(objectValue)) {
      stack.push({ level: param.level, value: objectValue as Record<string, unknown> });
    }
  });
  return root;
}

export function ApiDetailDrawer({ api, searchDoc, open, onClose }: ApiDetailDrawerProps) {
  const [tab, setTab] = useState<Tab>("request");
  const requestTemplate = useMemo(
    () => searchDoc?.request_template ?? (api ? buildTemplate(api.request_params) : {}),
    [api, searchDoc],
  );
  const responseTemplate = useMemo(
    () => searchDoc?.response_template ?? (api ? buildTemplate(api.response_params) : {}),
    [api, searchDoc],
  );

  if (!open || !api) return null;

  async function copyUrl() {
    if (api) await navigator.clipboard.writeText(api.url);
  }

  return (
    <aside className="drawer">
      <div className="drawer-head">
        <div>
          <span className="eyebrow">
            <BookOpen size={14} />
            {api.api_type || "API"}
          </span>
          <h2>{api.name}</h2>
        </div>
        <button className="icon-btn" type="button" onClick={onClose} aria-label="关闭详情">
          <X size={18} />
        </button>
      </div>

      <div className="endpoint-strip">
        <span>{api.http_method}</span>
        <code>{api.url}</code>
        <button className="icon-btn" type="button" onClick={copyUrl} aria-label="复制 URL">
          <Clipboard size={15} />
        </button>
      </div>

      <div className="meta-grid">
        <div>
          <span>编码</span>
          <strong>{api.number || "-"}</strong>
        </div>
        <div>
          <span>云</span>
          <strong>{api.cloud || "-"}</strong>
        </div>
        <div>
          <span>应用</span>
          <strong>{api.app || "-"}</strong>
        </div>
        <div>
          <span>源文件</span>
          <strong>{api.file || "-"}</strong>
        </div>
      </div>

      {api.description && <p className="description-line">{api.description}</p>}

      <div className="tabs">
        <button className={tab === "request" ? "active" : ""} type="button" onClick={() => setTab("request")}>
          请求体
        </button>
        <button className={tab === "response" ? "active" : ""} type="button" onClick={() => setTab("response")}>
          返回体
        </button>
        <button className={tab === "templates" ? "active" : ""} type="button" onClick={() => setTab("templates")}>
          JSON
        </button>
        <button className={tab === "raw" ? "active" : ""} type="button" onClick={() => setTab("raw")}>
          原文
        </button>
      </div>

      <div className="drawer-body">
        {tab === "request" && <ParamTable params={api.request_params} emptyLabel="无请求参数" />}
        {tab === "response" && <ParamTable params={api.response_params} emptyLabel="无返回参数" />}
        {tab === "templates" && (
          <div className="template-grid">
            <JsonTemplate title="请求模板" value={requestTemplate} />
            <JsonTemplate title="返回模板" value={responseTemplate} />
          </div>
        )}
        {tab === "raw" && (
          <pre className="raw-doc">
            {api.search_text}
            {"\n\n"}
            <ExternalLink size={12} /> {api.content_hash}
          </pre>
        )}
      </div>
    </aside>
  );
}
