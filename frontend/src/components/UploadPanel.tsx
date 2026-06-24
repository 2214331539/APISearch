import { DatabaseZap, FileUp, Loader2, RefreshCw, Upload } from "lucide-react";
import { ChangeEvent, useRef, useState } from "react";
import type { UploadJob } from "../api/types";

type UploadPanelProps = {
  activeJob: UploadJob | null;
  uploading: boolean;
  onUpload: (files: File[], mode: "incremental" | "rebuild") => Promise<void>;
};

export function UploadPanel({ activeJob, uploading, onUpload }: UploadPanelProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [mode, setMode] = useState<"incremental" | "rebuild">("incremental");
  const inputRef = useRef<HTMLInputElement | null>(null);

  function pickFiles(event: ChangeEvent<HTMLInputElement>) {
    setFiles(Array.from(event.target.files ?? []));
  }

  async function submit() {
    if (!files.length) return;
    await onUpload(files, mode);
    setFiles([]);
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <section className="upload-panel">
      <div className="panel-head">
        <h2>索引更新</h2>
        <DatabaseZap size={18} />
      </div>

      <label className="drop-zone">
        <FileUp size={22} />
        <span>{files.length ? `${files.length} 个文件已选择` : ".dts / .json"}</span>
        <input ref={inputRef} type="file" accept=".dts,.json" multiple onChange={pickFiles} />
      </label>

      <div className="segmented">
        <button className={mode === "incremental" ? "active" : ""} type="button" onClick={() => setMode("incremental")}>
          增量
        </button>
        <button className={mode === "rebuild" ? "active" : ""} type="button" onClick={() => setMode("rebuild")}>
          重建
        </button>
      </div>

      <button className="wide-btn" type="button" disabled={!files.length || uploading} onClick={submit}>
        {uploading ? <Loader2 className="spin" size={16} /> : <Upload size={16} />}
        提交入库
      </button>

      {activeJob && (
        <div className="job-box">
          <div className="job-status">
            <span className={`status-dot ${activeJob.status}`} />
            <strong>{activeJob.status}</strong>
            <span>{activeJob.mode}</span>
          </div>
          <div className="job-grid">
            <span>文件 {activeJob.parsed_files}/{activeJob.total_files}</span>
            <span>新增 {activeJob.created_apis}</span>
            <span>更新 {activeJob.updated_apis}</span>
            <span>跳过 {activeJob.skipped_apis}</span>
          </div>
          {activeJob.status !== "completed" && activeJob.status !== "failed" && (
            <div className="job-pulse">
              <RefreshCw size={13} />
              {activeJob.total_apis} APIs
            </div>
          )}
          {activeJob.error_message && <pre className="error-box">{activeJob.error_message}</pre>}
        </div>
      )}
    </section>
  );
}
