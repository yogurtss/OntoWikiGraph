from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


NodeKind = Literal["structural", "semantic"]
EdgeSource = Literal["structural", "extracted", "normalized"]


@dataclass
class DocumentInput:
    document_name: str
    source_path: str
    content: str
    document_id: str


@dataclass
class Component:
    component_id: str
    type: str
    title: str
    content: str
    title_level: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TreeNode:
    node_id: str
    title: str
    level: int
    content: str
    node_type: str
    path: str
    parent_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    children: list["TreeNode"] = field(default_factory=list)


@dataclass
class KGNode:
    id: str
    name: str
    entity_type: str
    description: str
    kind: NodeKind = "semantic"
    evidence_span: str = ""
    evidence_status: str = "missing"
    ontology_status: str = "unknown"
    document_id: str = ""
    tree_path: str = ""
    source_path: str = ""
    source_trace_id: str = ""
    modality: str = "text"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class KGEdge:
    id: str
    src: str
    tgt: str
    relation_type: str
    description: str
    edge_source: EdgeSource = "extracted"
    evidence_span: str = ""
    evidence_status: str = "missing"
    ontology_status: str = "unknown"
    confidence: float = 1.0
    document_id: str = ""
    tree_path: str = ""
    source_path: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class KGArtifacts:
    document: DocumentInput
    tree: TreeNode
    nodes: list[KGNode]
    edges: list[KGEdge]
    review: dict[str, list[dict[str, Any]]]

