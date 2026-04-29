from pathlib import Path

from kg_workbench.config import load_config


def test_load_yaml_config(tmp_path: Path):
    config_path = tmp_path / "kg.yaml"
    config_path.write_text(
        """
input: demo.md
working_dir: cache/custom
graph_backend: kuzu
export: json
tree:
  split_text_nodes: true
  split_text_to_paragraphs: true
extraction:
  extractor: llm
llm:
  model: gpt-test
  base_url: http://localhost:8000/v1
  temperature: 0.2
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.input_path == "demo.md"
    assert config.working_dir == "cache/custom"
    assert config.split_text_nodes is True
    assert config.split_text_to_paragraphs is True
    assert config.extractor == "llm"
    assert config.llm_model == "gpt-test"
    assert config.llm_base_url == "http://localhost:8000/v1"
    assert config.llm_temperature == 0.2
