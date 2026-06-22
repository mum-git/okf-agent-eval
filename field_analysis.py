#!/usr/bin/env python3
"""Helpers for YAML field-usage analysis and frontmatter ablations."""

from __future__ import annotations

import json
import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

from grader import parse_frontmatter


FRONTMATTER_SCOPES = {"index", "concept", "all"}


def slugify_field(field: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", field.strip().lower())
    return slug.strip("-") or "field"


def _split_frontmatter(text: str) -> tuple[list[str] | None, str]:
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text
    return text[4:end].splitlines(), text[end + 5 :]


def _render_frontmatter(lines: list[str]) -> str:
    if not lines:
        return ""
    return "---\n" + "\n".join(lines) + "\n---\n"


def strip_frontmatter_fields(text: str, remove_fields: set[str]) -> str:
    """Remove selected top-level YAML keys from a frontmatter block."""
    frontmatter, body = _split_frontmatter(text)
    if frontmatter is None:
        return text

    kept_lines: list[str] = []
    keep_current = True
    for line in frontmatter:
        if not line.strip():
            if keep_current:
                kept_lines.append(line)
            continue
        if line.lstrip().startswith("#"):
            if keep_current:
                kept_lines.append(line)
            continue
        if line.startswith("  - "):
            if keep_current:
                kept_lines.append(line)
            continue
        if line.startswith((" ", "\t")):
            if keep_current:
                kept_lines.append(line)
            continue
        if ":" not in line:
            if keep_current:
                kept_lines.append(line)
            continue

        key, value = line.split(":", 1)
        keep_current = key.strip() not in remove_fields
        if keep_current:
            kept_lines.append(f"{key}:{value}")

    has_key_lines = any(
        ":" in line and not line.startswith((" ", "\t")) and not line.lstrip().startswith("#")
        for line in kept_lines
    )
    rendered_frontmatter = _render_frontmatter(kept_lines if has_key_lines else [])
    if not rendered_frontmatter:
        return body.lstrip("\n")
    return rendered_frontmatter + body.lstrip("\n")


def _validate_scope(scope: str) -> str:
    if scope not in FRONTMATTER_SCOPES:
        raise ValueError(f"scope must be one of {sorted(FRONTMATTER_SCOPES)}")
    return scope


def _path_matches_scope(path: Path, scope: str) -> bool:
    scope = _validate_scope(scope)
    if path.suffix != ".md":
        return False
    if scope == "all":
        return True
    if scope == "index":
        return path.name == "index.md"
    return path.name not in {"index.md", "log.md"}


def build_ablation_bundle(
    source_bundle: Path,
    target_bundle: Path,
    remove_fields: set[str],
    *,
    scope: str = "index",
) -> None:
    """Copy a bundle and remove selected frontmatter keys from scoped Markdown files."""
    scope = _validate_scope(scope)
    if target_bundle.exists():
        shutil.rmtree(target_bundle)
    shutil.copytree(source_bundle, target_bundle)
    for path in target_bundle.rglob("*.md"):
        if not _path_matches_scope(path, scope):
            continue
        text = path.read_text(encoding="utf-8")
        path.write_text(strip_frontmatter_fields(text, remove_fields), encoding="utf-8")


def frontmatter_field_inventory(bundle: Path, *, scope: str = "all") -> dict[str, int]:
    """Count how often each frontmatter key appears across scoped Markdown files."""
    scope = _validate_scope(scope)
    inventory: dict[str, int] = defaultdict(int)
    for path in bundle.rglob("*.md"):
        if not _path_matches_scope(path, scope):
            continue
        fm, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        if not isinstance(fm, dict):
            continue
        for key in fm:
            inventory[str(key)] += 1
    return dict(sorted(inventory.items()))


def index_field_inventory(bundle: Path) -> dict[str, int]:
    """Count how often each frontmatter key appears across index files."""
    return frontmatter_field_inventory(bundle, scope="index")


def _normalize_trace_path(raw_path: str, bundle: Path) -> str:
    path = raw_path.strip()
    bundle_prefix = bundle.as_posix().rstrip("/")
    if path.startswith(bundle_prefix):
        path = path[len(bundle_prefix):]
    if path.startswith("./"):
        path = path[1:]
    if not path.startswith("/"):
        path = "/" + path.lstrip("/")
    return path


def _read_trace_paths(trace_path: Path, bundle: Path) -> list[str]:
    return [event["path"] for event in _read_trace_events(trace_path, bundle)]


def _read_trace_events(trace_path: Path, bundle: Path) -> list[dict[str, Any]]:
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    if not isinstance(trace, dict):
        return []
    events: list[dict[str, Any]] = []
    for event in trace.get("events", []):
        if not isinstance(event, dict):
            continue
        event_type = str(event.get("type") or event.get("event") or "").strip().lower()
        if event_type not in {"read", "open", "read_file", "file_read", "file-read", "view", "inspect"}:
            continue
        raw_path = event.get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            continue
        events.append({
            "type": "read",
            "path": _normalize_trace_path(raw_path, bundle),
        })
    return events


def _metric_mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _metric_median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return round(ordered[mid], 4)
    return round((ordered[mid - 1] + ordered[mid]) / 2, 4)


def collect_frontmatter_field_usage(
    results: list[dict[str, Any]],
    *,
    baseline_variants: set[str] | None = None,
    scope: str = "index",
) -> dict[str, Any]:
    """Summarize which YAML keys appeared in scoped read Markdown files."""
    scope = _validate_scope(scope)
    baseline_variants = baseline_variants or set()
    field_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    field_run_counts: dict[str, int] = defaultdict(int)
    field_read_counts: dict[str, int] = defaultdict(int)
    field_bundle_presence: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    overall_runs = 0

    for row in results:
        if row.get("status") != "pass":
            continue
        variant = str(row.get("variant") or "")
        if baseline_variants and variant not in baseline_variants:
            continue
        run_dir = row.get("run_dir")
        bundle_raw = row.get("bundle")
        if not isinstance(run_dir, str) or not isinstance(bundle_raw, str):
            continue
        trace_path = Path(run_dir) / "trace.json"
        bundle = Path(bundle_raw)
        if not trace_path.exists() or not bundle.exists():
            continue

        overall_runs += 1
        run_metrics = row.get("grade") or {}
        seen_in_run: set[str] = set()

        for raw_path in _read_trace_paths(trace_path, bundle):
            file_path = bundle / raw_path.lstrip("/")
            if not file_path.exists() or not _path_matches_scope(file_path, scope):
                continue
            fm, _ = parse_frontmatter(file_path.read_text(encoding="utf-8"))
            if not isinstance(fm, dict):
                continue
            for key in fm:
                field = str(key)
                field_read_counts[field] += 1
                field_bundle_presence[field][variant] += 1
                seen_in_run.add(field)

        for field in seen_in_run:
            field_run_counts[field] += 1
            field_rows[field].append(run_metrics)

    field_entries: list[dict[str, Any]] = []
    for field in sorted(field_read_counts, key=lambda item: (-field_read_counts[item], item)):
        rows = field_rows.get(field, [])
        accuracies = [float(r["accuracy_score"]) for r in rows if isinstance(r.get("accuracy_score"), (int, float))]
        speeds = [float(r.get("speed_score", 0.0)) for r in rows if isinstance(r.get("speed_score"), (int, float))]
        tokens = [float(r["tokens_used"]) for r in rows if isinstance(r.get("tokens_used"), (int, float))]
        durations = [float(r["duration_ms"]) for r in rows if isinstance(r.get("duration_ms"), (int, float))]
        field_entries.append({
            "field": field,
            "read_count": field_read_counts[field],
            "run_count": field_run_counts[field],
            "avg_accuracy_score_when_seen": _metric_mean(accuracies),
            "median_accuracy_score_when_seen": _metric_median(accuracies),
            "avg_speed_score_when_seen": _metric_mean(speeds),
            "median_speed_score_when_seen": _metric_median(speeds),
            "avg_tokens_used_when_seen": _metric_mean(tokens),
            "median_tokens_used_when_seen": _metric_median(tokens),
            "avg_duration_ms_when_seen": _metric_mean(durations),
            "median_duration_ms_when_seen": _metric_median(durations),
            "bundle_presence_by_variant": dict(sorted(field_bundle_presence[field].items())),
        })

    return {
        "frontmatter_scope": scope,
        "baseline_run_count": overall_runs,
        "fields": field_entries,
    }


def collect_index_field_usage(
    results: list[dict[str, Any]],
    *,
    baseline_variants: set[str] | None = None,
) -> dict[str, Any]:
    """Summarize which YAML keys appeared in read index files during baseline runs."""
    return collect_frontmatter_field_usage(results, baseline_variants=baseline_variants, scope="index")


def _index_depth_from_trace_path(path: str) -> int:
    rel = Path(path.lstrip("/"))
    return len(rel.parent.parts)


def _ancestor_index_paths(path: str) -> list[str]:
    rel = Path(path.lstrip("/"))
    ancestors: list[str] = []
    current = rel.parent
    while current.parts:
        ancestors.append("/" + (current / "index.md").as_posix())
        current = current.parent
    ancestors.append("/index.md")
    ancestors.reverse()
    return ancestors


def collect_index_depth_coverage(
    results: list[dict[str, Any]],
    *,
    baseline_variants: set[str] | None = None,
) -> dict[str, Any]:
    """Summarize how many index pages were read and whether ancestor chains were followed."""
    baseline_variants = baseline_variants or set()
    run_rows: list[dict[str, Any]] = []

    for row in results:
        if row.get("status") != "pass":
            continue
        variant = str(row.get("variant") or "")
        if baseline_variants and variant not in baseline_variants:
            continue
        run_dir = row.get("run_dir")
        bundle_raw = row.get("bundle")
        if not isinstance(run_dir, str) or not isinstance(bundle_raw, str):
            continue
        trace_path = Path(run_dir) / "trace.json"
        bundle = Path(bundle_raw)
        if not trace_path.exists() or not bundle.exists():
            continue

        events = _read_trace_events(trace_path, bundle)
        seen_index_paths: set[str] = set()
        seen_index_depths: dict[int, int] = defaultdict(int)
        concept_read_count = 0
        concept_complete_count = 0
        ancestor_miss_count = 0
        first_concept_seen = False

        for event in events:
            raw_path = str(event.get("path") or "")
            if not raw_path:
                continue
            file_path = bundle / raw_path.lstrip("/")
            if not file_path.exists():
                continue
            if file_path.name == "index.md":
                seen_index_paths.add(raw_path)
                depth = _index_depth_from_trace_path(raw_path)
                seen_index_depths[depth] += 1
                continue

            concept_read_count += 1
            first_concept_seen = True
            ancestor_paths = _ancestor_index_paths(raw_path)
            missing = [ancestor for ancestor in ancestor_paths if ancestor not in seen_index_paths]
            if missing:
                ancestor_miss_count += 1
            else:
                concept_complete_count += 1

        run_rows.append({
            "variant": variant,
            "index_read_count": len(seen_index_paths),
            "index_depth_counts": dict(sorted(seen_index_depths.items())),
            "max_index_depth_read": max(seen_index_depths) if seen_index_depths else None,
            "concept_read_count": concept_read_count,
            "ancestor_chain_complete": concept_read_count > 0 and ancestor_miss_count == 0,
            "ancestor_chain_miss_count": ancestor_miss_count,
            "ancestor_chain_complete_rate": _metric_mean([concept_complete_count / concept_read_count]) if concept_read_count else None,
            "first_concept_seen": first_concept_seen,
        })

    index_read_counts = [float(row["index_read_count"]) for row in run_rows]
    max_depths = [float(row["max_index_depth_read"]) for row in run_rows if isinstance(row.get("max_index_depth_read"), int)]
    complete_runs = [row for row in run_rows if row["ancestor_chain_complete"]]
    concept_counts = [float(row["concept_read_count"]) for row in run_rows]
    miss_counts = [float(row["ancestor_chain_miss_count"]) for row in run_rows]
    complete_rates = [
        float(row["ancestor_chain_complete_rate"])
        for row in run_rows
        if isinstance(row.get("ancestor_chain_complete_rate"), (int, float))
    ]

    depth_histogram: dict[int, int] = defaultdict(int)
    for row in run_rows:
        for depth, count in row["index_depth_counts"].items():
            depth_histogram[int(depth)] += int(count)

    return {
        "baseline_run_count": len(run_rows),
        "avg_index_read_count": _metric_mean(index_read_counts),
        "median_index_read_count": _metric_median(index_read_counts),
        "avg_concept_read_count": _metric_mean(concept_counts),
        "median_concept_read_count": _metric_median(concept_counts),
        "avg_max_index_depth_read": _metric_mean(max_depths),
        "median_max_index_depth_read": _metric_median(max_depths),
        "avg_ancestor_chain_miss_count": _metric_mean(miss_counts),
        "median_ancestor_chain_miss_count": _metric_median(miss_counts),
        "ancestor_chain_complete_run_count": len(complete_runs),
        "ancestor_chain_complete_rate": round(len(complete_runs) / len(run_rows), 4) if run_rows else None,
        "avg_ancestor_chain_complete_rate_per_run": _metric_mean(complete_rates),
        "depth_histogram": dict(sorted(depth_histogram.items())),
        "runs": run_rows,
    }


def build_ablation_effects(
    summary: dict[str, Any],
    ablation_specs: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    """Compare baseline variants against ablated counterparts."""
    impacts: list[dict[str, Any]] = []
    for ablated_variant, spec in sorted(ablation_specs.items()):
        base_variant = spec["base_variant"]
        field = spec["field"]
        base = summary.get(base_variant)
        ablated = summary.get(ablated_variant)
        if not isinstance(base, dict) or not isinstance(ablated, dict):
            continue

        def get_num(row: dict[str, Any], key: str) -> float | None:
            value = row.get(key)
            return float(value) if isinstance(value, (int, float)) else None

        base_accuracy = get_num(base, "avg_accuracy_score")
        ablated_accuracy = get_num(ablated, "avg_accuracy_score")
        base_speed = get_num(base, "avg_speed_score")
        ablated_speed = get_num(ablated, "avg_speed_score")
        base_tokens = get_num(base, "avg_tokens_used")
        ablated_tokens = get_num(ablated, "avg_tokens_used")
        base_median_accuracy = get_num(base, "median_accuracy_score")
        ablated_median_accuracy = get_num(ablated, "median_accuracy_score")
        base_median_speed = get_num(base, "median_speed_score")
        ablated_median_speed = get_num(ablated, "median_speed_score")
        base_median_tokens = get_num(base, "median_tokens_used")
        ablated_median_tokens = get_num(ablated, "median_tokens_used")

        accuracy_drop = None if base_accuracy is None or ablated_accuracy is None else round(base_accuracy - ablated_accuracy, 4)
        speed_drop = None if base_speed is None or ablated_speed is None else round(base_speed - ablated_speed, 4)
        token_increase_ratio = None
        if base_tokens is not None and ablated_tokens is not None:
            token_increase_ratio = round(max(0.0, ablated_tokens - base_tokens) / max(base_tokens, 1.0), 4)

        median_accuracy_drop = None
        if base_median_accuracy is not None and ablated_median_accuracy is not None:
            median_accuracy_drop = round(base_median_accuracy - ablated_median_accuracy, 4)
        median_speed_drop = None
        if base_median_speed is not None and ablated_median_speed is not None:
            median_speed_drop = round(base_median_speed - ablated_median_speed, 4)
        median_token_increase_ratio = None
        if base_median_tokens is not None and ablated_median_tokens is not None:
            median_token_increase_ratio = round(max(0.0, ablated_median_tokens - base_median_tokens) / max(base_median_tokens, 1.0), 4)

        def impact_score(acc: float | None, spd: float | None, tok: float | None) -> float | None:
            parts = [part for part in (acc, spd, tok) if part is not None]
            if not parts:
                return None
            score = 0.0
            if acc is not None:
                score += 0.4 * max(0.0, acc)
            if spd is not None:
                score += 0.3 * max(0.0, spd)
            if tok is not None:
                score += 0.3 * max(0.0, tok)
            return round(score, 4)

        avg_score = impact_score(accuracy_drop, speed_drop, token_increase_ratio)
        median_score = impact_score(median_accuracy_drop, median_speed_drop, median_token_increase_ratio)
        combined_score = None
        if avg_score is not None and median_score is not None:
            combined_score = round((avg_score + median_score) / 2, 4)
        elif avg_score is not None:
            combined_score = avg_score
        elif median_score is not None:
            combined_score = median_score

        impacts.append({
            "field": field,
            "base_variant": base_variant,
            "ablated_variant": ablated_variant,
            "avg_accuracy_drop": accuracy_drop,
            "avg_speed_drop": speed_drop,
            "avg_token_increase_ratio": token_increase_ratio,
            "median_accuracy_drop": median_accuracy_drop,
            "median_speed_drop": median_speed_drop,
            "median_token_increase_ratio": median_token_increase_ratio,
            "avg_impact_score": avg_score,
            "median_impact_score": median_score,
            "impact_score": combined_score,
        })
    impacts.sort(
        key=lambda row: (
            row["impact_score"] is None,
            -(row["impact_score"] or 0.0),
            row["field"],
        )
    )
    return impacts
