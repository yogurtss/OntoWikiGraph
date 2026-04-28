from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_export_path(path_value: str, *, working_dir: Path) -> Path:
    path = Path(path_value).expanduser()
    if path.is_absolute():
        return path
    if path.exists():
        return path.resolve()
    return (working_dir / path).resolve()


def _graph_exports_from_index(working_dir: Path) -> list[Path]:
    index_path = working_dir / "index.json"
    if not index_path.exists():
        return []

    index = _read_json(index_path)
    graph_paths: list[Path] = []
    for entry in index.values():
        if not isinstance(entry, dict):
            continue
        export_path = entry.get("export_path")
        if isinstance(export_path, str):
            graph_paths.append(_resolve_export_path(export_path, working_dir=working_dir))
            continue
        document_id = entry.get("document_id")
        if isinstance(document_id, str):
            graph_paths.append(working_dir / document_id / "exports" / "graph.json")
    return graph_paths


def discover_graph_exports(working_dir: Path) -> list[Path]:
    graph_paths = _graph_exports_from_index(working_dir)
    if not graph_paths:
        graph_paths = sorted(working_dir.glob("*/exports/graph.json"))
    return [path for path in graph_paths if path.exists()]


def publish_frontend_data(*, working_dir: Path, frontend_dir: Path) -> dict[str, Any]:
    working_dir = working_dir.expanduser().resolve()
    frontend_dir = frontend_dir.expanduser().resolve()
    public_kg_dir = frontend_dir / "public" / "kg"
    public_kg_dir.mkdir(parents=True, exist_ok=True)

    graph_paths = discover_graph_exports(working_dir)
    if not graph_paths:
        raise FileNotFoundError(f"No graph exports found under {working_dir}")

    frontend_index: dict[str, dict[str, str]] = {}
    for graph_path in graph_paths:
        graph = _read_json(graph_path)
        document = graph.get("document", {})
        if not isinstance(document, dict):
            raise ValueError(f"Missing document metadata in {graph_path}")

        document_id = str(document.get("document_id") or graph_path.parent.parent.name)
        document_name = str(document.get("document_name") or document_id)
        target_dir = public_kg_dir / document_id
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(graph_path, target_dir / "graph.json")
        frontend_index[document_name] = {
            "document_id": document_id,
            "document_name": document_name,
            "source_path": str(document.get("source_path", "")),
            "graph_path": f"{document_id}/graph.json",
        }

    index_path = public_kg_dir / "index.json"
    index_path.write_text(json.dumps(frontend_index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "graph_count": len(frontend_index),
        "index_path": str(index_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish KG exports into the frontend public data directory.")
    parser.add_argument("--working-dir", default="cache/kg_workbench", help="KG workbench output directory.")
    parser.add_argument("--frontend-dir", default="frontend", help="Frontend project directory.")
    args = parser.parse_args()

    result = publish_frontend_data(working_dir=Path(args.working_dir), frontend_dir=Path(args.frontend_dir))
    print(f"Published {result['graph_count']} graph(s) -> {result['index_path']}")


if __name__ == "__main__":
    main()
