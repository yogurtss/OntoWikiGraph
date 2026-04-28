import { AlertTriangle, Database, FileText, Filter, Search } from "lucide-react";

import { entityTypesForGraph, relationTypesForGraph } from "../lib/graphUtils";
import type { GraphFilters, KGGraph } from "../types";

interface SidebarProps {
  graphs: KGGraph[];
  activeGraph: KGGraph;
  filters: GraphFilters;
  source: "export" | "mock";
  sourceMessage?: string;
  onGraphChange: (documentId: string) => void;
  onFiltersChange: (filters: GraphFilters) => void;
}

function toggleSetValue(values: Set<string>, value: string): Set<string> {
  const next = new Set(values);
  if (next.has(value)) {
    next.delete(value);
  } else {
    next.add(value);
  }
  return next;
}

function setAll(values: string[]): Set<string> {
  return new Set(values);
}

export function Sidebar({
  graphs,
  activeGraph,
  filters,
  source,
  sourceMessage,
  onGraphChange,
  onFiltersChange,
}: SidebarProps) {
  const entityTypes = entityTypesForGraph(activeGraph);
  const relationTypes = relationTypesForGraph(activeGraph);
  const reviewTotal = (activeGraph.stats.review_node_count ?? 0) + (activeGraph.stats.review_edge_count ?? 0);

  return (
    <aside className="sidebar">
      <div className="brand-block">
        <div className="brand-mark">
          <Database size={18} />
        </div>
        <div>
          <p className="eyebrow">OntoWikiGraph</p>
          <h1>每文件 KG</h1>
        </div>
      </div>

      <div className={`source-banner ${source === "mock" ? "is-mock" : "is-export"}`}>
        <span>{source === "mock" ? "Mock 数据" : "导出数据"}</span>
        <small>{source === "mock" ? "未发现 /kg/index.json，已启用演示数据" : sourceMessage}</small>
      </div>

      <section className="panel">
        <div className="panel-title">
          <FileText size={16} />
          <span>文件</span>
        </div>
        <div className="document-list">
          {graphs.map((graph) => (
            <button
              className={`document-item ${
                graph.document.document_id === activeGraph.document.document_id ? "is-active" : ""
              }`}
              key={graph.document.document_id}
              onClick={() => onGraphChange(graph.document.document_id)}
              type="button"
            >
              <span className="document-name">{graph.document.document_name}</span>
              <span className="document-meta">
                {graph.stats.node_count} nodes / {graph.stats.edge_count} edges
              </span>
            </button>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panel-title">
          <Filter size={16} />
          <span>过滤</span>
        </div>
        <label className="review-toggle">
          <input
            checked={filters.reviewOnly}
            onChange={(event) => onFiltersChange({ ...filters, reviewOnly: event.target.checked })}
            type="checkbox"
          />
          <span>
            只看 Review
            <small>{reviewTotal} items</small>
          </span>
          <AlertTriangle size={16} />
        </label>

        <div className="filter-group">
          <div className="filter-heading">
            <span>节点类型</span>
            <button onClick={() => onFiltersChange({ ...filters, entityTypes: setAll(entityTypes) })} type="button">
              全选
            </button>
          </div>
          <div className="chip-grid">
            {entityTypes.map((type) => (
              <button
                className={`filter-chip ${filters.entityTypes.has(type) ? "is-on" : ""}`}
                key={type}
                onClick={() =>
                  onFiltersChange({
                    ...filters,
                    entityTypes: toggleSetValue(filters.entityTypes, type),
                  })
                }
                title={type}
                type="button"
              >
                {type}
              </button>
            ))}
          </div>
        </div>

        <div className="filter-group">
          <div className="filter-heading">
            <span>关系类型</span>
            <button onClick={() => onFiltersChange({ ...filters, relationTypes: setAll(relationTypes) })} type="button">
              全选
            </button>
          </div>
          <div className="chip-grid">
            {relationTypes.map((type) => (
              <button
                className={`filter-chip relation ${filters.relationTypes.has(type) ? "is-on" : ""}`}
                key={type}
                onClick={() =>
                  onFiltersChange({
                    ...filters,
                    relationTypes: toggleSetValue(filters.relationTypes, type),
                  })
                }
                title={type}
                type="button"
              >
                {type}
              </button>
            ))}
          </div>
        </div>
      </section>

      <div className="search-note">
        <Search size={15} />
        <span>选中节点或边后，右侧会显示证据和路径。</span>
      </div>
    </aside>
  );
}
