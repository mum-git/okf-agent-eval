#!/usr/bin/env python3
"""Build concept-metadata alignment and drift bundle variants.

The matched variant copies each concept file's nearest index metadata into the
concept frontmatter. The drift variant does the same, then perturbs a small set
of inherited fields so the concept YAML is close to the index YAML but not
identical.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from grader import parse_frontmatter  # noqa: E402


SOURCE_BUNDLE = ROOT / "bundles" / "uniform-yaml-retail-ops"
TARGET_BUNDLES = {
    "concept-matched-yaml": ROOT / "bundles" / "concept-matched-yaml-retail-ops",
    "concept-drift-yaml": ROOT / "bundles" / "concept-drift-yaml-retail-ops",
}

INHERITED_KEYS = (
    "domain",
    "area",
    "depth",
    "metadata_profile",
    "owner",
    "task_hint",
    "routing_hint",
)

DRIFTED_KEYS = ("metadata_profile", "owner", "depth")


def _format_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if not text:
        return '""'
    if text == text.strip() and all(ch.isalnum() or ch in {"-", "_", ".", "/"} for ch in text):
        return text
    return json.dumps(text, ensure_ascii=True)


def _render_frontmatter(data: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {_format_scalar(item)}")
            continue
        lines.append(f"{key}: {_format_scalar(value)}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def _nearest_index_path(path: Path, bundle_root: Path) -> Path | None:
    current = path.parent
    while True:
        candidate = current / "index.md"
        if candidate.exists():
            return candidate
        if current == bundle_root or current.parent == current:
            return None
        current = current.parent


def _rewrite_concept(path: Path, bundle_root: Path, *, drift: bool) -> None:
    index_path = _nearest_index_path(path, bundle_root)
    if index_path is None:
        raise SystemExit(f"no ancestor index.md found for {path}")

    concept_fm, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    if not isinstance(concept_fm, dict):
        raise SystemExit(f"concept file missing frontmatter: {path}")

    index_fm, _ = parse_frontmatter(index_path.read_text(encoding="utf-8"))
    if not isinstance(index_fm, dict):
        raise SystemExit(f"index file missing frontmatter: {index_path}")

    merged = dict(concept_fm)
    for key in INHERITED_KEYS:
        if key in index_fm:
            merged[key] = index_fm[key]

    if drift:
        if "metadata_profile" in merged:
            merged["metadata_profile"] = "concept-drift-enterprise"
        if "owner" in merged:
            merged["owner"] = "concept-knowledge-team"
        if isinstance(merged.get("depth"), int):
            merged["depth"] = int(merged["depth"]) + 1

    path.write_text(_render_frontmatter(merged) + body.lstrip("\n"), encoding="utf-8")


def _build_bundle(target_bundle: Path, *, drift: bool) -> None:
    if target_bundle.exists():
        shutil.rmtree(target_bundle)
    shutil.copytree(SOURCE_BUNDLE, target_bundle)

    for path in target_bundle.rglob("*.md"):
        if path.name == "index.md":
            continue
        _rewrite_concept(path, target_bundle, drift=drift)


def main() -> int:
    if not SOURCE_BUNDLE.exists():
        raise SystemExit(f"source bundle not found: {SOURCE_BUNDLE}")

    _build_bundle(TARGET_BUNDLES["concept-matched-yaml"], drift=False)
    _build_bundle(TARGET_BUNDLES["concept-drift-yaml"], drift=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
