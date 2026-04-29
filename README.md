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
`llm.temperature` is optional, and `extraction.batch_size` controls concurrent
LLM posting per chunk batch.

## Frontend Usage

The repository also includes a frontend KG viewer under [frontend](/home/lukashe/data/projects/OntoWikiGraph/frontend).

Install and start the frontend:

```bash
conda run -n graphgen npm install --prefix frontend
conda run -n graphgen npm run dev --prefix frontend
```

Or run directly inside `frontend/`:

```bash
npm install
npm run dev
```

Open the local Vite URL shown in the terminal, usually `http://localhost:5173`.

The frontend now supports:

- importing a local absolute `index.json` path from the sidebar while running
  the Vite dev or preview server
- current-graph node-name search with click-to-focus
- an automatic large-graph mode that reduces layout and label cost for dense
  graphs

### View Real Graph Data

The frontend looks for exported graph files in:

- `frontend/public/kg/index.json`
- `frontend/public/kg/<document_id>/graph.json`

If these files do not exist yet, the UI falls back to built-in mock data.

To generate real graph data from the KG pipeline and publish it into the frontend:

```bash
conda run -n graphgen python -m kg_workbench.build --config examples/kg_workbench/manifest_tree_kg.yaml
conda run -n graphgen python -m kg_workbench.frontend_data --working-dir cache/kg_workbench --frontend-dir frontend
```

After that, restart or refresh the frontend and it will load the exported graphs.

If you want to inspect a local cache directory directly instead of publishing it
into `frontend/public/kg`, start the frontend dev server and paste an absolute
`index.json` path into the sidebar import box, for example
`/home/.../cache/kg_workbench/index.json`.
