from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class WorkbenchConfig:
    input_path: str
    working_dir: str = "cache/kg_workbench"
    graph_backend: str = "kuzu"
    export: str = "json"
    split_text_nodes: bool = False
    extractor: str = "heuristic"
    llm_model: str | None = None
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_temperature: float = 0.0


def _dig(data: dict[str, Any], *path: str, default: Any = None) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def load_config(path: str | Path) -> WorkbenchConfig:
    config_path = Path(path).expanduser().resolve()
    if not config_path.is_file():
        raise FileNotFoundError(config_path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("YAML config must be a mapping")

    input_path = data.get("input") or data.get("input_path")
    if not input_path:
        raise ValueError("YAML config must define `input` or `input_path`")

    return WorkbenchConfig(
        input_path=str(input_path),
        working_dir=str(data.get("working_dir", "cache/kg_workbench")),
        graph_backend=str(data.get("graph_backend", "kuzu")),
        export=str(data.get("export", "json")),
        split_text_nodes=bool(_dig(data, "tree", "split_text_nodes", default=data.get("split_text_nodes", False))),
        extractor=str(_dig(data, "extraction", "extractor", default=data.get("extractor", "heuristic"))),
        llm_model=_dig(data, "llm", "model", default=data.get("llm_model")),
        llm_api_key=_dig(data, "llm", "api_key", default=data.get("llm_api_key")),
        llm_base_url=_dig(data, "llm", "base_url", default=data.get("llm_base_url")),
        llm_temperature=float(_dig(data, "llm", "temperature", default=data.get("llm_temperature", 0.0))),
    )

