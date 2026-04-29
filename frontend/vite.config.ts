import { readFile } from "node:fs/promises";
import path from "node:path";
import type { IncomingMessage, ServerResponse } from "node:http";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

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

function sendJson(response: ServerResponse, status: number, payload: unknown): void {
  response.statusCode = status;
  response.setHeader("Content-Type", "application/json; charset=utf-8");
  response.end(JSON.stringify(payload));
}

async function readJsonFile<T>(filePath: string): Promise<T> {
  const content = await readFile(filePath, "utf-8");
  return JSON.parse(content) as T;
}

function isRemoteUrl(value: string): boolean {
  return /^https?:\/\//i.test(value);
}

function resolveGraphPath(name: string, entry: IndexEntry, baseDir: string): string {
  if (typeof entry === "string") {
    return path.resolve(baseDir, entry, "graph.json");
  }
  if (entry.graph_url && isRemoteUrl(entry.graph_url)) {
    return entry.graph_url;
  }
  if (entry.graph_path) {
    return path.resolve(baseDir, entry.graph_path);
  }
  if (entry.export_path) {
    return path.resolve(baseDir, entry.export_path);
  }
  if (entry.document_id) {
    return path.resolve(baseDir, entry.document_id, "exports", "graph.json");
  }
  return path.resolve(baseDir, name, "graph.json");
}

function normalizeLocalIndex(index: GraphIndex, indexPath: string): GraphIndex {
  const baseDir = path.dirname(indexPath);
  if (Array.isArray(index)) {
    return index.map((entry, indexNumber) => {
      if (typeof entry === "string") {
        const graphPath = resolveGraphPath(entry, entry, baseDir);
        return {
          document_id: entry,
          document_name: entry,
          graph_url: isRemoteUrl(graphPath) ? graphPath : `/api/local-graph?path=${encodeURIComponent(graphPath)}`,
        };
      }
      const name = entry.document_name ?? entry.document_id ?? `graph-${indexNumber + 1}`;
      const graphPath = resolveGraphPath(name, entry, baseDir);
      return {
        ...entry,
        graph_url: isRemoteUrl(graphPath) ? graphPath : `/api/local-graph?path=${encodeURIComponent(graphPath)}`,
      };
    });
  }

  return Object.fromEntries(
    Object.entries(index).map(([name, entry]) => {
      const graphPath = resolveGraphPath(name, entry, baseDir);
      if (typeof entry === "string") {
        return [
          name,
          {
            document_id: entry,
            document_name: name,
            graph_url: isRemoteUrl(graphPath) ? graphPath : `/api/local-graph?path=${encodeURIComponent(graphPath)}`,
          },
        ];
      }
      return [
        name,
        {
          ...entry,
          graph_url: isRemoteUrl(graphPath) ? graphPath : `/api/local-graph?path=${encodeURIComponent(graphPath)}`,
        },
      ];
    }),
  );
}

async function readRequestBody(request: IncomingMessage): Promise<string> {
  const chunks: Buffer[] = [];
  for await (const chunk of request) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }
  return Buffer.concat(chunks).toString("utf-8");
}

async function handleLocalIndex(request: IncomingMessage, response: ServerResponse): Promise<void> {
  try {
    const body = await readRequestBody(request);
    const payload = JSON.parse(body || "{}") as { index_path?: string };
    const indexPath = payload.index_path?.trim();
    if (!indexPath || !path.isAbsolute(indexPath)) {
      sendJson(response, 400, { error: "index_path must be an absolute path to index.json" });
      return;
    }

    const normalizedIndexPath = path.resolve(indexPath);
    const index = await readJsonFile<GraphIndex>(normalizedIndexPath);
    const normalizedIndex = normalizeLocalIndex(index, normalizedIndexPath);
    const graphCount = Array.isArray(normalizedIndex) ? normalizedIndex.length : Object.keys(normalizedIndex).length;
    sendJson(response, 200, {
      index: normalizedIndex,
      index_path: normalizedIndexPath,
      graph_count: graphCount,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to read local index.";
    sendJson(response, 500, { error: message });
  }
}

async function handleLocalGraph(request: IncomingMessage, response: ServerResponse): Promise<void> {
  try {
    const url = new URL(request.url ?? "", "http://localhost");
    const graphPath = url.searchParams.get("path")?.trim();
    if (!graphPath || !path.isAbsolute(graphPath)) {
      sendJson(response, 400, { error: "path must be an absolute path to graph.json" });
      return;
    }
    const normalizedGraphPath = path.resolve(graphPath);
    const graph = await readJsonFile<unknown>(normalizedGraphPath);
    sendJson(response, 200, graph);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to read graph.";
    sendJson(response, 500, { error: message });
  }
}

function attachLocalGraphProxy(server: { middlewares: { use: (handler: (request: IncomingMessage, response: ServerResponse, next: () => void) => void | Promise<void>) => void } }): void {
  server.middlewares.use(async (request, response, next) => {
    if (request.method === "POST" && request.url === "/api/local-index") {
      await handleLocalIndex(request, response);
      return;
    }
    if (request.method === "GET" && request.url?.startsWith("/api/local-graph")) {
      await handleLocalGraph(request, response);
      return;
    }
    next();
  });
}

export default defineConfig({
  plugins: [
    react(),
    {
      name: "local-graph-proxy",
      configureServer(server) {
        attachLocalGraphProxy(server);
      },
      configurePreviewServer(server) {
        attachLocalGraphProxy(server);
      },
    },
  ],
  server: {
    port: 5173,
  },
});
