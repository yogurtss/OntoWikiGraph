from __future__ import annotations

from dataclasses import asdict
from typing import Any

from kg_workbench.models import KGEdge, KGNode

from .schema import Ontology


def _node_has_grounding(node: KGNode) -> bool:
    if node.kind == "structural":
        return True
    if node.modality in {"image", "table", "formula", "video"}:
        return bool(
            node.evidence_span.strip()
            or node.metadata.get("img_path")
            or node.metadata.get("table_body")
            or node.metadata.get("image_caption")
            or node.metadata.get("table_caption")
        )
    return bool(node.evidence_span.strip())


def _edge_has_grounding(edge: KGEdge) -> bool:
    if edge.edge_source == "structural":
        return True
    return bool(edge.evidence_span.strip())


def validate_graph(
    nodes: list[KGNode],
    edges: list[KGEdge],
    ontology: Ontology,
    *,
    min_confidence: float = 0.5,
) -> tuple[list[KGNode], list[KGEdge], dict[str, list[dict[str, Any]]]]:
    valid_nodes: list[KGNode] = []
    valid_node_ids: set[str] = set()
    review: dict[str, list[dict[str, Any]]] = {
        "nodes": [],
        "edges": [],
    }

    for node in nodes:
        reasons = []
        if node.entity_type not in ontology.entity_types:
            reasons.append("unknown_entity_type")
        if not _node_has_grounding(node):
            reasons.append("missing_evidence")
        if reasons:
            node.ontology_status = "rejected"
            node.evidence_status = "missing" if "missing_evidence" in reasons else node.evidence_status
            payload = asdict(node)
            payload["review_reasons"] = reasons
            review["nodes"].append(payload)
            continue
        node.ontology_status = "valid"
        if node.evidence_status == "missing":
            node.evidence_status = "asset_grounded" if node.modality != "text" else "grounded"
        valid_nodes.append(node)
        valid_node_ids.add(node.id)

    valid_edges: list[KGEdge] = []
    for edge in edges:
        reasons = []
        if edge.src not in valid_node_ids or edge.tgt not in valid_node_ids:
            reasons.append("missing_valid_endpoint")
        if edge.relation_type not in ontology.relation_types:
            reasons.append("unknown_relation_type")
        if edge.confidence < min_confidence:
            reasons.append("low_confidence")
        if not _edge_has_grounding(edge):
            reasons.append("missing_evidence")
        if reasons:
            edge.ontology_status = "rejected"
            edge.evidence_status = "missing" if "missing_evidence" in reasons else edge.evidence_status
            payload = asdict(edge)
            payload["review_reasons"] = reasons
            review["edges"].append(payload)
            continue
        edge.ontology_status = "valid"
        if edge.evidence_status == "missing":
            edge.evidence_status = "grounded" if edge.edge_source != "structural" else "structural"
        valid_edges.append(edge)

    return valid_nodes, valid_edges, review

