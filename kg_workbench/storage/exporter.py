from __future__ import annotations

from pathlib import Path
from typing import Any

from kg_workbench.models import DocumentInput, KGEdge, KGNode, TreeNode
from kg_workbench.ontology.schema import Ontology
from kg_workbench.utils import to_jsonable, write_json


def _tree_to_dict(node: TreeNode) -> dict[str, Any]:
    data = to_jsonable(node)
    data["children"] = [_tree_to_dict(child) for child in node.children]
    return data


def export_graph_json(
    *,
    output_path: Path,
    document: DocumentInput,
    tree: TreeNode,
    nodes: list[KGNode],
    edges: list[KGEdge],
    review: dict[str, list[dict[str, Any]]],
    ontology: Ontology,
    storage_stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "document": {
            "document_name": document.document_name,
            "document_id": document.document_id,
            "source_path": document.source_path,
        },
        "tree": _tree_to_dict(tree),
        "ontology": {
            "entity_types": sorted(ontology.entity_types),
            "relation_types": sorted(ontology.relation_types),
            "structural_relation_types": sorted(ontology.structural_relation_types),
        },
        "nodes": [to_jsonable(node) for node in nodes],
        "edges": [to_jsonable(edge) for edge in edges],
        "review": review,
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "review_node_count": len(review.get("nodes", [])),
            "review_edge_count": len(review.get("edges", [])),
            **(storage_stats or {}),
        },
    }
    write_json(output_path, payload)
    return payload

