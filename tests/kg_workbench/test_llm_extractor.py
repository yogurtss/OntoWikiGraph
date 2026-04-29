from kg_workbench.extractors.llm import extract_candidates_with_llm
from kg_workbench.llm import BaseLLMClient
from kg_workbench.models import DocumentInput
from kg_workbench.ontology import default_ontology
from kg_workbench.tree.chunker import TreeChunk


class FakeLLM(BaseLLMClient):
    def __init__(self):
        self.last_image_data_url = None
        self.calls: list[str] = []

    async def generate(self, prompt: str, *, image_data_url: str | None = None) -> str:
        self.last_image_data_url = image_data_url
        self.calls.append(prompt)
        if "Stage: entity extraction" in prompt:
            if "BROKEN ENTITY" in prompt:
                raise RuntimeError("entity boom")
            if "BAD EVIDENCE" in prompt:
                return """
("entity"<|>"Ghost Metric"<|>"performance_metric"<|>"Should be rejected"<|>"not in chunk")<|COMPLETE|>
"""
            return """
("entity"<|>"LPDDR5X"<|>"memory_product"<|>"A memory product"<|>"LPDDR5X supports 8533 MT/s")##
("entity"<|>"8533 MT/s"<|>"performance_metric"<|>"A data rate"<|>"8533 MT/s")<|COMPLETE|>
"""

        if "BROKEN RELATION" in prompt:
            raise RuntimeError("relation boom")
        return """
("relationship"<|>"LPDDR5X"<|>"8533 MT/s"<|>"has_bandwidth"<|>"LPDDR5X has this data rate"<|>"LPDDR5X supports 8533 MT/s"<|>0.98)<|COMPLETE|>
"""


def test_llm_extractor_accepts_async_client_without_network():
    doc = DocumentInput("demo", "/tmp/demo.md", "", "doc-demo")
    chunks = [
        TreeChunk(
            chunk_id="chunk-1",
            content="LPDDR5X supports 8533 MT/s.",
            node_type="text",
            node_id="n1",
            parent_id="root",
            tree_path="root/demo",
            level=1,
            metadata={},
        )
    ]

    llm = FakeLLM()
    nodes, edges = extract_candidates_with_llm(
        doc,
        chunks,
        ontology=default_ontology(),
        llm_client=llm,
    )

    assert {node.name for node in nodes} == {"LPDDR5X", "8533 MT/s"}
    assert any(edge.relation_type == "has_bandwidth" for edge in edges)
    assert llm.last_image_data_url is None
    assert any("Stage: entity extraction" in prompt for prompt in llm.calls)
    assert any("Stage: relationship extraction" in prompt for prompt in llm.calls)


def test_llm_extractor_encodes_image_for_image_chunks(tmp_path):
    image_path = tmp_path / "demo.png"
    image_path.write_bytes(b"fake-png-bytes")
    doc = DocumentInput("demo", "/tmp/demo.md", "", "doc-demo")
    chunks = [
        TreeChunk(
            chunk_id="chunk-1",
            content="Figure 1",
            node_type="image",
            node_id="n1",
            parent_id="root",
            tree_path="root/figure",
            level=1,
            metadata={"img_path": str(image_path)},
        )
    ]

    llm = FakeLLM()
    extract_candidates_with_llm(
        doc,
        chunks,
        ontology=default_ontology(),
        llm_client=llm,
    )

    assert llm.last_image_data_url is not None
    assert llm.last_image_data_url.startswith("data:image/png;base64,")


def test_llm_extractor_skips_failed_chunk_without_stopping_batch():
    doc = DocumentInput("demo", "/tmp/demo.md", "", "doc-demo")
    chunks = [
        TreeChunk(
            chunk_id="chunk-1",
            content="LPDDR5X supports 8533 MT/s.",
            node_type="text",
            node_id="n1",
            parent_id="root",
            tree_path="root/demo",
            level=1,
            metadata={},
        ),
        TreeChunk(
            chunk_id="chunk-2",
            content="BROKEN ENTITY",
            node_type="text",
            node_id="n2",
            parent_id="root",
            tree_path="root/broken",
            level=1,
            metadata={},
        ),
    ]

    nodes, edges = extract_candidates_with_llm(
        doc,
        chunks,
        ontology=default_ontology(),
        llm_client=FakeLLM(),
        batch_size=2,
    )

    assert {node.name for node in nodes} == {"LPDDR5X", "8533 MT/s"}
    assert any(edge.relation_type == "has_bandwidth" for edge in edges)


def test_llm_extractor_filters_ungrounded_text_entities():
    doc = DocumentInput("demo", "/tmp/demo.md", "", "doc-demo")
    chunks = [
        TreeChunk(
            chunk_id="chunk-1",
            content="BAD EVIDENCE",
            node_type="text",
            node_id="n1",
            parent_id="root",
            tree_path="root/demo",
            level=1,
            metadata={},
        )
    ]

    nodes, edges = extract_candidates_with_llm(
        doc,
        chunks,
        ontology=default_ontology(),
        llm_client=FakeLLM(),
    )

    assert nodes == []
    assert edges == []


def test_llm_extractor_keeps_entities_when_relation_stage_fails():
    doc = DocumentInput("demo", "/tmp/demo.md", "", "doc-demo")
    chunks = [
        TreeChunk(
            chunk_id="chunk-1",
            content="LPDDR5X supports 8533 MT/s. BROKEN RELATION",
            node_type="text",
            node_id="n1",
            parent_id="root",
            tree_path="root/demo",
            level=1,
            metadata={},
        )
    ]

    nodes, edges = extract_candidates_with_llm(
        doc,
        chunks,
        ontology=default_ontology(),
        llm_client=FakeLLM(),
    )

    assert {node.name for node in nodes} == {"LPDDR5X", "8533 MT/s"}
    assert {edge.relation_type for edge in edges} == {"contains"}
