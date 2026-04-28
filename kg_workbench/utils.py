from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


def stable_id(*parts: object, prefix: str = "") -> str:
    payload = "\n".join(str(part) for part in parts)
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}{digest}"


def slugify(value: str, fallback: str = "item") -> str:
    base = (value or fallback).strip() or fallback
    base = re.sub(r"^#{1,6}\s+", "", base)
    base = re.sub(r"\s+", "-", base)
    base = re.sub(r"[\\/]+", "-", base)
    base = re.sub(r"[^\w.\-]+", "-", base, flags=re.UNICODE)
    base = re.sub(r"-{2,}", "-", base).strip("-_.")
    return base or fallback


def compact_text(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", (text or "").strip())


def normalize_key(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[_\-]+", " ", value)
    value = re.sub(r"[^\w\s./+=%]+", "", value, flags=re.UNICODE)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item) for item in value]
    return value


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(to_jsonable(data), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

