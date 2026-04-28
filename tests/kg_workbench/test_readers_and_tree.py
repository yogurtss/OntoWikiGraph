import json
from pathlib import Path

from kg_workbench.readers import read_json_manifest, read_markdown
from kg_workbench.tree import analyze_markdown_structure, chunk_tree_nodes, construct_tree


def test_json_manifest_uses_key_as_document_name(tmp_path: Path):
    md_path = tmp_path / "demo.md"
    md_path.write_text("# Title\n\nLPDDR5X supports 8533 MT/s.", encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps({"paper-a": str(md_path)}),
        encoding="utf-8",
    )

    docs = read_json_manifest(str(manifest_path))

    assert len(docs) == 1
    assert docs[0].document_name == "paper-a"
    assert docs[0].source_path == str(md_path.resolve())
    assert docs[0].document_id.startswith("doc-")


def test_markdown_tree_preserves_sections_and_mm_components(tmp_path: Path):
    md_path = tmp_path / "demo.md"
    md_path.write_text(
        "\n".join(
            [
                "# Root Section",
                "",
                "LPDDR5X supports 8533 MT/s.",
                "",
                "![demo](figures/demo.png)",
                "Figure 1. LPDDR5X channel diagram.",
                "",
                "## Child Section",
                "",
                "<table>",
                "<tr><td>HBM3</td><td>819 GB/s</td></tr>",
                "</table>",
            ]
        ),
        encoding="utf-8",
    )
    doc = read_markdown(str(md_path))

    components = analyze_markdown_structure(doc)
    tree = construct_tree(doc, components)
    chunks = chunk_tree_nodes(tree)

    assert [component.type for component in components] == [
        "section",
        "text",
        "image",
        "section",
        "table",
    ]
    assert tree.children[0].path == "root/Root-Section"
    assert any(chunk.node_type == "image" for chunk in chunks)
    assert any(chunk.node_type == "table" for chunk in chunks)

