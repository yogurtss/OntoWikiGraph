# KG Workbench

Self-contained Markdown-to-KG workbench. This directory is designed to be moved
to a separate Git repository later.

## Inputs

Single parsed Markdown file:

```bash
python -m kg_workbench.build --input examples/kg_workbench/single_file_tree_kg.md
```

JSON manifest:

```json
{
  "memory-demo": "examples/kg_workbench/single_file_tree_kg.md"
}
```

```bash
python -m kg_workbench.build --input examples/kg_workbench/manifest.json
```

YAML config:

```bash
python -m kg_workbench.build --config examples/kg_workbench/single_file_tree_kg.yaml
```

## LLM Extraction

The default extractor is offline `heuristic`. Use the async OpenAI-compatible
client with:

```bash
python -m kg_workbench.build \
  --config examples/kg_workbench/single_file_tree_kg.yaml \
  --extractor llm \
  --llm-model gpt-4o-mini
```

The client reads `OPENAI_API_KEY` and `OPENAI_BASE_URL` by default. You can also
set `llm.api_key`, `llm.base_url`, and `llm.model` in YAML. `llm.temperature`
is optional, and `extraction.batch_size` controls concurrent LLM posting.

## Outputs

Each Markdown file gets its own graph directory:

```text
cache/kg_workbench/{document_id}/graph_kuzu/
cache/kg_workbench/{document_id}/exports/graph.json
```

Manifest runs also write:

```text
cache/kg_workbench/index.json
```
