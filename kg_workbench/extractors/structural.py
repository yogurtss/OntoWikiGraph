from __future__ import annotations

from kg_workbench.models import DocumentInput, KGEdge, KGNode, TreeNode
from kg_workbench.utils import stable_id


def _entity_type_for_node(node: TreeNode) -> str:
    if node.node_type == "image":
        return "IMAGE"
    if node.node_type == "table":
        return "TABLE"
    if node.node_type == "formula":
        return "FORMULA"
    if node.node_type == "video":
        return "VIDEO"
    return "component"


def _modality_for_node(node: TreeNode) -> str:
    return node.node_type if node.node_type in {"image", "table", "formula", "video"} else "text"


def _grounding_for_node(node: TreeNode) -> tuple[str, str]:
    if node.node_type == "image":
        captions = node.metadata.get("image_caption") or []
        if isinstance(captions, list) and captions:
            return "\n".join(str(item) for item in captions), "asset_grounded"
        if node.metadata.get("img_path"):
            return str(node.metadata["img_path"]), "asset_grounded"
    if node.node_type == "table":
        captions = node.metadata.get("table_caption") or []
        body = node.metadata.get("table_body", "")
        evidence = "\n".join(str(item) for item in captions if item)
        if not evidence:
            evidence = str(body)[:500]
        return evidence, "asset_grounded" if evidence else "missing"
    if node.content:
        return node.content[:500], "grounded"
    return node.title, "grounded"


def _walk(node: TreeNode) -> list[TreeNode]:
    nodes = [node]
    for child in node.children:
        nodes.extend(_walk(child))
    return nodes


def add_structural_kg(doc: DocumentInput, root: TreeNode) -> tuple[list[KGNode], list[KGEdge]]:
    nodes: list[KGNode] = []
    edges: list[KGEdge] = []
    tree_nodes = _walk(root)
    structural_ids: dict[str, str] = {}

    for node in tree_nodes:
        kg_id = f"tree:{node.node_id}"
        structural_ids[node.node_id] = kg_id
        evidence, evidence_status = _grounding_for_node(node)
        nodes.append(
            KGNode(
                id=kg_id,
                name=node.title if node.node_type in {"root", "section"} else f"{node.node_type}:{node.path}",
                entity_type=_entity_type_for_node(node),
                description=f"{node.node_type} node at {node.path}",
                kind="structural",
                evidence_span=evidence,
                evidence_status=evidence_status,
                ontology_status="valid",
                document_id=doc.document_id,
                tree_path=node.path,
                source_path=doc.source_path,
                modality=_modality_for_node(node),
                metadata=dict(node.metadata),
            )
        )

    for node in tree_nodes:
        parent_kg_id = structural_ids.get(node.node_id)
        for index, child in enumerate(node.children):
            child_kg_id = structural_ids[child.node_id]
            edges.append(
                KGEdge(
                    id=stable_id(doc.document_id, parent_kg_id, child_kg_id, "parent_of", prefix="edge-"),
                    src=parent_kg_id,
                    tgt=child_kg_id,
                    relation_type="parent_of",
                    description=f"{node.path} is the parent of {child.path}",
                    edge_source="structural",
                    evidence_status="structural",
                    ontology_status="valid",
                    document_id=doc.document_id,
                    tree_path=node.path,
                    source_path=doc.source_path,
                )
            )
            edges.append(
                KGEdge(
                    id=stable_id(doc.document_id, parent_kg_id, child_kg_id, "contains", prefix="edge-"),
                    src=parent_kg_id,
                    tgt=child_kg_id,
                    relation_type="contains",
                    description=f"{node.path} contains {child.path}",
                    edge_source="structural",
                    evidence_status="structural",
                    ontology_status="valid",
                    document_id=doc.document_id,
                    tree_path=node.path,
                    source_path=doc.source_path,
                )
            )
            if index + 1 < len(node.children):
                next_child = node.children[index + 1]
                edges.append(
                    KGEdge(
                        id=stable_id(
                            doc.document_id,
                            child_kg_id,
                            structural_ids[next_child.node_id],
                            "next_sibling",
                            prefix="edge-",
                        ),
                        src=child_kg_id,
                        tgt=structural_ids[next_child.node_id],
                        relation_type="next_sibling",
                        description=f"{next_child.path} follows {child.path}",
                        edge_source="structural",
                        evidence_status="structural",
                        ontology_status="valid",
                        document_id=doc.document_id,
                        tree_path=node.path,
                        source_path=doc.source_path,
                    )
                )
    return nodes, edges

