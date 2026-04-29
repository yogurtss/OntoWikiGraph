from kg_workbench.extractors.llm import extract_candidates_with_llm
from kg_workbench.llm import BaseLLMClient
from kg_workbench.models import DocumentInput
from kg_workbench.ontology import default_ontology
from kg_workbench.tree.chunker import TreeChunk


class FakeLLM(BaseLLMClient):
    def __init__(self):
        self.last_image_data_url = None

    async def generate(self, prompt: str, *, image_data_url: str | None = None) -> str:
        self.last_image_data_url = image_data_url
        return """
        {
          "nodes": [
            {
              "name": "LPDDR5X",
              "entity_type": "memory_product",
              "description": "A memory product",
              "evidence_span": "LPDDR5X supports 8533 MT/s"
            },
            {
              "name": "8533 MT/s",
              "entity_type": "performance_metric",
              "description": "A data rate",
              "evidence_span": "8533 MT/s"
            }
          ],
          "edges": [
            {
              "source": "LPDDR5X",
              "target": "8533 MT/s",
              "relation_type": "has_bandwidth",
              "description": "LPDDR5X has this data rate",
              "evidence_span": "LPDDR5X supports 8533 MT/s",
              "confidence": 0.98
            }
          ]
        }
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
