#!/usr/bin/env python3
"""Run an external agent command against one OKF bundle and grade the result."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from grader import score_submission


EXPECTED_FACT_ALIASES: dict[str, tuple[str, ...]] = {
    "affected_kpi": ("affected_metric", "metric", "kpi"),
    "affected_segment": ("affected_business_segment", "segment"),
    "correct_join_key": ("join_key", "correct_key"),
    "impacted_asset": ("impacted_view", "impacted_table", "asset"),
    "pipeline": ("rollout_id", "deployment_id", "feature_flag"),
}


def _load_task_spec(task: Path) -> dict[str, Any]:
    return json.loads(task.read_text(encoding="utf-8"))


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _extract_join_key(text: str) -> str | None:
    match = re.search(r"instead of\s+`?([a-z0-9_.-]+)`?", text, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def _find_accepted_value(texts: list[str], accepted_values: list[str]) -> str | None:
    normalized_texts = [_normalize_text(text) for text in texts if text]
    for accepted in accepted_values:
        normalized_accepted = _normalize_text(accepted)
        if any(normalized_accepted in text for text in normalized_texts):
            return accepted
    return None


TOKEN_USAGE_RE = re.compile(r"(?i)\btokens used\b(?:\s*[:=]?\s*(?P<count>[\d,]+))?")


def _extract_tokens_used(stderr: str) -> int | None:
    lines = stderr.splitlines()
    for index, line in enumerate(lines):
        match = TOKEN_USAGE_RE.search(line)
        if not match:
            continue
        count = match.group("count")
        if count:
            return int(count.replace(",", ""))
        for follow in lines[index + 1 : index + 4]:
            follow = follow.strip()
            if not follow:
                continue
            number = re.fullmatch(r"[\d,]+", follow)
            if number:
                return int(number.group(0).replace(",", ""))
        return None
    return None


def _normalize_submission(submission: dict[str, Any], task_spec: dict[str, Any]) -> dict[str, Any]:
    expected_facts = task_spec.get("expected_facts") or {}
    expected_fact_keys = list(expected_facts.keys())

    raw_facts: dict[str, Any] = {}
    if isinstance(submission.get("facts"), dict):
        raw_facts.update(submission["facts"])

    # Accept top-level aliasing as a fallback, then rewrite to the canonical schema.
    for canonical_key, aliases in EXPECTED_FACT_ALIASES.items():
        if canonical_key not in raw_facts:
            for alias in aliases:
                if alias in raw_facts:
                    raw_facts[canonical_key] = raw_facts[alias]
                    break
        if canonical_key not in raw_facts and canonical_key in submission:
            raw_facts[canonical_key] = submission[canonical_key]
        if canonical_key not in raw_facts:
            for alias in aliases:
                if alias in submission:
                    raw_facts[canonical_key] = submission[alias]
                    break

    text_sources = [
        str(submission.get("answer") or ""),
        json.dumps(submission.get("facts") or {}, sort_keys=True),
        json.dumps({k: v for k, v in submission.items() if k not in {"facts", "citations"}}, sort_keys=True),
    ]
    text_sources.extend(str(value) for value in raw_facts.values())

    normalized_facts: dict[str, Any] = {}
    for key in expected_fact_keys:
        value = raw_facts.get(key)
        if isinstance(value, str) and value.strip():
            normalized_facts[key] = value.strip()
            continue

        accepted_values = expected_facts.get(key, {}).get("accepted") or []
        if accepted_values:
            matched = _find_accepted_value(text_sources, accepted_values)
            if matched:
                normalized_facts[key] = matched
                continue

        if key == "correct_join_key":
            extracted = _extract_join_key(" ".join(text_sources))
            if extracted:
                normalized_facts[key] = extracted
                continue

    normalized = dict(submission)
    normalized["facts"] = normalized_facts
    for key in EXPECTED_FACT_ALIASES:
        normalized.pop(key, None)
    return normalized


def _build_prompt(bundle: Path, task: Path, variant: str, task_spec: dict[str, Any]) -> str:
    facts_spec = task_spec.get("expected_facts") or {}
    fact_keys = list(facts_spec) or list(task_spec.get("fact_keys") or [])
    fact_lines = [f'- "{key}": "value found in the OKF bundle"' for key in fact_keys]
    fact_schema = "\n".join(fact_lines)
    task_prompt = task_spec.get("prompt") or ""
    task_id = task_spec.get("task_id") or "retail-margin-anomaly-v1"
    return f"""You are being evaluated on an OKF-style knowledge bundle.

Bundle path: {bundle}
Task path: {task}
Bundle variant: {variant}

Task id: {task_id}
Task prompt: {task_prompt}

Work independently. Inspect only files needed under the bundle path. The task
file is runner metadata and must not be used as a source of answer facts.
Produce exactly two JSON objects and no markdown fences:

1. Submission object:
{{
  "task_id": "{task_id}",
  "bundle_variant": "{variant}",
  "answer": "short synthesized answer",
  "facts": {{
{fact_schema}
  }},
  "citations": ["/path/inside/bundle.md"]
}}

Use the fact keys exactly as shown. Do not substitute aliases like
`affected_metric` or `rollout_id`.

2. Trace object:
{{
  "agent": "agent name",
  "bundle_variant": "{variant}",
  "events": [
    {{"type": "read", "path": "/index.md"}}
  ]
}}

Trace paths should be bundle-relative paths beginning with "/". Do not include
explanatory prose outside the two JSON objects.
"""


class RunnerError(Exception):
    """Raised when the runner cannot get gradeable agent output."""


def _json_objects(text: str) -> list[Any]:
    decoder = json.JSONDecoder()
    out: list[Any] = []
    idx = 0
    while idx < len(text):
        start_candidates = [pos for pos in (text.find("{", idx), text.find("[", idx)) if pos != -1]
        if not start_candidates:
            break
        start = min(start_candidates)
        try:
            obj, end = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            idx = start + 1
            continue
        out.append(obj)
        idx = start + end
    return out


def _pick_outputs(stdout: str) -> tuple[dict[str, Any], dict[str, Any]]:
    submission: dict[str, Any] | None = None
    trace: dict[str, Any] | None = None
    for obj in _json_objects(stdout):
        if not isinstance(obj, dict):
            continue
        if trace is None and isinstance(obj.get("events"), list):
            trace = obj
            continue
        if submission is None and (
            obj.get("task_id") or obj.get("citations") or obj.get("facts")
        ):
            submission = obj
    if submission is None:
        raise RunnerError("agent stdout did not contain a submission JSON object")
    if trace is None:
        trace = {
            "agent": "unknown",
            "events": [],
            "trace_warning": "agent stdout did not contain a trace JSON object",
        }
    return submission, trace


def _as_event(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize a runtime/tool log item into benchmark trace event shape."""
    event = raw
    if isinstance(raw.get("tool_call"), dict):
        event = {**raw, **raw["tool_call"]}

    args = event.get("args") or event.get("arguments") or event.get("input") or {}
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            args = {}
    if not isinstance(args, dict):
        args = {}

    kind = str(
        event.get("type")
        or event.get("event")
        or event.get("action")
        or event.get("tool")
        or event.get("name")
        or ""
    ).lower()
    path = (
        event.get("path")
        or event.get("file")
        or event.get("file_path")
        or event.get("filepath")
        or event.get("target")
        or args.get("path")
        or args.get("file")
        or args.get("file_path")
        or args.get("filepath")
        or args.get("target")
    )
    if not isinstance(path, str) or not path.strip():
        return None
    if not any(token in kind for token in ("read", "open", "view", "inspect", "cat", "sed")):
        if not path.endswith(".md"):
            return None
        kind = "read"

    out: dict[str, Any] = {"type": "read", "path": path}
    ts_ms = event.get("ts_ms") or event.get("timestamp_ms") or event.get("elapsed_ms")
    if isinstance(ts_ms, (int, float)):
        out["ts_ms"] = ts_ms
    source = event.get("source")
    if isinstance(source, str):
        out["source"] = source
    return out


def _read_events_from_json_text(text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    stripped = text.strip()
    if not stripped:
        return events

    parsed_whole = None
    try:
        parsed_whole = json.loads(stripped)
    except json.JSONDecodeError:
        parsed_whole = None
    if isinstance(parsed_whole, list):
        for item in parsed_whole:
            if isinstance(item, dict):
                event = _as_event(item)
                if event:
                    events.append(event)
        return events
    if isinstance(parsed_whole, dict):
        items = parsed_whole.get("events") if isinstance(parsed_whole.get("events"), list) else [parsed_whole]
        for item in items:
            if isinstance(item, dict):
                event = _as_event(item)
                if event:
                    events.append(event)
        return events

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("OKF_TRACE:"):
            line = line[len("OKF_TRACE:"):].strip()
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            if isinstance(item.get("events"), list):
                for nested in item["events"]:
                    if isinstance(nested, dict):
                        event = _as_event(nested)
                        if event:
                            events.append(event)
            else:
                event = _as_event(item)
                if event:
                    events.append(event)
    return events


def _read_runtime_events(paths: list[Path], stdout: str, stderr: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for path in paths:
        if path.exists():
            events.extend(_read_events_from_json_text(path.read_text(encoding="utf-8")))
    marker_lines = "\n".join(
        line for line in (stdout + "\n" + stderr).splitlines()
        if line.strip().startswith("OKF_TRACE:")
    )
    events.extend(_read_events_from_json_text(marker_lines))
    return events


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_agent(args: argparse.Namespace) -> dict[str, Any]:
    bundle = args.bundle.resolve()
    task = args.task.resolve()
    grade_task_arg = getattr(args, "grade_task", None) or args.task
    grade_task = grade_task_arg.resolve()
    task_spec = _load_task_spec(task)
    grade_task_spec = _load_task_spec(grade_task)
    output_dir = args.output_dir.resolve()
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = output_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    prompt = _build_prompt(bundle, task, args.variant, task_spec)
    cmd = shlex.split(args.agent_cmd)
    default_tool_log = run_dir / "tool-events.jsonl"
    tool_log_paths = [default_tool_log]
    if args.tool_log:
        tool_log_paths.append(args.tool_log.resolve())
    env = os.environ.copy()
    env.update({
        "OKF_TRACE_LOG": str(default_tool_log),
        "OKF_BUNDLE_PATH": str(bundle),
        "OKF_TASK_PATH": str(task),
        "OKF_BUNDLE_VARIANT": args.variant,
    })
    start = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            text=True,
            capture_output=True,
            timeout=args.timeout_s,
            cwd=str(args.cwd.resolve()) if args.cwd else None,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        duration_ms = round((time.monotonic() - start) * 1000, 3)
        _write_json(run_dir / "runner.json", {
            "status": "timeout",
            "duration_ms": duration_ms,
            "timeout_s": args.timeout_s,
            "cmd": cmd,
        })
        raise RunnerError(f"agent command timed out after {args.timeout_s}s") from exc

    duration_ms = round((time.monotonic() - start) * 1000, 3)
    (run_dir / "stdout.txt").write_text(proc.stdout, encoding="utf-8")
    (run_dir / "stderr.txt").write_text(proc.stderr, encoding="utf-8")
    _write_json(run_dir / "runner.json", {
        "status": "completed",
        "returncode": proc.returncode,
        "duration_ms": duration_ms,
        "cmd": cmd,
        "bundle": str(bundle),
        "task": str(task),
        "grade_task": str(grade_task),
        "variant": args.variant,
    })
    if proc.returncode != 0 and not args.allow_nonzero:
        raise RunnerError(f"agent command exited with {proc.returncode}; see {run_dir / 'stderr.txt'}")

    submission, trace = _pick_outputs(proc.stdout)
    submission = _normalize_submission(submission, grade_task_spec)
    tokens_used = _extract_tokens_used(proc.stderr)
    runtime_events = _read_runtime_events(tool_log_paths, proc.stdout, proc.stderr)
    if runtime_events:
        trace["events"] = runtime_events
        trace["trace_source"] = "runtime-log"
    else:
        trace.setdefault("trace_source", "agent-reported")
    trace["duration_ms"] = duration_ms
    trace.setdefault("runner_recorded_duration", True)
    _write_json(run_dir / "submission.json", submission)
    _write_json(run_dir / "trace.json", trace)

    grade = score_submission(
        bundle,
        grade_task,
        run_dir / "submission.json",
        mode=args.mode,
        trace_path=run_dir / "trace.json",
    )
    if tokens_used is not None:
        grade["tokens_used"] = tokens_used
    runner_data = json.loads((run_dir / "runner.json").read_text(encoding="utf-8"))
    runner_data["tokens_used"] = tokens_used
    _write_json(run_dir / "runner.json", runner_data)
    _write_json(run_dir / "grade.json", grade)
    return {"run_dir": str(run_dir), "grade": grade, "tokens_used": tokens_used}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--task", default=Path("tasks/synthesis.json"), type=Path)
    parser.add_argument("--grade-task", type=Path, help="Private grading task spec; defaults to --task")
    parser.add_argument("--variant", required=True)
    parser.add_argument("--mode", choices=["strict", "extension"], required=True)
    parser.add_argument("--agent-cmd", required=True, help="Command that reads the prompt on stdin")
    parser.add_argument("--output-dir", default=Path("runs"), type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--timeout-s", default=600, type=float)
    parser.add_argument("--cwd", type=Path)
    parser.add_argument("--tool-log", type=Path, help="Optional runtime event JSON/JSONL file to ingest after the run")
    parser.add_argument("--allow-nonzero", action="store_true")
    args = parser.parse_args()

    try:
        result = run_agent(args)
    except (RunnerError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}, indent=2, sort_keys=True))
        return 2
    print(json.dumps({"status": "pass", **result}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
