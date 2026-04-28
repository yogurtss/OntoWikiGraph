from __future__ import annotations

from kg_workbench.models import KGEdge, KGNode
from kg_workbench.utils import normalize_key, stable_id


def _merge_text(a: str, b: str, sep: str = "\n") -> str:
    parts = []
    seen = set()
    for value in (a, b):
        for part in str(value or "").split(sep):
            item = part.strip()
            if item and item not in seen:
                parts.append(item)
                seen.add(item)
    return sep.join(parts)


def normalize_and_cluster(
    nodes: list[KGNode],
    edges: list[KGEdge],
) -> tuple[list[KGNode], list[KGEdge]]:
    node_by_cluster: dict[str, KGNode] = {}
    id_map: dict[str, str] = {}

    for node in nodes:
        if node.kind == "structural":
            cluster_id = node.id
        else:
            cluster_key = normalize_key(f"{node.entity_type}:{node.name}")
            cluster_id = stable_id(node.document_id, cluster_key, prefix="ent-")

        id_map[node.id] = cluster_id
        if cluster_id not in node_by_cluster:
            node.id = cluster_id
            node.name = node.name.strip()
            node.metadata = dict(node.metadata)
            node.metadata.setdefault("mentions", [])
            if node.kind != "structural":
                node.metadata["mentions"].append(node.name)
            node_by_cluster[cluster_id] = node
            continue

        existing = node_by_cluster[cluster_id]
        existing.description = _merge_text(existing.description, node.description)
        existing.evidence_span = _merge_text(existing.evidence_span, node.evidence_span)
        existing.metadata.setdefault("mentions", [])
        if node.name not in existing.metadata["mentions"] and node.kind != "structural":
            existing.metadata["mentions"].append(node.name)

    edge_by_key: dict[tuple[str, str, str, str], KGEdge] = {}
    for edge in edges:
        edge.src = id_map.get(edge.src, edge.src)
        edge.tgt = id_map.get(edge.tgt, edge.tgt)
        if edge.src == edge.tgt:
            continue
        key = (edge.src, edge.tgt, edge.relation_type, edge.edge_source)
        if key not in edge_by_key:
            edge.id = stable_id(edge.document_id, *key, prefix="edge-")
            edge_by_key[key] = edge
            continue
        existing = edge_by_key[key]
        existing.description = _merge_text(existing.description, edge.description)
        existing.evidence_span = _merge_text(existing.evidence_span, edge.evidence_span)
        existing.confidence = max(existing.confidence, edge.confidence)

    return list(node_by_cluster.values()), list(edge_by_key.values())

