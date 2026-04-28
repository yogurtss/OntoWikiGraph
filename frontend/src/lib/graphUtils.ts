import type { ElementDefinition } from "cytoscape";

import type { GraphFilters, KGEdge, KGGraph, KGNode } from "../types";

const palette = [
  "#1b6b73",
  "#bf5b45",
  "#5a6f2a",
  "#8a5a2b",
  "#7356a6",
  "#28745d",
  "#b0446f",
  "#5f6f89",
  "#a36a00",
  "#3f6d9a",
];

function hashString(value: string): number {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) >>> 0;
  }
  return hash;
}

export function colorForType(entityType: string): string {
  return palette[hashString(entityType) % palette.length];
}

export function getAllNodes(graph: KGGraph): Array<KGNode & { isReview?: boolean }> {
  const byId = new Map<string, KGNode & { isReview?: boolean }>();
  graph.nodes.forEach((node) => byId.set(node.id, { ...node, isReview: false }));
  graph.review.nodes.forEach((node) => byId.set(node.id, { ...node, isReview: true }));
  return Array.from(byId.values());
}

export function getAllEdges(graph: KGGraph): Array<KGEdge & { isReview?: boolean }> {
  const byId = new Map<string, KGEdge & { isReview?: boolean }>();
  graph.edges.forEach((edge) => byId.set(edge.id, { ...edge, isReview: false }));
  graph.review.edges.forEach((edge) => byId.set(edge.id, { ...edge, isReview: true }));
  return Array.from(byId.values());
}

export function entityTypesForGraph(graph: KGGraph): string[] {
  return Array.from(new Set(getAllNodes(graph).map((node) => node.entity_type))).sort();
}

export function relationTypesForGraph(graph: KGGraph): string[] {
  return Array.from(new Set(getAllEdges(graph).map((edge) => edge.relation_type))).sort();
}

function nodeToElement(node: KGNode & { isReview?: boolean }): ElementDefinition {
  const reviewReasons = node.review_reasons ?? [];
  return {
    group: "nodes",
    data: {
      id: node.id,
      label: node.name,
      name: node.name,
      entityType: node.entity_type,
      kind: node.kind,
      modality: node.modality,
      description: node.description,
      evidenceSpan: node.evidence_span,
      evidenceStatus: node.evidence_status,
      ontologyStatus: node.ontology_status,
      documentId: node.document_id,
      treePath: node.tree_path,
      sourcePath: node.source_path,
      reviewReasons,
      review: Boolean(node.isReview),
      color: colorForType(node.entity_type),
    },
    classes: [
      node.kind === "structural" ? "structural-node" : "semantic-node",
      node.modality ? `modality-${node.modality}` : "",
      node.isReview ? "review-item" : "",
    ]
      .filter(Boolean)
      .join(" "),
  };
}

function edgeToElement(edge: KGEdge & { isReview?: boolean }): ElementDefinition {
  const reviewReasons = edge.review_reasons ?? [];
  return {
    group: "edges",
    data: {
      id: edge.id,
      source: edge.src,
      target: edge.tgt,
      label: edge.relation_type,
      relationType: edge.relation_type,
      edgeSource: edge.edge_source,
      description: edge.description,
      evidenceSpan: edge.evidence_span,
      evidenceStatus: edge.evidence_status,
      ontologyStatus: edge.ontology_status,
      confidence: edge.confidence,
      documentId: edge.document_id,
      treePath: edge.tree_path,
      sourcePath: edge.source_path,
      reviewReasons,
      review: Boolean(edge.isReview),
    },
    classes: [
      edge.edge_source === "structural" ? "structural-edge" : "semantic-edge",
      edge.isReview ? "review-item" : "",
    ]
      .filter(Boolean)
      .join(" "),
  };
}

export function buildCytoscapeElements(graph: KGGraph, filters: GraphFilters): ElementDefinition[] {
  const allNodes = getAllNodes(graph);
  const allEdges = getAllEdges(graph);
  const nodeCandidates = allNodes.filter((node) => filters.entityTypes.has(node.entity_type));
  const candidateNodeIds = new Set(nodeCandidates.map((node) => node.id));
  const edgeCandidates = allEdges.filter(
    (edge) =>
      filters.relationTypes.has(edge.relation_type) &&
      candidateNodeIds.has(edge.src) &&
      candidateNodeIds.has(edge.tgt) &&
      (!filters.reviewOnly || edge.isReview),
  );

  const visibleNodeIds = new Set<string>();
  if (filters.reviewOnly) {
    nodeCandidates.filter((node) => node.isReview).forEach((node) => visibleNodeIds.add(node.id));
    edgeCandidates.forEach((edge) => {
      visibleNodeIds.add(edge.src);
      visibleNodeIds.add(edge.tgt);
    });
  } else {
    nodeCandidates.forEach((node) => visibleNodeIds.add(node.id));
  }

  const nodes = nodeCandidates.filter((node) => visibleNodeIds.has(node.id)).map(nodeToElement);
  const edges = edgeCandidates.filter((edge) => visibleNodeIds.has(edge.src) && visibleNodeIds.has(edge.tgt)).map(edgeToElement);
  return [...nodes, ...edges];
}
