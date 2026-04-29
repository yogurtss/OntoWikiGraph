from __future__ import annotations

import asyncio
import base64
import json
import mimetypes
import re
from pathlib import Path
from typing import Any

from kg_workbench.llm import BaseLLMClient
from kg_workbench.models import DocumentInput, KGEdge, KGNode
from kg_workbench.ontology.schema import Ontology
from kg_workbench.tree.chunker import TreeChunk
from kg_workbench.utils import compact_text, normalize_key, stable_id


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.S)
    return fence.group(1).strip() if fence else stripped


def _parse_json_response(text: str) -> dict[str, Any]:
    try:
        data = json.loads(_strip_json_fence(text))
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM did not return valid JSON: {text[:500]}") from exc
    if not isinstance(data, dict):
        raise ValueError("LLM extraction response must be a JSON object")
    return data


def _prompt_for_chunk(chunk: TreeChunk, ontology: Ontology) -> str:
    modality = chunk.node_type
    grounding_note = (
        "For image/table chunks, use caption, nearby text, table body, asset path, "
        "and visible OCR-like text present in the input as grounding."
        if modality in {"image", "table"}
        else "For text chunks, every node and edge must include a verbatim evidence_span from the chunk."
    )
    return f"""You are building a high-quality ontology-grounded knowledge graph from one parsed Markdown tree chunk.

Return STRICT JSON only. Do not use markdown fences.

Allowed entity_types:
{", ".join(sorted(ontology.entity_types))}

Allowed relation_types:
{", ".join(sorted(ontology.relation_types))}

Rules:
- Extract only entities and relations explicitly supported by the chunk.
- Every entity must have: name, entity_type, description, evidence_span.
- Every edge must have: source, target, relation_type, description, evidence_span, confidence.
- source and target must exactly match extracted entity names.
- Use concise domain-specific entities. Avoid generic words like "system", "method", "result" unless they denote a concrete technical object.
- {grounding_note}
- If an image is provided, use visual evidence from the image itself plus caption/nearby text.

Return schema:
{{
  "nodes": [
    {{"name": "...", "entity_type": "...", "description": "...", "evidence_span": "..."}}
  ],
  "edges": [
    {{"source": "...", "target": "...", "relation_type": "...", "description": "...", "evidence_span": "...", "confidence": 0.0}}
  ]
}}

Tree path: {chunk.tree_path}
Chunk type: {chunk.node_type}
Metadata JSON:
{json.dumps(chunk.metadata, ensure_ascii=False)}

Chunk text:
{chunk.content}
"""


def _image_data_url_from_chunk(chunk: TreeChunk) -> str | None:
    if chunk.node_type != "image":
        return None
    img_path = compact_text(str(chunk.metadata.get("img_path", "")))
    if not img_path:
        return None
    path = Path(img_path)
    if not path.is_file():
        return None
    mime_type, _ = mimetypes.guess_type(path.name)
    if not mime_type:
        mime_type = "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _coerce_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, confidence))


async def extract_llm_candidates(
    doc: DocumentInput,
    chunks: list[TreeChunk],
    *,
    ontology: Ontology,
    llm_client: BaseLLMClient,
) -> tuple[list[KGNode], list[KGEdge]]:
    nodes: list[KGNode] = []
    edges: list[KGEdge] = []

    for chunk in chunks:
        if not compact_text(chunk.content) and chunk.node_type == "text":
            continue
        response = await llm_client.generate(
            _prompt_for_chunk(chunk, ontology),
            image_data_url=_image_data_url_from_chunk(chunk),
        )
        data = _parse_json_response(response)
        raw_nodes = data.get("nodes", [])
        raw_edges = data.get("edges", [])
        if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list):
            raise ValueError("LLM response fields 'nodes' and 'edges' must be lists")

        name_to_id: dict[str, str] = {}
        structural_id = f"tree:{chunk.node_id}"
        for raw_node in raw_nodes:
            if not isinstance(raw_node, dict):
                continue
            name = compact_text(str(raw_node.get("name", "")))
            entity_type = compact_text(str(raw_node.get("entity_type", "")))
            if not name or not entity_type:
                continue
            node_id = stable_id(doc.document_id, entity_type, normalize_key(name), prefix="ent-")
            name_to_id[name] = node_id
            evidence = compact_text(str(raw_node.get("evidence_span", "")))
            nodes.append(
                KGNode(
                    id=node_id,
                    name=name,
                    entity_type=entity_type,
                    description=compact_text(str(raw_node.get("description", ""))),
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
                    confidence=0.9,
                    document_id=doc.document_id,
                    tree_path=chunk.tree_path,
                    source_path=doc.source_path,
                    metadata={"source_node_id": chunk.node_id},
                )
            )

        for raw_edge in raw_edges:
            if not isinstance(raw_edge, dict):
                continue
            src_name = compact_text(str(raw_edge.get("source", "")))
            tgt_name = compact_text(str(raw_edge.get("target", "")))
            src_id = name_to_id.get(src_name)
            tgt_id = name_to_id.get(tgt_name)
            if not src_id or not tgt_id or src_id == tgt_id:
                continue
            relation_type = compact_text(str(raw_edge.get("relation_type", "")))
            evidence = compact_text(str(raw_edge.get("evidence_span", "")))
            edges.append(
                KGEdge(
                    id=stable_id(doc.document_id, src_id, tgt_id, relation_type, chunk.chunk_id, prefix="edge-"),
                    src=src_id,
                    tgt=tgt_id,
                    relation_type=relation_type,
                    description=compact_text(str(raw_edge.get("description", ""))),
                    edge_source="extracted",
                    evidence_span=evidence,
                    evidence_status="grounded" if evidence else "missing",
                    confidence=_coerce_confidence(raw_edge.get("confidence", 0.5)),
                    document_id=doc.document_id,
                    tree_path=chunk.tree_path,
                    source_path=doc.source_path,
                    metadata={"source_chunk_id": chunk.chunk_id},
                )
            )

    return nodes, edges


def extract_candidates_with_llm(
    doc: DocumentInput,
    chunks: list[TreeChunk],
    *,
    ontology: Ontology,
    llm_client: BaseLLMClient,
) -> tuple[list[KGNode], list[KGEdge]]:
    return asyncio.run(
        extract_llm_candidates(
            doc,
            chunks,
            ontology=ontology,
            llm_client=llm_client,
        )
    )
