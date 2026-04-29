from __future__ import annotations

from pathlib import Path
from typing import Any

from kg_workbench.extractors import (
    add_structural_kg,
    extract_candidates,
    extract_candidates_with_llm,
)
from kg_workbench.config import WorkbenchConfig
from kg_workbench.llm import LLMConfig, OpenAICompatibleClient
from kg_workbench.models import DocumentInput
from kg_workbench.normalization import normalize_and_cluster
from kg_workbench.ontology import default_ontology, validate_graph
from kg_workbench.readers import read_json_manifest, read_markdown
from kg_workbench.storage import KuzuGraphStore, export_graph_json
from kg_workbench.tree import analyze_markdown_structure, chunk_tree_nodes, construct_tree
from kg_workbench.utils import write_json


def _document_dir(working_dir: Path, document: DocumentInput) -> Path:
    return working_dir / document.document_id


def build_document_kg(
    document: DocumentInput,
    *,
    working_dir: str | Path = "cache/kg_workbench",
    graph_backend: str = "kuzu",
    export: str = "json",
    split_text_nodes: bool = False,
    split_text_to_paragraphs: bool = False,
    extractor: str = "heuristic",
    llm_model: str | None = None,
    llm_api_key: str | None = None,
    llm_base_url: str | None = None,
    llm_temperature: float = 0.0,
) -> dict[str, Any]:
    working_dir = Path(working_dir)
    ontology = default_ontology()

    components = analyze_markdown_structure(document)
    tree = construct_tree(document, components)
    chunks = chunk_tree_nodes(
        tree,
        split_text_nodes=split_text_nodes,
        split_text_to_paragraphs=split_text_to_paragraphs,
    )

    structural_nodes, structural_edges = add_structural_kg(document, tree)
    if extractor == "heuristic":
        extracted_nodes, extracted_edges = extract_candidates(document, chunks)
    elif extractor == "llm":
        if not llm_model:
            raise ValueError("--llm-model is required when extractor='llm'")
        llm_client = OpenAICompatibleClient(
            LLMConfig(
                model=llm_model,
                api_key=llm_api_key,
                base_url=llm_base_url,
                temperature=llm_temperature,
            )
        )
        extracted_nodes, extracted_edges = extract_candidates_with_llm(
            document,
            chunks,
            ontology=ontology,
            llm_client=llm_client,
        )
    else:
        raise ValueError("extractor must be 'heuristic' or 'llm'")
    nodes, edges = normalize_and_cluster(
        structural_nodes + extracted_nodes,
        structural_edges + extracted_edges,
    )
    valid_nodes, valid_edges, review = validate_graph(nodes, edges, ontology)

    document_dir = _document_dir(working_dir, document)
    storage_stats: dict[str, Any] = {}
    if graph_backend != "kuzu":
        raise ValueError("v1 supports only graph_backend='kuzu'")
    store = KuzuGraphStore(document_dir / "graph_kuzu")
    storage_stats = store.persist(valid_nodes, valid_edges)

    if export != "json":
        raise ValueError("v1 supports only export='json'")
    export_path = document_dir / "exports" / "graph.json"
    payload = export_graph_json(
        output_path=export_path,
        document=document,
        tree=tree,
        nodes=valid_nodes,
        edges=valid_edges,
        review=review,
        ontology=ontology,
        storage_stats=storage_stats,
    )
    payload["export_path"] = str(export_path)
    return payload


def load_documents(input_path: str) -> list[DocumentInput]:
    path = Path(input_path).expanduser().resolve()
    suffix = path.suffix.lower()
    if suffix == ".md":
        return [read_markdown(str(path))]
    if suffix == ".json":
        return read_json_manifest(str(path))
    raise ValueError("Input must be a parsed Markdown file or JSON manifest")


def build_from_input(
    input_path: str,
    *,
    working_dir: str | Path = "cache/kg_workbench",
    graph_backend: str = "kuzu",
    export: str = "json",
    split_text_nodes: bool = False,
    split_text_to_paragraphs: bool = False,
    extractor: str = "heuristic",
    llm_model: str | None = None,
    llm_api_key: str | None = None,
    llm_base_url: str | None = None,
    llm_temperature: float = 0.0,
) -> list[dict[str, Any]]:
    documents = load_documents(input_path)
    results = [
        build_document_kg(
            document,
            working_dir=working_dir,
            graph_backend=graph_backend,
            export=export,
            split_text_nodes=split_text_nodes,
            split_text_to_paragraphs=split_text_to_paragraphs,
            extractor=extractor,
            llm_model=llm_model,
            llm_api_key=llm_api_key,
            llm_base_url=llm_base_url,
            llm_temperature=llm_temperature,
        )
        for document in documents
    ]

    if len(documents) > 1:
        index = {
            result["document"]["document_name"]: {
                "document_id": result["document"]["document_id"],
                "source_path": result["document"]["source_path"],
                "export_path": result["export_path"],
            }
            for result in results
        }
        write_json(Path(working_dir) / "index.json", index)

    return results


def build_from_config(config: WorkbenchConfig) -> list[dict[str, Any]]:
    return build_from_input(
        config.input_path,
        working_dir=config.working_dir,
        graph_backend=config.graph_backend,
        export=config.export,
        split_text_nodes=config.split_text_nodes,
        split_text_to_paragraphs=config.split_text_to_paragraphs,
        extractor=config.extractor,
        llm_model=config.llm_model,
        llm_api_key=config.llm_api_key,
        llm_base_url=config.llm_base_url,
        llm_temperature=config.llm_temperature,
    )
