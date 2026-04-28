# OntoWikiGraph

OntoWikiGraph is a self-contained Markdown-to-KG workbench for building
ontology-grounded, per-document knowledge graphs. The project is designed around
layered knowledge assets:

1. Raw file layer: parsed Markdown documents and manifests.
2. KG layer: tree-aware, ontology-validated knowledge graphs.
3. Wiki layer: future entity-centric wiki pages that can reconcile multiple
   documents' views of the same entity.

## Quick Start

```bash
python -m kg_workbench.build --config examples/kg_workbench/single_file_tree_kg.yaml
```

Use LLM extraction with an OpenAI-compatible API:

```bash
python -m kg_workbench.build \
  --config examples/kg_workbench/single_file_tree_kg.yaml \
  --extractor llm \
  --llm-model gpt-4o-mini
```

The async LLM client reads `OPENAI_API_KEY` and `OPENAI_BASE_URL` by default.
