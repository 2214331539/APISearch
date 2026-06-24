import { Clipboard, Check } from "lucide-react";
import { useMemo, useState } from "react";

type JsonTemplateProps = {
  title: string;
  value: Record<string, unknown>;
};

export function JsonTemplate({ title, value }: JsonTemplateProps) {
  const [copied, setCopied] = useState(false);
  const text = useMemo(() => JSON.stringify(value, null, 2), [value]);

  async function copy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1100);
  }

  return (
    <section className="json-panel">
      <div className="panel-head compact">
        <h3>{title}</h3>
        <button className="icon-btn" type="button" onClick={copy} aria-label="复制 JSON">
          {copied ? <Check size={16} /> : <Clipboard size={16} />}
        </button>
      </div>
      <pre className="json-block">{text}</pre>
    </section>
  );
}
