# OntoWikiGraph Frontend

Interactive per-file KG viewer for exported `graph.json` artifacts.

## Development

```bash
conda run -n graphgen npm install --prefix frontend
conda run -n graphgen npm run dev --prefix frontend
```

Or run from this directory:

```bash
npm install
npm run dev
```

## Data

The app first tries to load real exports from:

- `public/kg/index.json`
- `public/kg/<document_id>/graph.json`

If no export index is available, it falls back to built-in mock graphs.

The expected graph payload matches `kg_workbench.storage.exporter.export_graph_json`.

To publish real Kuzu-backed exports into the frontend:

```bash
conda run -n graphgen python -m kg_workbench.build --config examples/kg_workbench/manifest_tree_kg.yaml
conda run -n graphgen python -m kg_workbench.frontend_data --working-dir cache/kg_workbench --frontend-dir frontend
```
