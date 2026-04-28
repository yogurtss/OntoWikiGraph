from __future__ import annotations

import re
from itertools import combinations

from kg_workbench.models import DocumentInput, KGEdge, KGNode
from kg_workbench.tree.chunker import TreeChunk
from kg_workbench.utils import compact_text, normalize_key, stable_id


MEMORY_PRODUCTS = re.compile(
    r"\b(?:LPDDR\dX?|DDR\d|GDDR\dX?|HBM\d?|SRAM|DRAM|NAND|DIMM|MRAM|RRAM)\b",
    re.I,
)
INTERFACE_STANDARDS = re.compile(r"\b(?:PCIe|NVLink|CXL|UCIe|JEDEC|ONFI|NVMe|ECC)\b", re.I)
TIMING_PARAMETERS = re.compile(r"\b(?:tRCD|tRP|tRAS|tWR|tRFC|tREFI|CL|CAS latency)\b", re.I)
PROCESS_TECH = re.compile(r"\b\d+(?:\.\d+)?\s*(?:nm|µm|um)\s*(?:process|node)?\b", re.I)
CAPACITY = re.compile(r"\b\d+(?:\.\d+)?\s*(?:Gb|GB|Tb|TB|Mb|MB)\b")
POWER = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mW|W|pJ/bit|nJ|V)\b", re.I)
PERFORMANCE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:MT/s|GT/s|Gb/s|GB/s|MHz|GHz|ns|ps|%)\b",
    re.I,
)
COMPONENT_WORDS = re.compile(
    r"\b(?:controller|channel|bank|rank|die|base die|PHY|buffer|cache|array|cell|"
    r"wordline|bitline|TSV|interposer|package|interface|decoder|sense amplifier)\b",
    re.I,
)
MATERIAL_WORDS = re.compile(r"\b(?:silicon|copper|oxide|hafnium|carbon|polymer|metal)\b", re.I)


def _sentence_for(text: str, mention: str) -> str:
    for sentence in re.split(r"(?<=[。.!?])\s+|\n+", text):
        if mention.lower() in sentence.lower():
            return compact_text(sentence)[:500]
    return compact_text(text)[:500]


def _find_entities(text: str) -> list[tuple[str, str, str]]:
    patterns = [
        ("memory_product", MEMORY_PRODUCTS),
        ("interface_standard", INTERFACE_STANDARDS),
        ("timing_parameter", TIMING_PARAMETERS),
        ("process_technology", PROCESS_TECH),
        ("capacity_metric", CAPACITY),
        ("power_metric", POWER),
        ("performance_metric", PERFORMANCE),
        ("component", COMPONENT_WORDS),
        ("material", MATERIAL_WORDS),
    ]
    found: dict[str, tuple[str, str, str]] = {}
    for entity_type, pattern in patterns:
        for match in pattern.finditer(text):
            name = compact_text(match.group(0))
            key = normalize_key(f"{entity_type}:{name}")
            found[key] = (name, entity_type, _sentence_for(text, name))
    return list(found.values())


def _edge_relation_for(src_type: str, tgt_type: str) -> str:
    types = {src_type, tgt_type}
    if "timing_parameter" in types:
        return "has_timing"
    if "capacity_metric" in types:
        return "has_capacity"
    if "power_metric" in types:
        return "consumes_power"
    if "performance_metric" in types:
        return "specification_of"
    if "interface_standard" in types:
        return "uses_protocol"
    if "component" in types:
        return "part_of"
    return "related_to"


def extract_candidates(
    doc: DocumentInput,
    chunks: list[TreeChunk],
) -> tuple[list[KGNode], list[KGEdge]]:
    nodes: list[KGNode] = []
    edges: list[KGEdge] = []

    for chunk in chunks:
        text = compact_text(chunk.content)
        if not text:
            continue
        entities = _find_entities(text)
        chunk_entity_ids: list[tuple[str, str]] = []
        structural_id = f"tree:{chunk.node_id}"

        for name, entity_type, evidence in entities:
            node_id = stable_id(doc.document_id, entity_type, normalize_key(name), prefix="ent-")
            chunk_entity_ids.append((node_id, entity_type))
            nodes.append(
                KGNode(
                    id=node_id,
                    name=name,
                    entity_type=entity_type,
                    description=f"{name} mentioned in {chunk.tree_path}",
                    kind="semantic",
                    evidence_span=evidence,
                    evidence_status="grounded" if evidence else "missing",
                    document_id=doc.document_id,
                    tree_path=chunk.tree_path,
                    source_path=doc.source_path,
                    modality=chunk.node_type if chunk.node_type in {"image", "table"} else "text",
                    metadata={"source_node_id": chunk.node_id, **chunk.metadata},
                )
            )
            edges.append(
                KGEdge(
                    id=stable_id(doc.document_id, structural_id, node_id, "contains", prefix="edge-"),
                    src=structural_id,
                    tgt=node_id,
                    relation_type="contains",
                    description=f"{chunk.tree_path} contains mention of {name}",
                    edge_source="extracted",
                    evidence_span=evidence,
                    evidence_status="grounded" if evidence else "missing",
                    confidence=0.85,
                    document_id=doc.document_id,
                    tree_path=chunk.tree_path,
                    source_path=doc.source_path,
                    metadata={"source_node_id": chunk.node_id},
                )
            )

        for (src_id, src_type), (tgt_id, tgt_type) in combinations(chunk_entity_ids[:8], 2):
            relation_type = _edge_relation_for(src_type, tgt_type)
            edges.append(
                KGEdge(
                    id=stable_id(doc.document_id, src_id, tgt_id, relation_type, chunk.chunk_id, prefix="edge-"),
                    src=src_id,
                    tgt=tgt_id,
                    relation_type=relation_type,
                    description=f"{src_type} and {tgt_type} co-occur in {chunk.tree_path}",
                    edge_source="extracted",
                    evidence_span=text[:500],
                    evidence_status="grounded",
                    confidence=0.6,
                    document_id=doc.document_id,
                    tree_path=chunk.tree_path,
                    source_path=doc.source_path,
                    metadata={"source_chunk_id": chunk.chunk_id},
                )
            )

    return nodes, edges

