# KG Build Pipeline

This document summarizes the current KG construction flow implemented in
`kg_workbench`. The pipeline builds one ontology-grounded knowledge graph per
parsed Markdown document, stores it in Kuzu, and exports a JSON artifact for
inspection or downstream UI use.

## Directory Layout

```text
kg_workbench/
  build.py                 # CLI entry point
  pipeline.py              # End-to-end orchestration
  config.py                # YAML/CLI config model
  readers/                 # Markdown and manifest readers
  tree/                    # Markdown structure analysis, tree building, chunking
  extractors/              # Structural, heuristic, and LLM extraction
  normalization/           # Entity clustering and edge deduplication
  ontology/                # Default ontology and validation
  storage/                 # Kuzu persistence and JSON export

examples/kg_workbench/     # Runnable example inputs and configs
cache/kg_workbench/        # Default generated KG outputs
docs/kg_workbench/         # KG workbench documentation
```

Generated files are intentionally kept under `cache/kg_workbench/` by default,
so source code, examples, and documentation stay separate from build artifacts.

## Entry Points

The main CLI entry point is:

```bash
python -m kg_workbench.build --config examples/kg_workbench/single_file_tree_kg.yaml
```

The CLI accepts either a YAML config or a direct input path:

```bash
python -m kg_workbench.build --input examples/kg_workbench/single_file_tree_kg.md
python -m kg_workbench.build --input examples/kg_workbench/manifest.json
```

For LLM extraction, pass `--extractor llm` and a model:

```bash
python -m kg_workbench.build \
  --config examples/kg_workbench/single_file_tree_kg.yaml \
  --extractor llm \
  --llm-model gpt-4o-mini
```

The OpenAI-compatible client reads `OPENAI_API_KEY` and `OPENAI_BASE_URL` by
default, unless those values are provided in YAML or CLI flags.

## Configuration

The current config surface is represented by `WorkbenchConfig` in
`kg_workbench/config.py`.

```yaml
input: examples/kg_workbench/single_file_tree_kg.md
working_dir: cache/kg_workbench
graph_backend: kuzu
export: json

tree:
  split_text_nodes: false

extraction:
  extractor: heuristic

llm:
  model: gpt-4o-mini
  base_url: null
  api_key: null
  temperature: 0.0
```

Supported values in the current v1 implementation:

- `input`: required; a parsed Markdown file (`.md`) or JSON manifest (`.json`).
- `working_dir`: output root, defaulting to `cache/kg_workbench`.
- `graph_backend`: currently only `kuzu`.
- `export`: currently only `json`.
- `tree.split_text_nodes`: whether long text nodes are split into overlapping
  chunks before semantic extraction.
- `extraction.extractor`: `heuristic` for offline extraction or `llm` for
  OpenAI-compatible extraction.
- `llm.*`: model and client settings used only by the LLM extractor.

## Input Loading

Implemented in `kg_workbench/pipeline.py`, `kg_workbench/readers/markdown_reader.py`,
and `kg_workbench/readers/json_manifest_reader.py`.

1. `build.py` loads a `WorkbenchConfig` from YAML or creates one from `--input`.
2. `build_from_config()` forwards the config into `build_from_input()`.
3. `load_documents()` resolves the input type:
   - `.md`: `read_markdown()` returns one `DocumentInput`.
   - `.json`: `read_json_manifest()` expects `{document_name: md_path}` and
     returns one `DocumentInput` per manifest entry.
4. Each document gets a stable `document_id` from its name and source path.

## Markdown Structure Analysis

Implemented in `kg_workbench/tree/markdown.py`.

The parser converts Markdown text into ordered `Component` objects:

- `section`: title-like lines, including Markdown headings, numeric headings,
  and Chinese chapter/section headings.
- `text`: paragraph blocks under the current title.
- `table`: HTML table blocks, plus nearby table captions when detected.
- `image`: Markdown or HTML image references, plus image captions and notes.

The parser preserves source grounding in component metadata where possible, such
as `img_path`, `image_caption`, `table_body`, `table_caption`, and `note_text`.

## Tree Construction

Implemented in `kg_workbench/tree/constructor.py`.

`construct_tree()` turns the flat component sequence into a hierarchical
`TreeNode` tree:

1. Create a root node for the document.
2. Use inferred title levels to attach `section` nodes to the correct parent.
3. Attach non-section components to the current section.
4. Build stable, readable `tree_path` values such as
   `root/introduction/text`.

This tree is the backbone that keeps semantic entities connected to their
document context.

## Chunking

Implemented in `kg_workbench/tree/chunker.py`.

`chunk_tree_nodes()` walks the tree and emits `TreeChunk` objects for extractable
content:

- `root` and `section` nodes are skipped because they organize context.
- `text`, `table`, and `image` content become chunks.
- If `split_text_nodes` is enabled, long text nodes are split with the current
  defaults of `chunk_size=1200` and `chunk_overlap=120`.
- Each chunk carries `node_id`, `parent_id`, `tree_path`, `node_type`, level,
  content, and metadata.

## Structural KG Construction

Implemented in `kg_workbench/extractors/structural.py`.

`add_structural_kg()` creates KG nodes and edges directly from the document tree:

- Every tree node becomes a structural `KGNode` with an id shaped like
  `tree:{node_id}`.
- Structural node entity types include `IMAGE`, `TABLE`, `FORMULA`, `VIDEO`, or
  generic `component`.
- Evidence is grounded from text content, captions, table bodies, or asset paths.
- Tree edges are emitted as:
  - `parent_of`
  - `contains`
  - `next_sibling`

These structural nodes and edges make the final graph navigable even before
semantic extraction runs.

## Semantic Extraction

Implemented in `kg_workbench/extractors/heuristic.py` and
`kg_workbench/extractors/llm.py`.

The pipeline supports two extraction modes.

### Heuristic Extraction

`extract_candidates()` uses regex patterns to find memory-domain entities such
as memory products, interface standards, timing parameters, process
technologies, capacity metrics, power metrics, performance metrics, components,
and materials.

For each chunk:

1. Matched mentions become semantic `KGNode` objects.
2. The source structural node gets a `contains` edge to each semantic node.
3. Co-occurring entities in the chunk are connected with relation types inferred
   from their entity types, such as `has_timing`, `has_capacity`,
   `consumes_power`, `uses_protocol`, `part_of`, or `related_to`.

This mode is offline, deterministic, and the default.

### LLM Extraction

`extract_candidates_with_llm()` sends each chunk to an OpenAI-compatible client
with the default ontology embedded in the prompt.

The model must return strict JSON:

```json
{
  "nodes": [
    {
      "name": "...",
      "entity_type": "...",
      "description": "...",
      "evidence_span": "..."
    }
  ],
  "edges": [
    {
      "source": "...",
      "target": "...",
      "relation_type": "...",
      "description": "...",
      "evidence_span": "...",
      "confidence": 0.0
    }
  ]
}
```

The extractor maps returned names to stable entity ids, adds `contains` edges
from the source tree node, and preserves chunk evidence and metadata.

## Normalization and Clustering

Implemented in `kg_workbench/normalization/cluster.py`.

`normalize_and_cluster()` merges duplicate semantic entities within a document:

1. Structural nodes keep their original `tree:*` ids.
2. Semantic nodes cluster by normalized `{entity_type}:{name}`.
3. Duplicate node descriptions, evidence spans, and mention names are merged.
4. Edge endpoints are remapped to clustered node ids.
5. Duplicate edges are merged by `(src, tgt, relation_type, edge_source)`.
6. Edge descriptions, evidence spans, and confidence values are consolidated.

This produces a cleaner per-document graph while preserving mention metadata.

## Ontology Validation

Implemented in `kg_workbench/ontology/schema.py` and
`kg_workbench/ontology/validator.py`.

`default_ontology()` defines the allowed entity and relation types. Validation
then separates accepted graph items from review items:

- Nodes are rejected if their `entity_type` is unknown or they lack grounding.
- Edges are rejected if either endpoint is invalid, the relation type is
  unknown, confidence is below `0.5`, or evidence is missing.
- Structural nodes and structural edges are treated as grounded.
- Rejected items are written into the export payload under `review.nodes` and
  `review.edges` with `review_reasons`.

Only valid nodes and valid edges are persisted and exported as the primary KG.

## Persistence and Export

Implemented in `kg_workbench/storage/kuzu_store.py` and
`kg_workbench/storage/exporter.py`.

The current storage backend is Kuzu:

1. Open or create a per-document database directory.
2. Ensure the node table `Entity` and relationship table `Relation` exist.
3. Clear the existing graph for this document output directory.
4. Upsert all valid nodes.
5. Insert all valid edges.
6. Return stored node and edge counts.

The JSON exporter writes a full inspection payload containing:

- `document`: name, id, and source path.
- `tree`: recursive tree structure.
- `ontology`: allowed entity and relation type lists.
- `nodes`: valid KG nodes.
- `edges`: valid KG edges.
- `review`: rejected nodes and edges.
- `stats`: graph and storage counts.

## Output Layout

For each input Markdown file, the build creates a dedicated document directory:

```text
cache/kg_workbench/{document_id}/
  graph_kuzu/
    database.kuzu
  exports/
    graph.json
```

When the input is a manifest with multiple documents, the pipeline also writes:

```text
cache/kg_workbench/index.json
```

The index maps document names to their `document_id`, source path, and exported
graph path.

## End-to-End Step Summary

1. Load config from YAML or CLI flags.
2. Resolve input into one or more `DocumentInput` objects.
3. Parse each Markdown document into ordered components.
4. Construct a document tree from components.
5. Chunk extractable tree nodes.
6. Add structural KG nodes and tree relation edges.
7. Extract semantic candidate nodes and edges with the heuristic or LLM
   extractor.
8. Normalize and cluster duplicate semantic entities and edges.
9. Validate nodes and edges against the default ontology and grounding rules.
10. Persist valid graph items to Kuzu.
11. Export `graph.json` with graph, tree, ontology, review, and stats.
12. For manifest runs, write `index.json`.

## Extension Points

- Add new input formats under `kg_workbench/readers/`, then extend
  `load_documents()`.
- Add new component types in `tree/markdown.py`, then map their modality and
  structural entity type in `extractors/structural.py`.
- Add or revise ontology labels in `ontology/schema.py`.
- Add another extractor implementation under `extractors/` and expose it through
  `WorkbenchConfig` and `build.py`.
- Add another storage backend under `storage/` and extend the backend switch in
  `build_document_kg()`.

Keep generated data in `cache/`, runnable examples in `examples/`, implementation
code in `kg_workbench/`, and durable documentation in `docs/`.
