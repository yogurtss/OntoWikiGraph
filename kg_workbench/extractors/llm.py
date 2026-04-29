from __future__ import annotations

import asyncio
import base64
import mimetypes
import re
from pathlib import Path
from unicodedata import normalize as unicode_normalize
from typing import Any

from kg_workbench.llm import BaseLLMClient
from kg_workbench.models import DocumentInput, KGEdge, KGNode
from kg_workbench.ontology.schema import Ontology
from kg_workbench.tree.chunker import TreeChunk
from kg_workbench.utils import compact_text, normalize_key, stable_id


DEFAULT_LLM_BATCH_SIZE = 16
TUPLE_DELIMITER = "<|>"
RECORD_DELIMITER = "##"
COMPLETION_DELIMITER = "<|COMPLETE|>"


def _contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", text or ""))


def _escape_prompt_value(value: str) -> str:
    return str(value).replace("{", "{{").replace("}", "}}")


def _normalize_text_for_match(text: str) -> str:
    normalized = unicode_normalize("NFKC", compact_text(text or ""))
    normalized = re.sub(r"\s+", " ", normalized).strip().lower()
    return normalized


def _evidence_supported_by_text(evidence_span: str, source_text: str) -> bool:
    evidence = _normalize_text_for_match(evidence_span)
    source = _normalize_text_for_match(source_text)
    return bool(evidence and source and evidence in source)


def _allowed_relation_types(ontology: Ontology) -> list[str]:
    return sorted(ontology.relation_types.difference(ontology.structural_relation_types))


def _entity_prompt_for_chunk(chunk: TreeChunk, ontology: Ontology) -> str:
    language = "Chinese" if _contains_cjk(chunk.content) else "English"
    grounding_note = (
        "For image/table chunks, use visual/table evidence plus caption, nearby text, asset path, and OCR-like text."
        if chunk.node_type in {"image", "table"}
        else "For text chunks, every entity must include a short verbatim evidence_span copied from the chunk text."
    )
    strict_note = (
        "For text chunks, do not output any entity unless the evidence_span is directly supported by the chunk text."
        if chunk.node_type == "text"
        else "If a visual-only entity is supported by the image/table context, it may omit exact text matching."
    )
    return f"""You are an ontology-grounded entity extraction expert for semiconductor memory technical documents.

Stage: entity extraction
Output language: {language}

Return records only. Do not return JSON, markdown, or prose.
Protocol:
- tuple delimiter: {TUPLE_DELIMITER}
- record delimiter: {RECORD_DELIMITER}
- completion delimiter: {COMPLETION_DELIMITER}

Allowed entity_types:
{", ".join(sorted(ontology.entity_types))}

Rules:
- Extract only concrete entities explicitly supported by the chunk.
- Prefer technical entities such as memory products, standards, components, substructures, timing parameters, metrics, operating conditions, process technologies, materials, signals, test methods, failure modes, and organizations.
- Avoid generic discourse words like system, method, result, device unless they denote a concrete technical object in the chunk.
- Keep entity names faithful to the source wording.
- Each record must use exactly 5 fields.
- {grounding_note}
- {strict_note}

Entity record format:
("entity"{TUPLE_DELIMITER}"entity_name"{TUPLE_DELIMITER}"entity_type"{TUPLE_DELIMITER}"entity_summary"{TUPLE_DELIMITER}"evidence_span")

Example:
("entity"{TUPLE_DELIMITER}"LPDDR5X"{TUPLE_DELIMITER}"memory_product"{TUPLE_DELIMITER}"LPDDR5X is the memory product described in this chunk."{TUPLE_DELIMITER}"LPDDR5X supports 8533 MT/s"){RECORD_DELIMITER}
("entity"{TUPLE_DELIMITER}"8533 MT/s"{TUPLE_DELIMITER}"performance_metric"{TUPLE_DELIMITER}"8533 MT/s is the reported data-rate metric."{TUPLE_DELIMITER}"8533 MT/s"){COMPLETION_DELIMITER}

Chunk path: {_escape_prompt_value(chunk.tree_path)}
Chunk type: {_escape_prompt_value(chunk.node_type)}
Chunk metadata: {_escape_prompt_value(str(chunk.metadata))}
Chunk text:
{chunk.content}

Output:
"""


def _relation_prompt_for_chunk(chunk: TreeChunk, ontology: Ontology, entity_names: list[str]) -> str:
    language = "Chinese" if _contains_cjk(chunk.content) else "English"
    entity_list = "\n".join(f"- {name}" for name in entity_names) or "- (none)"
    grounding_note = (
        "For image/table chunks, use visual/table evidence plus caption, nearby text, asset path, and OCR-like text."
        if chunk.node_type in {"image", "table"}
        else "For text chunks, every relationship must include a verbatim evidence_span copied from the chunk text."
    )
    strict_note = (
        "Strict triplet grounding for text chunks: only output a relationship when source entity, target entity, and relation are each directly supported by the chunk text."
        if chunk.node_type == "text"
        else "Only output relationships that are clearly grounded in the provided multimodal context."
    )
    return f"""You are an ontology-grounded relationship extraction expert for semiconductor memory technical documents.

Stage: relationship extraction
Output language: {language}

Return records only. Do not return JSON, markdown, or prose.
Protocol:
- tuple delimiter: {TUPLE_DELIMITER}
- record delimiter: {RECORD_DELIMITER}
- completion delimiter: {COMPLETION_DELIMITER}

Allowed relation_types:
{", ".join(_allowed_relation_types(ontology))}

Validated entities for this chunk:
{entity_list}

Rules:
- Only use source and target names from the validated entity list above.
- Extract only technically meaningful, explicit relations grounded in the chunk.
- Do not invent relationships or rely on background knowledge.
- Each record must use exactly 7 fields.
- {grounding_note}
- {strict_note}

Relationship record format:
("relationship"{TUPLE_DELIMITER}"source_entity"{TUPLE_DELIMITER}"target_entity"{TUPLE_DELIMITER}"relation_type"{TUPLE_DELIMITER}"relationship_summary"{TUPLE_DELIMITER}"evidence_span"{TUPLE_DELIMITER}0.95)

Example:
("relationship"{TUPLE_DELIMITER}"LPDDR5X"{TUPLE_DELIMITER}"8533 MT/s"{TUPLE_DELIMITER}"has_bandwidth"{TUPLE_DELIMITER}"The text gives 8533 MT/s as a data-rate metric for LPDDR5X."{TUPLE_DELIMITER}"LPDDR5X supports 8533 MT/s"{TUPLE_DELIMITER}0.98){COMPLETION_DELIMITER}

Chunk path: {_escape_prompt_value(chunk.tree_path)}
Chunk type: {_escape_prompt_value(chunk.node_type)}
Chunk metadata: {_escape_prompt_value(str(chunk.metadata))}
Chunk text:
{chunk.content}

Output:
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


def _canonical_lookup(values: frozenset[str]) -> dict[str, str]:
    return {normalize_key(value): value for value in values}


def _strip_wrapping_quotes(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {'"', "'"}:
        stripped = stripped[1:-1]
    return compact_text(stripped)


def _protocol_records(text: str) -> list[str]:
    return [
        record.strip()
        for record in re.split(
            f"{re.escape(RECORD_DELIMITER)}|{re.escape(COMPLETION_DELIMITER)}",
            compact_text(text),
        )
        if record.strip()
    ]


def _record_fields(record: str) -> list[str] | None:
    match = re.search(r"\((.*)\)", record, re.S)
    if not match:
        return None
    inner = match.group(1).strip()
    return [_strip_wrapping_quotes(part) for part in inner.split(TUPLE_DELIMITER)]


def _entity_from_fields(
    fields: list[str],
    *,
    doc: DocumentInput,
    chunk: TreeChunk,
    entity_type_lookup: dict[str, str],
) -> KGNode | None:
    if len(fields) != 5 or normalize_key(fields[0]) != "entity":
        return None

    name = compact_text(fields[1])
    canonical_entity_type = entity_type_lookup.get(normalize_key(fields[2]))
    description = compact_text(fields[3])
    evidence = compact_text(fields[4])
    is_text_chunk = chunk.node_type == "text"
    if not name or not canonical_entity_type:
        return None
    if is_text_chunk:
        if not evidence or not _evidence_supported_by_text(evidence, chunk.content):
            return None

    node_id = stable_id(doc.document_id, canonical_entity_type, normalize_key(name), prefix="ent-")
    return KGNode(
        id=node_id,
        name=name,
        entity_type=canonical_entity_type,
        description=description,
        kind="semantic",
        evidence_span=evidence,
        evidence_status="grounded" if evidence else "missing",
        document_id=doc.document_id,
        tree_path=chunk.tree_path,
        source_path=doc.source_path,
        modality=chunk.node_type if chunk.node_type in {"image", "table"} else "text",
        metadata={"source_node_id": chunk.node_id, **chunk.metadata},
    )


def _contains_edge_for_node(doc: DocumentInput, chunk: TreeChunk, node: KGNode) -> KGEdge:
    structural_id = f"tree:{chunk.node_id}"
    return KGEdge(
        id=stable_id(doc.document_id, structural_id, node.id, "contains", prefix="edge-"),
        src=structural_id,
        tgt=node.id,
        relation_type="contains",
        description=f"{chunk.tree_path} contains mention of {node.name}",
        edge_source="extracted",
        evidence_span=node.evidence_span,
        evidence_status=node.evidence_status,
        confidence=0.9,
        document_id=doc.document_id,
        tree_path=chunk.tree_path,
        source_path=doc.source_path,
        metadata={"source_node_id": chunk.node_id},
    )


def _edge_from_fields(
    fields: list[str],
    *,
    doc: DocumentInput,
    chunk: TreeChunk,
    relation_type_lookup: dict[str, str],
    entity_by_key: dict[str, KGNode],
) -> KGEdge | None:
    if len(fields) != 7 or normalize_key(fields[0]) != "relationship":
        return None

    src_name = compact_text(fields[1])
    tgt_name = compact_text(fields[2])
    canonical_relation_type = relation_type_lookup.get(normalize_key(fields[3]))
    description = compact_text(fields[4])
    evidence = compact_text(fields[5])
    src_node = entity_by_key.get(normalize_key(src_name))
    tgt_node = entity_by_key.get(normalize_key(tgt_name))
    if not src_node or not tgt_node or src_node.id == tgt_node.id or not canonical_relation_type:
        return None
    if chunk.node_type == "text":
        if not evidence or not _evidence_supported_by_text(evidence, chunk.content):
            return None
    elif not evidence:
        return None

    return KGEdge(
        id=stable_id(doc.document_id, src_node.id, tgt_node.id, canonical_relation_type, chunk.chunk_id, prefix="edge-"),
        src=src_node.id,
        tgt=tgt_node.id,
        relation_type=canonical_relation_type,
        description=description,
        edge_source="extracted",
        evidence_span=evidence,
        evidence_status="grounded" if evidence else "missing",
        confidence=_coerce_confidence(fields[6]),
        document_id=doc.document_id,
        tree_path=chunk.tree_path,
        source_path=doc.source_path,
        metadata={"source_chunk_id": chunk.chunk_id},
    )


async def extract_llm_candidates(
    doc: DocumentInput,
    chunks: list[TreeChunk],
    *,
    ontology: Ontology,
    llm_client: BaseLLMClient,
    batch_size: int = DEFAULT_LLM_BATCH_SIZE,
) -> tuple[list[KGNode], list[KGEdge]]:
    nodes: list[KGNode] = []
    edges: list[KGEdge] = []
    entity_type_lookup = _canonical_lookup(ontology.entity_types)
    relation_type_lookup = _canonical_lookup(ontology.relation_types)

    async def _extract_one(chunk: TreeChunk, chunk_index: int, total_chunks: int) -> tuple[list[KGNode], list[KGEdge]]:
        if not compact_text(chunk.content) and chunk.node_type == "text":
            print(
                f"[llm-extract] chunk {chunk_index}/{total_chunks} skipped: empty text chunk "
                f"(id={chunk.chunk_id}, path={chunk.tree_path})"
            )
            return [], []

        print(f"[llm-extract] chunk {chunk_index}/{total_chunks} start (id={chunk.chunk_id}, type={chunk.node_type})")
        chunk_nodes: list[KGNode] = []
        chunk_edges: list[KGEdge] = []
        image_data_url = _image_data_url_from_chunk(chunk)
        try:
            entity_response = await llm_client.generate(
                _entity_prompt_for_chunk(chunk, ontology),
                image_data_url=image_data_url,
            )
        except Exception as exc:
            print(f"[llm-extract] chunk {chunk_index}/{total_chunks} entity stage failed: {exc}")
            return [], []

        for record in _protocol_records(entity_response):
            fields = _record_fields(record)
            if not fields:
                continue
            node = _entity_from_fields(
                fields,
                doc=doc,
                chunk=chunk,
                entity_type_lookup=entity_type_lookup,
            )
            if node is None:
                continue
            chunk_nodes.append(node)
            chunk_edges.append(_contains_edge_for_node(doc, chunk, node))

        entity_by_key = {normalize_key(node.name): node for node in chunk_nodes}
        if entity_by_key:
            try:
                relation_response = await llm_client.generate(
                    _relation_prompt_for_chunk(chunk, ontology, [node.name for node in chunk_nodes]),
                    image_data_url=image_data_url,
                )
            except Exception as exc:
                print(f"[llm-extract] chunk {chunk_index}/{total_chunks} relation stage failed: {exc}")
                relation_response = ""

            for record in _protocol_records(relation_response):
                fields = _record_fields(record)
                if not fields:
                    continue
                edge = _edge_from_fields(
                    fields,
                    doc=doc,
                    chunk=chunk,
                    relation_type_lookup=relation_type_lookup,
                    entity_by_key=entity_by_key,
                )
                if edge is not None:
                    chunk_edges.append(edge)

        node_preview = ", ".join(node.name for node in chunk_nodes[:3])
        edge_preview = ", ".join(edge.relation_type for edge in chunk_edges[:3])
        print(
            f"[llm-extract] chunk {chunk_index}/{total_chunks} done: "
            f"nodes={len(chunk_nodes)} ({node_preview or '-'}) "
            f"edges={len(chunk_edges)} ({edge_preview or '-'})"
        )
        return chunk_nodes, chunk_edges

    total_chunks = len(chunks)
    effective_batch_size = max(1, int(batch_size))
    print(f"[llm-extract] start: total_chunks={total_chunks}, batch_size={effective_batch_size}")
    for batch_start in range(0, total_chunks, effective_batch_size):
        batch_end = min(total_chunks, batch_start + effective_batch_size)
        print(f"[llm-extract] posting batch {batch_start + 1}-{batch_end}/{total_chunks}")
        batch_results = await asyncio.gather(
            *[
                _extract_one(chunk, chunk_index, total_chunks)
                for chunk_index, chunk in enumerate(chunks[batch_start:batch_end], start=batch_start + 1)
            ],
            return_exceptions=True,
        )
        for result in batch_results:
            if isinstance(result, Exception):
                print(f"[llm-extract] batch task failed unexpectedly: {result}")
                continue
            batch_nodes, batch_edges = result
            nodes.extend(batch_nodes)
            edges.extend(batch_edges)

    print(f"[llm-extract] finished: total_nodes={len(nodes)}, total_edges={len(edges)}")

    return nodes, edges


def extract_candidates_with_llm(
    doc: DocumentInput,
    chunks: list[TreeChunk],
    *,
    ontology: Ontology,
    llm_client: BaseLLMClient,
    batch_size: int = DEFAULT_LLM_BATCH_SIZE,
) -> tuple[list[KGNode], list[KGEdge]]:
    return asyncio.run(
        extract_llm_candidates(
            doc,
            chunks,
            ontology=ontology,
            llm_client=llm_client,
            batch_size=batch_size,
        )
    )
