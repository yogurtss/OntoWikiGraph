import { useCallback, useEffect, useMemo, useState } from "react";

import { GraphCanvas } from "./components/GraphCanvas";
import { Inspector } from "./components/Inspector";
import { Sidebar } from "./components/Sidebar";
import { Toolbar } from "./components/Toolbar";
import { entityTypesForGraph, getAllNodes, relationTypesForGraph } from "./lib/graphUtils";
import { loadGraphs } from "./lib/loadGraphs";
import type { GraphFilters, KGGraph, LayoutName, LoadedGraphs, NodeSearchMatch, SelectedGraphItem } from "./types";

const LOCAL_INDEX_STORAGE_KEY = "ontowikigraph.localIndexPath";

function initialLocalIndexPath(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return localStorage.getItem(LOCAL_INDEX_STORAGE_KEY) ?? "";
}

function defaultFilters(graph: KGGraph): GraphFilters {
  return {
    entityTypes: new Set(entityTypesForGraph(graph)),
    relationTypes: new Set(relationTypesForGraph(graph)),
    reviewOnly: false,
  };
}

export default function App() {
  const [loaded, setLoaded] = useState<LoadedGraphs | null>(null);
  const [activeDocumentId, setActiveDocumentId] = useState<string>("");
  const [filters, setFilters] = useState<GraphFilters | null>(null);
  const [layout, setLayout] = useState<LayoutName>("cose");
  const [selection, setSelection] = useState<SelectedGraphItem | null>(null);
  const [fitSignal, setFitSignal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [localIndexPath, setLocalIndexPath] = useState<string>(initialLocalIndexPath);
  const [localImportError, setLocalImportError] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");
  const [focusNodeId, setFocusNodeId] = useState<string | null>(null);
  const [focusSignal, setFocusSignal] = useState(0);

  const applyLoadedResult = useCallback((result: LoadedGraphs) => {
    setLoaded(result);
    setActiveDocumentId(result.graphs[0]?.document.document_id ?? "");
    setFilters(result.graphs[0] ? defaultFilters(result.graphs[0]) : null);
    setSelection(null);
    setFocusNodeId(null);
  }, []);

  const refreshGraphs = useCallback(async (overrideLocalIndexPath?: string) => {
    const nextLocalIndexPath = overrideLocalIndexPath ?? localIndexPath;
    setIsLoading(true);
    setLocalImportError("");
    try {
      const result = await loadGraphs(nextLocalIndexPath ? { localIndexPath: nextLocalIndexPath } : undefined);
      applyLoadedResult(result);
      if (nextLocalIndexPath) {
        localStorage.setItem(LOCAL_INDEX_STORAGE_KEY, nextLocalIndexPath);
        setLocalIndexPath(nextLocalIndexPath);
      } else {
        localStorage.removeItem(LOCAL_INDEX_STORAGE_KEY);
        setLocalIndexPath("");
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to load local index.";
      setLocalImportError(message);
      const fallback = await loadGraphs();
      applyLoadedResult(fallback);
    } finally {
      setIsLoading(false);
    }
  }, [applyLoadedResult, localIndexPath]);

  useEffect(() => {
    void refreshGraphs();
  }, [refreshGraphs]);

  const activeGraph = useMemo(() => {
    if (!loaded?.graphs.length) {
      return null;
    }
    return loaded.graphs.find((graph) => graph.document.document_id === activeDocumentId) ?? loaded.graphs[0];
  }, [activeDocumentId, loaded]);

  useEffect(() => {
    if (activeGraph) {
      setFilters(defaultFilters(activeGraph));
      setSelection(null);
      setSearchQuery("");
      setFocusNodeId(null);
    }
  }, [activeGraph?.document.document_id]);

  const searchResults = useMemo<NodeSearchMatch[]>(() => {
    if (!activeGraph || !searchQuery.trim()) {
      return [];
    }
    const query = searchQuery.trim().toLowerCase();
    return getAllNodes(activeGraph)
      .filter((node) => node.name.toLowerCase().includes(query))
      .slice(0, 20)
      .map((node) => ({
        id: node.id,
        name: node.name,
        entityType: node.entity_type,
        treePath: node.tree_path,
      }));
  }, [activeGraph, searchQuery]);

  const handleSearchSelect = useCallback((match: NodeSearchMatch) => {
    setFocusNodeId(match.id);
    setFocusSignal((value) => value + 1);
  }, []);

  if (isLoading || !loaded || !activeGraph || !filters) {
    return (
      <main className="loading-screen">
        <div className="loading-mark" />
        <span>加载 KG workbench...</span>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <Sidebar
        activeGraph={activeGraph}
        filters={filters}
        graphs={loaded.graphs}
        onFiltersChange={setFilters}
        onGraphChange={setActiveDocumentId}
        onLocalIndexPathChange={setLocalIndexPath}
        onLoadLocalIndex={() => void refreshGraphs(localIndexPath)}
        onClearLocalIndex={() => void refreshGraphs("")}
        localImportError={localImportError}
        localIndexPath={localIndexPath}
        source={loaded.source}
        sourceMessage={loaded.message}
      />
      <section className="workspace">
        <Toolbar
          activeGraph={activeGraph}
          layout={layout}
          onFit={() => setFitSignal((value) => value + 1)}
          onLayoutChange={setLayout}
          onReload={() => void refreshGraphs()}
          onSearchQueryChange={setSearchQuery}
          onSearchSelect={handleSearchSelect}
          searchQuery={searchQuery}
          searchResults={searchResults}
        />
        <GraphCanvas
          filters={filters}
          fitSignal={fitSignal}
          focusNodeId={focusNodeId}
          focusSignal={focusSignal}
          graph={activeGraph}
          layout={layout}
          onSelect={setSelection}
        />
      </section>
      <Inspector selection={selection} />
    </main>
  );
}
