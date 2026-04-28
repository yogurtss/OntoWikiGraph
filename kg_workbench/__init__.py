"""Self-contained KG Workbench for per-Markdown knowledge graph construction."""

from .pipeline import build_document_kg, build_from_input

__all__ = ["build_document_kg", "build_from_input"]

