from __future__ import annotations

import json
from pathlib import Path

from kg_workbench.models import DocumentInput

from .markdown_reader import read_markdown


def read_json_manifest(path: str) -> list[DocumentInput]:
    manifest_path = Path(path).expanduser().resolve()
    if manifest_path.suffix.lower() != ".json":
        raise ValueError(f"Expected a JSON manifest: {manifest_path}")
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON manifest must be an object: {document_name: md_path}")

    documents = []
    for document_name, md_path in data.items():
        if not isinstance(document_name, str) or not document_name.strip():
            raise ValueError("JSON manifest keys must be non-empty document names")
        if not isinstance(md_path, str) or not md_path.strip():
            raise ValueError(f"Manifest path for {document_name!r} must be a string")
        documents.append(read_markdown(md_path, document_name=document_name))
    return documents

