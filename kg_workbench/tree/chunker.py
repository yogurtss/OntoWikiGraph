from __future__ import annotations

from dataclasses import dataclass

from kg_workbench.models import TreeNode
from kg_workbench.utils import stable_id

from .constructor import iter_tree


@dataclass
class TreeChunk:
    chunk_id: str
    content: str
    node_type: str
    node_id: str
    parent_id: str | None
    tree_path: str
    level: int
    metadata: dict


def _split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start = max(end - chunk_overlap, start + 1)
    return [chunk for chunk in chunks if chunk]


def chunk_tree_nodes(
    root: TreeNode,
    *,
    split_text_nodes: bool = False,
    chunk_size: int = 1200,
    chunk_overlap: int = 120,
) -> list[TreeChunk]:
    chunks: list[TreeChunk] = []
    for node in iter_tree(root):
        if node.node_type in {"root", "section"}:
            continue
        if not node.content and node.node_type == "text":
            continue
        pieces = (
            _split_text(node.content, chunk_size, chunk_overlap)
            if node.node_type == "text" and split_text_nodes
            else [node.content]
        )
        for index, piece in enumerate(pieces, start=1):
            chunks.append(
                TreeChunk(
                    chunk_id=stable_id(node.node_id, node.path, index, prefix="chk-"),
                    content=piece,
                    node_type=node.node_type,
                    node_id=node.node_id,
                    parent_id=node.parent_id,
                    tree_path=node.path,
                    level=node.level,
                    metadata=dict(node.metadata),
                )
            )
    return chunks

