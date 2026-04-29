import cytoscape from "cytoscape";
import type { Core, EdgeSingular, EventObject, LayoutOptions, StylesheetJson } from "cytoscape";
import { Maximize2 } from "lucide-react";
import { useEffect, useMemo, useRef } from "react";

import { buildCytoscapeElements } from "../lib/graphUtils";
import type { GraphFilters, KGGraph, LayoutName, SelectedGraphItem } from "../types";

interface GraphCanvasProps {
  graph: KGGraph;
  filters: GraphFilters;
  layout: LayoutName;
  fitSignal: number;
  focusNodeId: string | null;
  focusSignal: number;
  onSelect: (selection: SelectedGraphItem | null) => void;
}

const cytoscapeStyle: StylesheetJson = [
  {
    selector: "node",
    style: {
      "background-color": "data(color)",
      "border-color": "#ffffff",
      "border-width": 2,
      color: "#162029",
      "font-family": "Inter, ui-sans-serif, system-ui, sans-serif",
      "font-size": 11,
      "font-weight": 700,
      height: 34,
      label: "data(label)",
      "min-zoomed-font-size": 8,
      "overlay-opacity": 0,
      shape: "ellipse",
      "text-background-color": "#ffffff",
      "text-background-opacity": 0.92,
      "text-background-padding": "4px",
      "text-halign": "center",
      "text-margin-y": 8,
      "text-max-width": "130px",
      "text-valign": "bottom",
      "text-wrap": "wrap",
      width: 34,
    },
  },
  {
    selector: ".structural-node",
    style: {
      "background-color": "#eef3f5",
      "border-color": "#78909c",
      color: "#26343b",
      height: 28,
      shape: "round-rectangle",
      width: 48,
    },
  },
  {
    selector: ".modality-table",
    style: {
      shape: "rectangle",
      "border-style": "double",
    },
  },
  {
    selector: ".modality-image",
    style: {
      shape: "hexagon",
    },
  },
  {
    selector: ".review-item",
    style: {
      "border-color": "#b42318",
      "border-width": 4,
      "line-color": "#b42318",
      "target-arrow-color": "#b42318",
    },
  },
  {
    selector: "edge",
    style: {
      "curve-style": "bezier",
      "font-family": "Inter, ui-sans-serif, system-ui, sans-serif",
      "font-size": 9,
      label: "data(label)",
      "line-color": "#89949f",
      opacity: 0.78,
      "overlay-opacity": 0,
      "target-arrow-color": "#89949f",
      "target-arrow-shape": "triangle",
      "text-background-color": "#f7faf9",
      "text-background-opacity": 0.86,
      "text-background-padding": "2px",
      "text-rotation": "autorotate",
      width: 1.4,
    },
  },
  {
    selector: ".hide-label",
    style: {
      label: "",
    },
  },
  {
    selector: ".structural-edge",
    style: {
      "line-color": "#a7b2ba",
      "line-style": "dashed",
      "target-arrow-color": "#a7b2ba",
      width: 1,
    },
  },
  {
    selector: ".semantic-edge",
    style: {
      "line-color": "#2f6f73",
      "target-arrow-color": "#2f6f73",
      width: 2,
    },
  },
  {
    selector: ".dimmed",
    style: {
      opacity: 0.14,
      "text-opacity": 0,
    },
  },
  {
    selector: ".neighbor",
    style: {
      opacity: 1,
    },
  },
  {
    selector: ".selected",
    style: {
      "border-color": "#111827",
      "border-width": 5,
      "line-color": "#111827",
      "target-arrow-color": "#111827",
      width: 3.5,
      "z-index": 20,
    },
  },
];

function layoutOptions(layout: LayoutName, disableAnimation: boolean): LayoutOptions {
  if (layout === "breadthfirst") {
    return {
      name: "breadthfirst",
      animate: !disableAnimation,
      animationDuration: disableAnimation ? 0 : 420,
      directed: true,
      fit: true,
      padding: 48,
      spacingFactor: 1.25,
    } as LayoutOptions;
  }

  if (layout === "circle") {
    return {
      name: "circle",
      animate: !disableAnimation,
      animationDuration: disableAnimation ? 0 : 420,
      fit: true,
      padding: 48,
    } as LayoutOptions;
  }

  return {
    name: "cose",
    animate: !disableAnimation,
    animationDuration: disableAnimation ? 0 : 560,
    fit: true,
    idealEdgeLength: 118,
    nodeOverlap: 14,
    padding: 48,
    refresh: 20,
  } as LayoutOptions;
}

function clearFocus(cy: Core, hideEdgeLabels: boolean): void {
  cy.elements().removeClass("dimmed neighbor selected");
  if (hideEdgeLabels) {
    cy.edges().addClass("hide-label");
  } else {
    cy.edges().removeClass("hide-label");
  }
}

function focusElement(cy: Core, target: cytoscape.SingularElementReturnValue, hideEdgeLabels: boolean): void {
  clearFocus(cy, hideEdgeLabels);
  const neighborhood = target.isNode()
    ? target.closedNeighborhood()
    : (target as EdgeSingular).source().union((target as EdgeSingular).target()).union(target);
  cy.elements().not(neighborhood).addClass("dimmed");
  neighborhood.addClass("neighbor");
  if (hideEdgeLabels && target.isEdge()) {
    target.removeClass("hide-label");
  }
  target.addClass("selected");
}

function fitGraph(cy: Core, hideAnimation: boolean): void {
  if (hideAnimation) {
    cy.fit(cy.elements(), 48);
    return;
  }
  cy.animate({ fit: { eles: cy.elements(), padding: 48 } }, { duration: 280 });
}

export function GraphCanvas({
  graph,
  filters,
  layout,
  fitSignal,
  focusNodeId,
  focusSignal,
  onSelect,
}: GraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);
  const elements = useMemo(() => buildCytoscapeElements(graph, filters), [graph, filters]);
  const isLargeGraph = graph.stats.node_count >= 300 || graph.stats.edge_count >= 600;

  useEffect(() => {
    if (!containerRef.current) {
      return;
    }

    if (cyRef.current) {
      cyRef.current.destroy();
      cyRef.current = null;
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements: [],
      layout: { name: "preset" },
      hideEdgesOnViewport: isLargeGraph,
      maxZoom: 2.6,
      minZoom: 0.16,
      motionBlur: isLargeGraph,
      pixelRatio: isLargeGraph ? 1 : undefined,
      style: cytoscapeStyle,
      textureOnViewport: isLargeGraph,
      wheelSensitivity: 0.18,
    });

    const handleElementTap = (event: EventObject) => {
      const target = event.target as cytoscape.SingularElementReturnValue;
      focusElement(cy, target, isLargeGraph);
      onSelect({
        type: target.isNode() ? "node" : "edge",
        data: target.data(),
      });
    };

    const handleCanvasTap = (event: EventObject) => {
      if (event.target === cy) {
        clearFocus(cy, isLargeGraph);
        onSelect(null);
      }
    };

    cy.on("tap", "node, edge", handleElementTap);
    cy.on("tap", handleCanvasTap);
    cyRef.current = cy;

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [isLargeGraph, onSelect]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) {
      return;
    }

    cy.batch(() => {
      cy.elements().remove();
      cy.add(elements);
    });
    clearFocus(cy, isLargeGraph);
    onSelect(null);
  }, [elements, graph.document.document_id, isLargeGraph, onSelect]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) {
      return;
    }
    cy.layout(layoutOptions(layout, isLargeGraph)).run();
  }, [graph.document.document_id, isLargeGraph, layout]);

  useEffect(() => {
    const cy = cyRef.current;
    if (cy && fitSignal > 0) {
      fitGraph(cy, isLargeGraph);
    }
  }, [fitSignal, isLargeGraph]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || !focusNodeId || focusSignal === 0) {
      return;
    }
    const target = cy.getElementById(focusNodeId);
    if (!target.nonempty()) {
      return;
    }
    focusElement(cy, target, isLargeGraph);
    onSelect({
      type: "node",
      data: target.data(),
    });
    fitGraph(cy, isLargeGraph);
  }, [focusNodeId, focusSignal, isLargeGraph, onSelect]);

  return (
    <section className="graph-stage" aria-label="Knowledge graph canvas">
      <div className="canvas-toolbar">
        <span>{elements.filter((element) => element.group === "nodes").length} nodes</span>
        <span>{elements.filter((element) => element.group === "edges").length} edges</span>
        {isLargeGraph ? <span>大图模式</span> : null}
      </div>
      <div ref={containerRef} className="graph-canvas" />
      {!elements.length ? (
        <div className="empty-graph">
          <Maximize2 size={26} />
          <span>当前过滤条件下没有可显示的图谱元素</span>
        </div>
      ) : null}
    </section>
  );
}
