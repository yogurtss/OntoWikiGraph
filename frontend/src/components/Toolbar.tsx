import { Circle, Focus, GitBranch, Network, RefreshCw, Search } from "lucide-react";

import type { KGGraph, LayoutName, NodeSearchMatch } from "../types";

interface ToolbarProps {
  activeGraph: KGGraph;
  layout: LayoutName;
  onLayoutChange: (layout: LayoutName) => void;
  onFit: () => void;
  onReload: () => void;
  searchQuery: string;
  searchResults: NodeSearchMatch[];
  onSearchQueryChange: (value: string) => void;
  onSearchSelect: (match: NodeSearchMatch) => void;
}

const layouts: Array<{ id: LayoutName; label: string; icon: typeof Network }> = [
  { id: "cose", label: "Force", icon: Network },
  { id: "breadthfirst", label: "Tree", icon: GitBranch },
  { id: "circle", label: "Circle", icon: Circle },
];

export function Toolbar({
  activeGraph,
  layout,
  onLayoutChange,
  onFit,
  onReload,
  searchQuery,
  searchResults,
  onSearchQueryChange,
  onSearchSelect,
}: ToolbarProps) {
  return (
    <header className="topbar">
      <div className="document-heading">
        <p>{activeGraph.document.source_path}</p>
        <h2>{activeGraph.document.document_name}</h2>
      </div>
      <div className="toolbar-search">
        <label aria-label="按节点名搜索" className="search-field">
          <Search size={15} />
          <input
            onChange={(event) => onSearchQueryChange(event.target.value)}
            placeholder="按节点名搜索"
            type="search"
            value={searchQuery}
          />
        </label>
        {searchQuery.trim() ? (
          <div className="search-results">
            {searchResults.length ? (
              searchResults.map((result) => (
                <button key={result.id} onClick={() => onSearchSelect(result)} type="button">
                  <strong>{result.name}</strong>
                  <span>
                    {result.entityType} · {result.treePath}
                  </span>
                </button>
              ))
            ) : (
              <div className="search-results-empty">当前图中没有匹配的节点</div>
            )}
          </div>
        ) : null}
      </div>
      <div className="stats-strip" aria-label="Graph statistics">
        <span>
          <strong>{activeGraph.stats.node_count}</strong>
          nodes
        </span>
        <span>
          <strong>{activeGraph.stats.edge_count}</strong>
          edges
        </span>
        <span>
          <strong>{activeGraph.stats.review_node_count + activeGraph.stats.review_edge_count}</strong>
          review
        </span>
      </div>
      <div className="toolbar-actions">
        <div className="segmented" aria-label="Layout mode">
          {layouts.map((item) => {
            const Icon = item.icon;
            return (
              <button
                className={layout === item.id ? "is-active" : ""}
                key={item.id}
                onClick={() => onLayoutChange(item.id)}
                title={`切换到 ${item.label} 布局`}
                type="button"
              >
                <Icon size={16} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>
        <button className="icon-button" onClick={onFit} title="适配视图" type="button">
          <Focus size={18} />
        </button>
        <button className="icon-button" onClick={onReload} title="重新加载数据" type="button">
          <RefreshCw size={18} />
        </button>
      </div>
    </header>
  );
}
