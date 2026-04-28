from __future__ import annotations

from pathlib import Path

from kg_workbench.models import DocumentInput
from kg_workbench.utils import stable_id


def read_markdown(path: str, document_name: str | None = None) -> DocumentInput:
    md_path = Path(path).expanduser().resolve()
    if md_path.suffix.lower() != ".md":
        raise ValueError(f"Only parsed Markdown input is supported: {md_path}")
    if not md_path.is_file():
        raise FileNotFoundError(md_path)

    name = document_name or md_path.stem
    source_path = str(md_path)
    return DocumentInput(
        document_name=name,
        source_path=source_path,
        content=md_path.read_text(encoding="utf-8"),
        document_id=stable_id(name, source_path, prefix="doc-"),
    )

