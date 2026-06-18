#!/usr/bin/env python3
"""Dependency-free grader for the OKF agent evaluation fixture."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


class GraderError(Exception):
    """Raised when inputs are malformed enough to stop grading."""


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _parse_scalar(value: str) -> Any:
    value = _strip_quotes(value.strip())
    lower = value.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    if lower in {"null", "none"}:
        return None
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    return value


def parse_frontmatter(text: str) -> tuple[dict[str, Any] | None, str]:
    """Parse a small YAML-frontmatter subset used by this fixture.

    Supported YAML is intentionally conservative: top-level key/value pairs and
    top-level lists of scalars. That keeps the grader portable and makes
    malformed fixture metadata fail loudly.
    """
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        raise GraderError("unterminated YAML frontmatter")
    raw = text[4:end]
    body = text[end + 5 :]
    data: dict[str, Any] = {}
    current_list: str | None = None
    for line_no, line in enumerate(raw.splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - "):
            if current_list is None:
                raise GraderError(f"list item without key on frontmatter line {line_no}")
            data[current_list].append(_parse_scalar(line[4:]))
            continue
        if line.startswith((" ", "\t")):
            raise GraderError(f"unsupported nested YAML on frontmatter line {line_no}")
        if ":" not in line:
            raise GraderError(f"invalid frontmatter line {line_no}: {line!r}")
        key, value = line.split(":", 1)
        key = key.strip()
        if not key:
            raise GraderError(f"empty key on frontmatter line {line_no}")
        value = value.strip()
        if value == "":
            data[key] = []
            current_list = key
        else:
            data[key] = _parse_scalar(value)
            current_list = None
    return data, body


def _bundle_path(path: Path, bundle: Path) -> str:
    return "/" + path.relative_to(bundle).as_posix()


def validate_bundle(bundle: Path, *, mode: str) -> dict[str, Any]:
    """Validate parseability and strict/extension OKF index behavior."""
    if not bundle.exists():
        raise GraderError(f"bundle not found: {bundle}")
    if mode not in {"strict", "extension"}:
        raise GraderError("mode must be strict or extension")

    errors: list[str] = []
    concepts: dict[str, dict[str, Any]] = {}
    index_files = sorted(bundle.rglob("index.md"))
    if bundle / "index.md" not in index_files:
        errors.append("missing root index.md")

    for path in sorted(bundle.rglob("*.md")):
        rel = _bundle_path(path, bundle)
        try:
            fm, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        except GraderError as exc:
            errors.append(f"{rel}: {exc}")
            continue

        name = path.name
        is_reserved = name in {"index.md", "log.md"}
        if is_reserved:
            if mode == "strict" and fm is not None and path != bundle / "index.md":
                errors.append(f"{rel}: strict mode forbids frontmatter on reserved file")
            if path == bundle / "index.md" and fm is not None:
                extra = set(fm) - {"okf_version", "schema"}
                if mode == "strict" and extra:
                    errors.append(f"{rel}: root index frontmatter has non-OKF keys {sorted(extra)}")
            continue

        if fm is None:
            errors.append(f"{rel}: concept file missing YAML frontmatter")
            continue
        if not isinstance(fm.get("type"), str) or not fm["type"].strip():
            errors.append(f"{rel}: concept frontmatter missing non-empty type")
        if not body.strip():
            errors.append(f"{rel}: concept body is empty")
        concepts[rel] = fm

    return {
        "parseability": "pass" if not errors else "fail",
        "mode": mode,
        "concept_count": len(concepts),
        "index_count": len(index_files),
        "errors": errors,
    }


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _contains_any(haystack: str, needles: list[str]) -> bool:
    normalized = _norm(haystack)
    return any(_norm(needle) in normalized for needle in needles)


def _submission_facts(submission: dict[str, Any], expected_keys: set[str]) -> dict[str, Any]:
    facts = submission.get("facts")
    if isinstance(facts, dict):
        return facts
    return {
        key: submission[key]
        for key in expected_keys
        if key in submission
    }


def _normalize_trace_path(raw_path: str, bundle: Path | None) -> str | None:
    path = raw_path.strip()
    if bundle is not None:
        bundle_root = str(bundle.resolve())
        if path.startswith(bundle_root + "/"):
            return "/" + Path(path).resolve().relative_to(bundle.resolve()).as_posix()
        if path.startswith("/") and path not in {"/index.md"} and not path.endswith(".md"):
            return None
    if not path.startswith("/"):
        path = "/" + path
    return path


def _read_event_paths(trace: dict[str, Any], bundle: Path | None = None) -> list[tuple[str, float | None]]:
    paths: list[tuple[str, float | None]] = []
    for event in trace.get("events", []):
        if not isinstance(event, dict):
            continue
        event_type = _norm(event.get("type") or event.get("event"))
        if event_type not in {"read", "open", "read_file", "file_read", "file-read", "view", "inspect"}:
            continue
        raw_path = event.get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            continue
        path = _normalize_trace_path(raw_path, bundle)
        if path is None:
            continue
        ts_raw = event.get("ts_ms")
        ts_ms = float(ts_raw) if isinstance(ts_raw, (int, float)) else None
        paths.append((path, ts_ms))
    return paths


def _trace_duration_ms(trace: dict[str, Any], paths: list[tuple[str, float | None]]) -> float | None:
    duration = trace.get("duration_ms")
    if isinstance(duration, (int, float)) and duration >= 0:
        return float(duration)
    times = [ts for _, ts in paths if ts is not None]
    if len(times) >= 2:
        return max(times) - min(times)
    return None


def score_trace(task: dict[str, Any], trace_path: Path, *, bundle: Path | None = None) -> dict[str, Any]:
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    if not isinstance(trace, dict):
        raise GraderError("trace must be a JSON object")

    paths = _read_event_paths(trace, bundle)
    unique_paths = []
    seen = set()
    for path, _ in paths:
        if path not in seen:
            seen.add(path)
            unique_paths.append(path)

    required = set(task.get("required_citations", []))
    expected = task.get("trace_expectations", {})
    relevant = required | set(expected.get("relevant_paths", []))
    navigation = {
        p for p in unique_paths
        if p == "/index.md" or p.endswith("/index.md")
    }
    distractor_paths = set(expected.get("distractor_paths", []))
    duration_ms = _trace_duration_ms(trace, paths)
    max_unique = expected.get("max_unique_files_read", 14)
    target_duration = expected.get("target_duration_ms", 120000)

    required_read = required & set(unique_paths)
    missing_required = sorted(required - required_read)
    irrelevant_paths = sorted(set(unique_paths) - relevant - navigation)
    distractor_hits = sorted(set(unique_paths) & distractor_paths)

    completeness = len(required_read) / len(required) if required else 1.0
    efficiency = min(1.0, float(max_unique) / len(unique_paths)) if unique_paths else 0.0
    speed_score = min(1.0, float(target_duration) / duration_ms) if duration_ms and duration_ms > 0 else 0.0
    no_distractors = 0.0 if distractor_hits else 1.0
    trace_score = round(
        (0.50 * completeness) + (0.25 * efficiency) + (0.25 * no_distractors),
        4,
    )

    return {
        "trace_score": trace_score,
        "speed_score": round(speed_score, 4),
        "duration_ms": duration_ms,
        "unique_files_read": len(unique_paths),
        "total_read_events": len(paths),
        "required_files_read": len(required_read),
        "missing_required_files": missing_required,
        "irrelevant_files_read": irrelevant_paths,
        "distractor_files_read": distractor_hits,
        "first_required_read_ms": min(
            (ts for path, ts in paths if path in required and ts is not None),
            default=None,
        ),
    }


def score_submission(
    bundle: Path,
    task_path: Path,
    submission_path: Path,
    *,
    mode: str,
    trace_path: Path | None = None,
) -> dict[str, Any]:
    validation = validate_bundle(bundle, mode=mode)
    task = json.loads(task_path.read_text(encoding="utf-8"))
    submission = json.loads(submission_path.read_text(encoding="utf-8"))

    expected = task["expected_facts"]
    submitted_facts = _submission_facts(submission, set(expected))
    missing: list[str] = []
    incorrect: list[str] = []
    matched = 0

    for key, spec in expected.items():
        accepted = spec["accepted"]
        got = submitted_facts.get(key)
        if got is None:
            missing.append(key)
            continue
        if _contains_any(got, accepted):
            matched += 1
        else:
            incorrect.append(key)

    answer_blob = " ".join([
        str(submission.get("answer", "")),
        " ".join(str(v) for v in submitted_facts.values()),
    ])
    distractor_hits = [
        term for term in task.get("distractors", [])
        if _contains_any(answer_blob, [term])
    ]

    citations = {
        str(c).strip()
        for c in submission.get("citations", [])
        if isinstance(c, str) and str(c).strip()
    }
    required_citations = set(task.get("required_citations", []))
    existing_required = {
        c for c in required_citations
        if (bundle / c.lstrip("/")).exists()
    }
    missing_citations = sorted(required_citations - citations)
    broken_required_citations = sorted(required_citations - existing_required)
    citation_score = (
        len(required_citations - set(missing_citations)) / len(required_citations)
        if required_citations else 1.0
    )
    accuracy_score = matched / len(expected) if expected else 1.0
    if distractor_hits:
        accuracy_score = max(0.0, accuracy_score - task.get("distractor_penalty", 0.2))
    parseability_score = 1.0 if validation["parseability"] == "pass" else 0.0
    trace_result = score_trace(task, trace_path, bundle=bundle) if trace_path else None
    if trace_result:
        total_score = round(
            (0.50 * accuracy_score)
            + (0.20 * citation_score)
            + (0.10 * parseability_score)
            + (0.20 * trace_result["trace_score"]),
            4,
        )
    else:
        total_score = round(
            (0.60 * accuracy_score) + (0.25 * citation_score) + (0.15 * parseability_score),
            4,
        )

    result = {
        "parseability": validation["parseability"],
        "accuracy_score": round(accuracy_score, 4),
        "citation_score": round(citation_score, 4),
        "total_score": total_score,
        "missing": missing,
        "incorrect": incorrect,
        "missing_citations": missing_citations,
        "broken_required_citations": broken_required_citations,
        "distractor_hits": distractor_hits,
        "validation_errors": validation["errors"],
    }
    if trace_result:
        result.update(trace_result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--task", type=Path)
    parser.add_argument("--submission", type=Path)
    parser.add_argument("--trace", type=Path, help="Optional agent trace JSON for path and speed scoring")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--strict", action="store_true", help="Validate strict OKF behavior")
    group.add_argument("--extension", action="store_true", help="Allow index frontmatter extension")
    args = parser.parse_args()

    mode = "extension" if args.extension else "strict"
    try:
        if args.trace and not (args.task and args.submission):
            raise GraderError("--trace requires --task and --submission")
        if args.task and args.submission:
            result = score_submission(
                args.bundle,
                args.task,
                args.submission,
                mode=mode,
                trace_path=args.trace,
            )
        else:
            result = validate_bundle(args.bundle, mode=mode)
    except (GraderError, json.JSONDecodeError) as exc:
        result = {"parseability": "fail", "error": str(exc)}
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("parseability") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
