from __future__ import annotations

from kg_workbench.models import Component, DocumentInput, TreeNode
from kg_workbench.utils import slugify


def _uniq_key(seen: set[str], base: str) -> str:
    base = slugify(base, fallback="node")
    if base not in seen:
        seen.add(base)
        return base
    idx = 1
    while f"{base}_{idx}" in seen:
        idx += 1
    value = f"{base}_{idx}"
    seen.add(value)
    return value


def construct_tree(doc: DocumentInput, components: list[Component]) -> TreeNode:
    root = TreeNode(
        node_id="root",
        title=doc.document_name,
        level=0,
        content="",
        node_type="root",
        path="root",
        metadata={"document_id": doc.document_id, "source_path": doc.source_path},
    )
    stack: list[TreeNode] = [root]
    child_keys: dict[str, set[str]] = {"root": set()}

    for component in components:
        level = max(1, int(component.title_level or 1))
        if component.type == "section":
            while stack and stack[-1].level >= level:
                stack.pop()
            parent = stack[-1] if stack else root
        else:
            parent = stack[-1] if stack else root

        seen = child_keys.setdefault(parent.node_id, set())
        key_seed = component.title if component.type == "section" else component.type
        key = _uniq_key(seen, key_seed)
        node = TreeNode(
            node_id=component.component_id,
            title=component.title,
            level=level,
            content=component.content,
            node_type=component.type,
            path=f"{parent.path}/{key}",
            parent_id=parent.node_id,
            metadata=dict(component.metadata),
        )
        parent.children.append(node)
        child_keys[node.node_id] = set()
        if component.type == "section":
            stack.append(node)

    return root


def iter_tree(root: TreeNode) -> list[TreeNode]:
    nodes: list[TreeNode] = []

    def visit(node: TreeNode) -> None:
        nodes.append(node)
        for child in node.children:
            visit(child)

    visit(root)
    return nodes

