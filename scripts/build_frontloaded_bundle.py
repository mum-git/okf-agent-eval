#!/usr/bin/env python3
"""Build the frontloaded YAML bundle variant for the hard-mode benchmark.

This variant is the inverse of the progressive/extended style:
top-level indexes carry richer frontmatter, and directory indexes become
lighter as depth increases.
"""

from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_BUNDLE = ROOT / "bundles" / "extended-retail-ops"
TARGET_BUNDLE = ROOT / "bundles" / "frontloaded-yaml-retail-ops"


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


def _render_frontmatter(lines: list[tuple[str, str]]) -> str:
    out = ["---"]
    out.extend(f"{key}: {value}" for key, value in lines)
    out.append("---")
    return "\n".join(out) + "\n"


def _rewrite_root_index(path: Path) -> None:
    body = (
        "# Northstar Retail Ops Knowledge Catalog\n\n"
        "This frontloaded-YAML variant starts with denser directory metadata at the "
        "top of the tree and gets lighter as you descend.\n\n"
        "## Domains\n\n"
        "- [Commerce](commerce/index.md)\n"
        "- [Platform](platform/index.md)\n"
        "- [Incidents](incidents/index.md)\n\n"
        "- [Deep retail ops](deep-retail-ops/index.md): deeper benchmark corpus with regional, identity, pipeline, experiment, and incident branches.\n\n"
        "- [Enterprise FNF mock](enterprise-fnf/index.md): synthetic title-insurance enterprise schema catalog for database lineage tests.\n"
    )
    fm = _render_frontmatter([
        ("okf_version", "0.1"),
        ("scope", "northstar-retail-ops"),
        ("frontmatter_policy", "frontloaded-index-extension"),
        ("metadata_profile", "frontloaded-heavy"),
        ("owner", "knowledge-team"),
    ])
    path.write_text(fm + body, encoding="utf-8")


def _rewrite_directory_index(path: Path, rel_depth: int) -> None:
    text = path.read_text(encoding="utf-8")
    frontmatter, body = _split_frontmatter(text)
    if frontmatter is None:
        return
    fm = _parse_kv_lines(frontmatter)
    density = "frontloaded-heavy" if rel_depth <= 2 else "frontloaded-light"
    lines: list[tuple[str, str]] = [
        ("type", fm.get("type", "directory_index")),
        ("domain", fm.get("domain", "")),
        ("area", fm.get("area", "")),
        ("depth", fm.get("depth", str(rel_depth))),
        ("metadata_profile", density),
        ("owner", fm.get("owner", "knowledge-team")),
    ]
    if rel_depth <= 6 and fm.get("task_hint"):
        lines.append(("task_hint", fm["task_hint"]))
    if rel_depth <= 4 and fm.get("routing_hint"):
        lines.append(("routing_hint", fm["routing_hint"]))
    if rel_depth <= 2 and fm.get("priority_hint"):
        lines.append(("priority_hint", fm["priority_hint"]))
    path.write_text(_render_frontmatter(lines) + body, encoding="utf-8")


def main() -> int:
    if not SOURCE_BUNDLE.exists():
        raise SystemExit(f"source bundle not found: {SOURCE_BUNDLE}")

    if TARGET_BUNDLE.exists():
        shutil.rmtree(TARGET_BUNDLE)
    shutil.copytree(SOURCE_BUNDLE, TARGET_BUNDLE)

    for path in TARGET_BUNDLE.rglob("index.md"):
        rel_depth = len(path.relative_to(TARGET_BUNDLE).parent.parts)
        if path == TARGET_BUNDLE / "index.md":
            _rewrite_root_index(path)
        else:
            _rewrite_directory_index(path, rel_depth)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
