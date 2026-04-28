from __future__ import annotations

import re
from typing import Any

from kg_workbench.models import Component, DocumentInput
from kg_workbench.utils import compact_text, stable_id

TITLE_PATTERNS = [
    re.compile(r"^#{1,6}\s+.+"),
    re.compile(r"^(?:\d+(?:\.\d+)+(?:\s+.*)?|\d+\s+.+)$"),
    re.compile(r"^(?:第[一二三四五六七八九十百千万\d]+[章节篇节])\s*.+"),
]


def infer_title_level(title: str) -> int:
    stripped = (title or "").strip()
    if not stripped:
        return 1

    markdown_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
    markdown_level = len(markdown_match.group(1)) if markdown_match else 0
    semantic_source = markdown_match.group(2).strip() if markdown_match else stripped

    numeric = re.match(r"^(\d+(?:\.\d+)*)(?:\s+.+)?$", semantic_source)
    if numeric:
        numeric_level = min(6, numeric.group(1).count(".") + 1)
        return max(markdown_level, numeric_level)

    zh_num = re.match(r"^第([一二三四五六七八九十百千万\d]+)([章节篇节])", semantic_source)
    if zh_num:
        zh_level = 1 if zh_num.group(2) in {"章", "篇"} else 2
        return max(markdown_level, zh_level)

    return markdown_level or 1


def is_title_line(line: str) -> bool:
    line = (line or "").strip()
    return bool(line) and any(pattern.match(line) for pattern in TITLE_PATTERNS)


def _is_table_caption(line: str) -> bool:
    return bool(re.match(r"^(table|tab\.?)\s*\d+[\.:]?\s+", line.strip(), re.I))


def _is_image_caption(line: str) -> bool:
    stripped = (line or "").strip()
    return bool(
        re.match(r"^(figure|fig\.?|image|img\.?)\s*\d+[\.:]?\s+", stripped, re.I)
        or re.match(r"^图\s*\d+[\.:：]?\s*", stripped)
    )


def _is_image_line(line: str) -> bool:
    stripped = (line or "").strip()
    return bool(
        re.match(r"^!\[[^\]]*\]\([^)]+\)", stripped)
        or re.search(r"<img\b[^>]*src=['\"][^'\"]+['\"][^>]*>", stripped, re.I)
    )


def _extract_image_path(line: str) -> str:
    stripped = (line or "").strip()
    markdown_match = re.match(r"^!\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", stripped)
    if markdown_match:
        return markdown_match.group(1)

    html_match = re.search(r"<img\b[^>]*src=['\"]([^'\"]+)['\"][^>]*>", stripped, re.I)
    return html_match.group(1) if html_match else ""


def _split_paragraphs(lines: list[str]) -> list[list[str]]:
    paragraphs: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.strip():
            current.append(line)
            continue
        if current:
            paragraphs.append(current)
            current = []
    if current:
        paragraphs.append(current)
    return paragraphs


def _normalize_mm_payload(metadata: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(metadata)
    for key in ("table_caption", "image_caption"):
        value = normalized.get(key)
        if isinstance(value, str):
            normalized[key] = [value] if value else []
        elif value is None:
            normalized[key] = []
    note_text = normalized.get("note_text")
    if isinstance(note_text, list):
        normalized["note_text"] = compact_text("\n".join(str(item) for item in note_text if item))
    elif note_text is None:
        normalized["note_text"] = ""
    else:
        normalized["note_text"] = compact_text(str(note_text))
    return normalized


def _make_component(
    doc: DocumentInput,
    component_type: str,
    title: str,
    content: str,
    index: int,
    metadata: dict[str, Any] | None = None,
) -> Component:
    return Component(
        component_id=stable_id(doc.document_id, index, component_type, title, prefix="cmp-"),
        type=component_type,
        title=title,
        content=compact_text(content),
        title_level=infer_title_level(title),
        metadata=metadata or {},
    )


def _build_text_components(
    doc: DocumentInput,
    title: str,
    lines: list[str],
    start_index: int,
) -> tuple[list[Component], int]:
    components = []
    index = start_index
    for paragraph in _split_paragraphs(lines):
        content = compact_text("\n".join(paragraph))
        if not content:
            continue
        components.append(_make_component(doc, "text", title, content, index))
        index += 1
    return components, index


def _split_trailing_paragraph(lines: list[str]) -> tuple[list[str], str]:
    if not lines:
        return [], ""
    end = len(lines)
    while end > 0 and not lines[end - 1].strip():
        end -= 1
    if end == 0:
        return [], ""
    start = end - 1
    while start > 0 and lines[start - 1].strip():
        start -= 1
    return lines[:start], compact_text("\n".join(lines[start:end]))


def _consume_trailing_image_lines(
    lines: list[str], start_idx: int
) -> tuple[int, list[str], list[str]]:
    idx = start_idx
    candidate_lines: list[str] = []
    while idx < len(lines):
        raw_line = lines[idx]
        stripped = raw_line.strip()
        if is_title_line(stripped) or _is_image_line(stripped) or stripped.lower().startswith("<table"):
            break
        candidate_lines.append(raw_line)
        idx += 1

    caption_start = None
    for pos, raw_line in enumerate(candidate_lines):
        if _is_image_caption(raw_line):
            caption_start = pos
            break
    if caption_start is None:
        return start_idx, [], []

    note_lines = [line.strip() for line in candidate_lines[:caption_start] if line.strip()]
    caption_lines = [line.strip() for line in candidate_lines[caption_start:] if line.strip()]
    return idx, caption_lines, note_lines


def analyze_markdown_structure(doc: DocumentInput) -> list[Component]:
    lines = doc.content.splitlines()
    components: list[Component] = []
    current_title = "Document"
    current_buffer: list[str] = []
    idx = 0
    component_index = 1

    def flush_text_buffer() -> None:
        nonlocal current_buffer, component_index
        text_components, component_index = _build_text_components(
            doc, current_title, current_buffer, component_index
        )
        components.extend(text_components)
        current_buffer = []

    while idx < len(lines):
        raw_line = lines[idx]
        line = raw_line.strip()

        if not line:
            current_buffer.append("")
            idx += 1
            continue

        if is_title_line(line):
            flush_text_buffer()
            current_title = line
            components.append(_make_component(doc, "section", current_title, "", component_index))
            component_index += 1
            idx += 1
            continue

        if line.lower().startswith("<table"):
            leading_lines, caption = _split_trailing_paragraph(current_buffer)
            use_caption = caption if _is_table_caption(caption) else ""
            current_buffer = leading_lines if use_caption else current_buffer
            flush_text_buffer()

            table_lines = [raw_line]
            idx += 1
            if "</table>" not in line.lower():
                while idx < len(lines):
                    table_lines.append(lines[idx])
                    if "</table>" in lines[idx].lower():
                        idx += 1
                        break
                    idx += 1
            table_body = compact_text("\n".join(table_lines))
            metadata = _normalize_mm_payload(
                {"table_body": table_body, "table_caption": [use_caption] if use_caption else []}
            )
            content = "\n\n".join(
                part
                for part in [
                    f"[Table Caption]\n{use_caption}" if use_caption else "",
                    f"[Table Body]\n{table_body}",
                ]
                if part
            )
            components.append(_make_component(doc, "table", current_title, content, component_index, metadata))
            component_index += 1
            continue

        if _is_image_line(line):
            flush_text_buffer()
            image_path = _extract_image_path(line)
            idx, caption_lines, note_lines = _consume_trailing_image_lines(lines, idx + 1)
            metadata = _normalize_mm_payload(
                {
                    "img_path": image_path,
                    "image_caption": caption_lines,
                    "note_text": compact_text("\n".join(note_lines)),
                }
            )
            content = "\n\n".join(
                part
                for part in [
                    compact_text("\n".join(caption_lines)),
                    f"[Notes]\n{metadata['note_text']}" if metadata.get("note_text") else "",
                ]
                if part
            )
            components.append(_make_component(doc, "image", current_title, content, component_index, metadata))
            component_index += 1
            continue

        current_buffer.append(raw_line)
        idx += 1

    flush_text_buffer()
    if not components and doc.content.strip():
        components.append(_make_component(doc, "text", "Document", doc.content, 1))
    return components

