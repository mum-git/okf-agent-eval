#!/usr/bin/env python3
"""Build the body-routed index bundle variant.

This variant removes all YAML from index files and moves routing signal into the
body via a routing paragraph plus a dedicated key-entries section.
"""

from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_BUNDLE = ROOT / "bundles" / "uniform-yaml-retail-ops"
TARGET_BUNDLE = ROOT / "bundles" / "body-routed-indexes-retail-ops"


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


def _routing_paragraph(frontmatter: dict[str, str], heading: str) -> str:
    parts = [
        frontmatter.get("task_hint", ""),
        frontmatter.get("routing_hint", ""),
        frontmatter.get("priority_hint", ""),
    ]
    bits = [part.strip().rstrip(".") for part in parts if part and part.strip()]
    if bits:
        lead = "Routing note: " + ". ".join(bits) + "."
    else:
        lead = f"Routing note: start from {heading.lstrip('# ').strip()} and follow the key entries below."
    return lead


def _key_entries_block(body: str) -> str:
    lines = body.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.lstrip().startswith("- "):
            start = index
            break
    if start is None:
        return body.strip()
    return "\n".join(lines[start:]).rstrip()


def _rewrite_index(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    frontmatter, body = _split_frontmatter(text)
    if frontmatter is None:
        return
    fm = _parse_kv_lines(frontmatter)
    heading, body_tail = _heading_and_body(body)
    routing = _routing_paragraph(fm, heading)
    key_entries = _key_entries_block(body_tail)
    new_body = "\n".join([
        heading,
        "",
        routing,
        "",
        "## Key entries:",
        "",
        key_entries,
    ]).rstrip() + "\n"
    path.write_text(new_body, encoding="utf-8")


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
