import { mockGraphs } from "../data/mockGraphs";
import type { KGGraph, LoadedGraphs } from "../types";

type IndexEntry =
  | string
  | {
      document_id?: string;
      document_name?: string;
      source_path?: string;
      export_path?: string;
      graph_path?: string;
      graph_url?: string;
    };

type GraphIndex = Record<string, IndexEntry> | IndexEntry[];

function isGraph(value: unknown): value is KGGraph {
  const graph = value as KGGraph;
  return Boolean(graph?.document?.document_id && Array.isArray(graph.nodes) && Array.isArray(graph.edges));
}

function normalizeGraph(graph: KGGraph): KGGraph {
  return {
    ...graph,
    review: {
      nodes: graph.review?.nodes ?? [],
      edges: graph.review?.edges ?? [],
    },
    stats: {
      ...graph.stats,
      node_count: graph.stats?.node_count ?? graph.nodes.length,
      edge_count: graph.stats?.edge_count ?? graph.edges.length,
      review_node_count: graph.stats?.review_node_count ?? graph.review?.nodes?.length ?? 0,
      review_edge_count: graph.stats?.review_edge_count ?? graph.review?.edges?.length ?? 0,
    },
  };
}

function graphUrlForEntry(name: string, entry: IndexEntry): string {
  if (typeof entry === "string") {
    return `/kg/${encodeURIComponent(entry)}/graph.json`;
  }

  if (entry.graph_url) {
    return entry.graph_url;
  }

  if (entry.graph_path) {
    return entry.graph_path.startsWith("/") ? entry.graph_path : `/kg/${entry.graph_path}`;
  }

  if (entry.document_id) {
    return `/kg/${encodeURIComponent(entry.document_id)}/graph.json`;
  }

  if (entry.export_path?.startsWith("/kg/")) {
    return entry.export_path;
  }

  return `/kg/${encodeURIComponent(name)}/graph.json`;
}

function normalizeIndex(index: GraphIndex): Array<[string, IndexEntry]> {
  if (Array.isArray(index)) {
    return index.map((entry, indexNumber) => {
      if (typeof entry === "string") {
        return [entry, entry];
      }
      return [entry.document_name ?? entry.document_id ?? `graph-${indexNumber + 1}`, entry];
    });
  }
  return Object.entries(index);
}

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

export async function loadGraphs(): Promise<LoadedGraphs> {
  try {
    const index = await fetchJson<GraphIndex>("/kg/index.json");
    const entries = normalizeIndex(index);
    const graphs = await Promise.all(
      entries.map(async ([name, entry]) => {
        const graph = await fetchJson<KGGraph>(graphUrlForEntry(name, entry));
        if (!isGraph(graph)) {
          throw new Error(`Invalid graph payload for ${name}`);
        }
        return normalizeGraph(graph);
      }),
    );

    if (!graphs.length) {
      throw new Error("No graphs listed in /kg/index.json");
    }

    return {
      graphs,
      source: "export",
      message: `Loaded ${graphs.length} exported graph${graphs.length > 1 ? "s" : ""}.`,
    };
  } catch (error) {
    return {
      graphs: mockGraphs.map(normalizeGraph),
      source: "mock",
      message: error instanceof Error ? error.message : "Exported graphs are unavailable.",
    };
  }
}
