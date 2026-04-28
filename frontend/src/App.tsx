import { useCallback, useEffect, useMemo, useState } from "react";

import { GraphCanvas } from "./components/GraphCanvas";
import { Inspector } from "./components/Inspector";
import { Sidebar } from "./components/Sidebar";
import { Toolbar } from "./components/Toolbar";
import { entityTypesForGraph, relationTypesForGraph } from "./lib/graphUtils";
import { loadGraphs } from "./lib/loadGraphs";
import type { GraphFilters, KGGraph, LayoutName, LoadedGraphs, SelectedGraphItem } from "./types";

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

  const refreshGraphs = useCallback(async () => {
    setIsLoading(true);
    const result = await loadGraphs();
    setLoaded(result);
    setActiveDocumentId(result.graphs[0]?.document.document_id ?? "");
    setFilters(result.graphs[0] ? defaultFilters(result.graphs[0]) : null);
    setSelection(null);
    setIsLoading(false);
  }, []);

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
    }
  }, [activeGraph?.document.document_id]);

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
        source={loaded.source}
        sourceMessage={loaded.message}
      />
      <section className="workspace">
        <Toolbar
          activeGraph={activeGraph}
          layout={layout}
          onFit={() => setFitSignal((value) => value + 1)}
          onLayoutChange={setLayout}
          onReload={refreshGraphs}
        />
        <GraphCanvas
          filters={filters}
          fitSignal={fitSignal}
          graph={activeGraph}
          layout={layout}
          onSelect={setSelection}
        />
      </section>
      <Inspector selection={selection} />
    </main>
  );
}
