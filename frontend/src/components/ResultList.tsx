import { ArrowRight, Gauge, Link2 } from "lucide-react";
import type { SearchCandidate } from "../api/types";

type ResultListProps = {
  candidates: SearchCandidate[];
  selectedId?: string | null;
  onSelect: (apiId: string) => void;
};

export function ResultList({ candidates, selectedId, onSelect }: ResultListProps) {
  if (!candidates.length) {
    return <div className="empty-state">未返回候选接口</div>;
  }

  return (
    <div className="result-list">
      {candidates.map((candidate, index) => (
        <button
          className={`result-row ${selectedId === candidate.api_id ? "active" : ""}`}
          key={candidate.api_id}
          type="button"
          onClick={() => onSelect(candidate.api_id)}
        >
          <span className="rank">{String(index + 1).padStart(2, "0")}</span>
          <span className="result-main">
            <span className="result-title">{candidate.name}</span>
            <span className="result-url">
              <Link2 size={13} />
              {candidate.url}
            </span>
            <span className="result-reason">{candidate.reason}</span>
          </span>
          <span className="result-meta">
            <span className="score">
              <Gauge size={14} />
              {Math.round(candidate.score * 100)}
            </span>
            <span className="tag">{candidate.api_type || "API"}</span>
            <ArrowRight size={16} />
          </span>
        </button>
      ))}
    </div>
  );
}
