import { AlertTriangle, FileText, Info, Link2, MousePointer2 } from "lucide-react";

import type { SelectedGraphItem } from "../types";

interface InspectorProps {
  selection: SelectedGraphItem | null;
}

function textValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "未提供";
  }
  if (Array.isArray(value)) {
    return value.length ? value.join(", ") : "无";
  }
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(2);
  }
  if (typeof value === "object") {
    return JSON.stringify(value, null, 2);
  }
  return String(value);
}

function DetailRow({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="detail-row">
      <span>{label}</span>
      <strong>{textValue(value)}</strong>
    </div>
  );
}

export function Inspector({ selection }: InspectorProps) {
  if (!selection) {
    return (
      <aside className="inspector empty">
        <MousePointer2 size={24} />
        <h3>选择图谱元素</h3>
        <p>点击节点或边，查看证据、路径、状态和 review 原因。</p>
      </aside>
    );
  }

  const data = selection.data;
  const isNode = selection.type === "node";
  const title = isNode ? data.name ?? data.label : data.relationType ?? data.label;
  const reviewReasons = Array.isArray(data.reviewReasons) ? data.reviewReasons : [];

  return (
    <aside className="inspector">
      <div className="inspector-header">
        <div className="inspector-icon">{isNode ? <Info size={18} /> : <Link2 size={18} />}</div>
        <div>
          <p>{isNode ? "节点" : "关系"}</p>
          <h3>{textValue(title)}</h3>
        </div>
      </div>

      {data.review ? (
        <div className="review-alert">
          <AlertTriangle size={16} />
          <span>需要人工复核</span>
        </div>
      ) : null}

      <section className="detail-section">
        <h4>概览</h4>
        {isNode ? (
          <>
            <DetailRow label="Entity Type" value={data.entityType} />
            <DetailRow label="Kind" value={data.kind} />
            <DetailRow label="Modality" value={data.modality} />
          </>
        ) : (
          <>
            <DetailRow label="Relation Type" value={data.relationType} />
            <DetailRow label="Source" value={data.edgeSource} />
            <DetailRow label="Confidence" value={data.confidence} />
          </>
        )}
        <DetailRow label="Ontology" value={data.ontologyStatus} />
        <DetailRow label="Evidence" value={data.evidenceStatus} />
      </section>

      <section className="detail-section">
        <h4>证据</h4>
        <p className="evidence">{textValue(data.evidenceSpan)}</p>
      </section>

      <section className="detail-section">
        <h4>路径</h4>
        <DetailRow label="Tree Path" value={data.treePath} />
        <DetailRow label="Source Path" value={data.sourcePath} />
      </section>

      {reviewReasons.length ? (
        <section className="detail-section">
          <h4>Review Reasons</h4>
          <div className="reason-list">
            {reviewReasons.map((reason) => (
              <span key={String(reason)}>{String(reason)}</span>
            ))}
          </div>
        </section>
      ) : null}

      <section className="detail-section raw-id">
        <h4>
          <FileText size={14} />
          ID
        </h4>
        <code>{textValue(data.id)}</code>
      </section>
    </aside>
  );
}
