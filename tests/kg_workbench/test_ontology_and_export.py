from pathlib import Path

from kg_workbench.models import DocumentInput, KGEdge, KGNode, TreeNode
from kg_workbench.ontology import default_ontology, validate_graph
from kg_workbench.storage import export_graph_json


def test_ontology_validation_routes_unknown_and_missing_evidence_to_review():
    ontology = default_ontology()
    nodes = [
        KGNode(
            id="n1",
            name="LPDDR5X",
            entity_type="memory_product",
            description="A memory product",
            evidence_span="LPDDR5X supports 8533 MT/s",
        ),
        KGNode(
            id="n2",
            name="ghost",
            entity_type="unknown_type",
            description="Invalid",
        ),
    ]
    edges = [
        KGEdge(
            id="e1",
            src="n1",
            tgt="n2",
            relation_type="related_to",
            description="bad endpoint",
            evidence_span="ghost",
        )
    ]

    valid_nodes, valid_edges, review = validate_graph(nodes, edges, ontology)

    assert [node.id for node in valid_nodes] == ["n1"]
    assert valid_edges == []
    assert review["nodes"][0]["review_reasons"] == [
        "unknown_entity_type",
        "missing_evidence",
    ]
    assert "missing_valid_endpoint" in review["edges"][0]["review_reasons"]


def test_export_graph_json_schema(tmp_path: Path):
    document = DocumentInput(
        document_name="demo",
        source_path="/tmp/demo.md",
        content="# demo",
        document_id="doc-demo",
    )
    tree = TreeNode(
        node_id="root",
        title="demo",
        level=0,
        content="",
        node_type="root",
        path="root",
    )
    node = KGNode(
        id="n1",
        name="LPDDR5X",
        entity_type="memory_product",
        description="A memory product",
        evidence_span="LPDDR5X",
        ontology_status="valid",
    )

    payload = export_graph_json(
        output_path=tmp_path / "graph.json",
        document=document,
        tree=tree,
        nodes=[node],
        edges=[],
        review={"nodes": [], "edges": []},
        ontology=default_ontology(),
    )

    assert payload["document"]["document_name"] == "demo"
    assert payload["stats"]["node_count"] == 1
    assert (tmp_path / "graph.json").exists()

