# KG Export Data

Generated graph exports can be published here for the frontend to load:

```bash
conda run -n graphgen python -m kg_workbench.build --config examples/kg_workbench/manifest_tree_kg.yaml
conda run -n graphgen python -m kg_workbench.frontend_data --working-dir cache/kg_workbench --frontend-dir frontend
```

The frontend expects:

- `index.json`
- `<document_id>/graph.json`
