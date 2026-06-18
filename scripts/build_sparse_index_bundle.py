#!/usr/bin/env python3
"""Build the sparse-index bundle variant.

Indexes keep only a minimal frontmatter block: type, title, and description.
Concept files remain identical to the source bundle.
"""

from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_BUNDLE = ROOT / "bundles" / "uniform-yaml-retail-ops"
TARGET_BUNDLE = ROOT / "bundles" / "sparse-index-retail-ops"


def _split_frontmatter(text: str) -> tuple[list[str] | None, str]:
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text
    return text[4:end].splitlines(), text[end + 5 :]


def _parse_kv_lines(lines: list[str]) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data


def _heading_and_body(body: str) -> tuple[str, str]:
    lines = body.splitlines()
    heading = lines[0] if lines and lines[0].startswith("# ") else "# Index"
    rest = "\n".join(lines[1:]).lstrip("\n")
    return heading, rest


def _first_paragraph(text: str, fallback: str) -> str:
    chunks = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]
    for chunk in chunks:
        if chunk.startswith("# "):
            continue
        if chunk.startswith("- "):
            continue
        return " ".join(line.strip() for line in chunk.splitlines())
    return fallback


def _rewrite_index(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    frontmatter, body = _split_frontmatter(text)
    if frontmatter is None:
        return
    fm = _parse_kv_lines(frontmatter)
    heading, body_tail = _heading_and_body(body)
    title = heading.lstrip("# ").strip() or fm.get("title", "Index")
    description = _first_paragraph(
        body_tail,
        f"Navigation page for {title}.",
    )
    new_frontmatter = "\n".join([
        "---",
        "type: directory_index",
        f"title: {title}",
        f"description: {description}",
        "---",
    ]) + "\n"
    path.write_text(new_frontmatter + body, encoding="utf-8")


def main() -> int:
    if not SOURCE_BUNDLE.exists():
        raise SystemExit(f"source bundle not found: {SOURCE_BUNDLE}")

    if TARGET_BUNDLE.exists():
        shutil.rmtree(TARGET_BUNDLE)
    shutil.copytree(SOURCE_BUNDLE, TARGET_BUNDLE)

    for path in TARGET_BUNDLE.rglob("index.md"):
        _rewrite_index(path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
