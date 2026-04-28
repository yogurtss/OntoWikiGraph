export type NodeKind = "structural" | "semantic";
export type EdgeSource = "structural" | "extracted" | "normalized";
export type LayoutName = "cose" | "breadthfirst" | "circle";

export interface DocumentSummary {
  document_name: string;
  document_id: string;
  source_path: string;
}

export interface TreeNode {
  node_id: string;
  title: string;
  level: number;
  content: string;
  node_type: string;
  path: string;
  parent_id?: string | null;
  metadata?: Record<string, unknown>;
  children?: TreeNode[];
}

export interface KGNode {
  id: string;
  name: string;
  entity_type: string;
  description: string;
  kind: NodeKind;
  evidence_span: string;
  evidence_status: string;
  ontology_status: string;
  document_id: string;
  tree_path: string;
  source_path: string;
  source_trace_id?: string;
  modality: string;
  metadata?: Record<string, unknown>;
  review_reasons?: string[];
}

export interface KGEdge {
  id: string;
  src: string;
  tgt: string;
  relation_type: string;
  description: string;
  edge_source: EdgeSource;
  evidence_span: string;
  evidence_status: string;
  ontology_status: string;
  confidence: number;
  document_id: string;
  tree_path: string;
  source_path: string;
  metadata?: Record<string, unknown>;
  review_reasons?: string[];
}

export interface GraphStats {
  node_count: number;
  edge_count: number;
  review_node_count: number;
  review_edge_count: number;
  [key: string]: number | string | boolean | null | undefined;
}

export interface KGGraph {
  document: DocumentSummary;
  tree: TreeNode;
  ontology?: {
    entity_types: string[];
    relation_types: string[];
    structural_relation_types: string[];
  };
  nodes: KGNode[];
  edges: KGEdge[];
  review: {
    nodes: KGNode[];
    edges: KGEdge[];
  };
  stats: GraphStats;
  export_path?: string;
}

export interface GraphFilters {
  entityTypes: Set<string>;
  relationTypes: Set<string>;
  reviewOnly: boolean;
}

export interface SelectedGraphItem {
  type: "node" | "edge";
  data: Record<string, unknown>;
}

export interface LoadedGraphs {
  graphs: KGGraph[];
  source: "export" | "mock";
  message?: string;
}
