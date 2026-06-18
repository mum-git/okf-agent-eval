#!/usr/bin/env python3
"""Run repeated OKF benchmark iterations across bundle variants."""

from __future__ import annotations

import argparse
import json
import statistics
import random
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from agent_runner import RunnerError, run_agent


ROOT = Path(__file__).resolve().parent

VARIANTS = {
    "strict": {
        "bundle": ROOT / "bundles/strict-retail-ops",
        "mode": "strict",
    },
    "extended": {
        "bundle": ROOT / "bundles/extended-retail-ops",
        "mode": "extension",
    },
    "uniform-yaml": {
        "bundle": ROOT / "bundles/uniform-yaml-retail-ops",
        "mode": "extension",
    },
}


def _job_args(args: argparse.Namespace, variant: str, iteration: int, batch_dir: Path) -> SimpleNamespace:
    spec = VARIANTS[variant]
    counted = iteration > 0
    run_label = f"iter-{iteration:03d}" if counted else f"warmup-{abs(iteration):03d}"
    output_root = batch_dir / variant
    if not counted:
        output_root = batch_dir / "_warmup" / variant
    return SimpleNamespace(
        bundle=spec["bundle"],
        task=args.task,
        variant=variant,
        mode=spec["mode"],
        agent_cmd=args.agent_cmd,
        output_dir=output_root,
        run_id=run_label,
        timeout_s=args.timeout_s,
        cwd=args.cwd,
        tool_log=None,
        allow_nonzero=args.allow_nonzero,
        counted=counted,
    )


def _run_one(job: SimpleNamespace) -> dict[str, Any]:
    try:
        result = run_agent(job)
        return {
            "variant": job.variant,
            "iteration": job.run_id,
            "status": "pass",
            "counted": job.counted,
            "run_dir": result["run_dir"],
            "grade": result["grade"],
        }
    except (RunnerError, json.JSONDecodeError, FileExistsError) as exc:
        return {
            "variant": job.variant,
            "iteration": job.run_id,
            "status": "fail",
            "counted": job.counted,
            "error": str(exc),
        }


def _mean(values: list[float]) -> float | None:
    return round(statistics.mean(values), 4) if values else None


def _median(values: list[float]) -> float | None:
    return round(statistics.median(values), 4) if values else None


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1)))))
    return round(ordered[index], 4)


def _trace_read_paths(trace_path: Path) -> list[str]:
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    if not isinstance(trace, dict):
        return []

    paths: list[str] = []
    for event in trace.get("events", []):
        if not isinstance(event, dict):
            continue
        event_type = str(event.get("type") or event.get("event") or "").strip().lower()
        if event_type not in {"read", "open", "read_file", "file_read", "file-read", "view", "inspect"}:
            continue
        raw_path = event.get("path")
        if not isinstance(raw_path, str):
            continue
        path = raw_path.strip()
        if not path:
            continue
        if not path.startswith("/"):
            path = "/" + path
        paths.append(path)
    return paths


def _iteration_sort_key(row: dict[str, Any]) -> tuple[int, int, str]:
    iteration = str(row.get("iteration", ""))
    if iteration.startswith("warmup-"):
        try:
            return (0, int(iteration.split("-", 1)[1]), iteration)
        except (IndexError, ValueError):
            return (0, 0, iteration)
    if iteration.startswith("iter-"):
        try:
            return (1, int(iteration.split("-", 1)[1]), iteration)
        except (IndexError, ValueError):
            return (1, 0, iteration)
    return (2, 0, iteration)


def _annotate_cache_metrics(results: list[dict[str, Any]]) -> None:
    by_variant: dict[str, list[dict[str, Any]]] = {}
    for row in results:
        by_variant.setdefault(row["variant"], []).append(row)

    for rows in by_variant.values():
        seen_paths: set[str] = set()
        for row in sorted(rows, key=_iteration_sort_key):
            if row.get("status") != "pass":
                continue
            run_dir = row.get("run_dir")
            if not isinstance(run_dir, str) or not run_dir:
                continue
            trace_path = Path(run_dir) / "trace.json"
            if not trace_path.exists():
                continue
            read_paths = _trace_read_paths(trace_path)
            cache_hit_reads = sum(1 for path in read_paths if path in seen_paths)
            cache_cold_reads = len(read_paths) - cache_hit_reads
            cache_hit_rate = round(cache_hit_reads / len(read_paths), 4) if read_paths else None
            cache_state = "warm" if cache_hit_reads > 0 else "cold"

            grade = row.setdefault("grade", {})
            grade["cache_hit_reads"] = cache_hit_reads
            grade["cache_cold_reads"] = cache_cold_reads
            grade["cache_hit_rate"] = cache_hit_rate
            grade["cache_state"] = cache_state
            row["cache_hit_reads"] = cache_hit_reads
            row["cache_cold_reads"] = cache_cold_reads
            row["cache_hit_rate"] = cache_hit_rate
            row["cache_state"] = cache_state
            seen_paths.update(read_paths)


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_variant: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        by_variant.setdefault(result["variant"], []).append(result)

    summary: dict[str, Any] = {}
    for variant, rows in sorted(by_variant.items()):
        passed = [row for row in rows if row["status"] == "pass"]
        grades = [row["grade"] for row in passed]
        ordered_rows = sorted(passed, key=lambda row: str(row.get("iteration", "")))
        durations = [
            g["duration_ms"] for g in grades
            if isinstance(g.get("duration_ms"), (int, float))
        ]
        token_values = [
            g["tokens_used"] for g in grades
            if isinstance(g.get("tokens_used"), (int, float))
        ]
        cache_hit_reads = [
            g["cache_hit_reads"] for g in grades
            if isinstance(g.get("cache_hit_reads"), (int, float))
        ]
        cache_cold_reads = [
            g["cache_cold_reads"] for g in grades
            if isinstance(g.get("cache_cold_reads"), (int, float))
        ]
        cache_hit_rates = [
            g["cache_hit_rate"] for g in grades
            if isinstance(g.get("cache_hit_rate"), (int, float))
        ]
        cold_grades = [
            g for g in grades
            if g.get("cache_state") == "cold" and isinstance(g.get("duration_ms"), (int, float))
        ]
        warm_grades = [
            g for g in grades
            if g.get("cache_state") == "warm" and isinstance(g.get("duration_ms"), (int, float))
        ]
        correct_grades = [
            g for g in grades
            if g.get("accuracy_score") == 1.0 and isinstance(g.get("tokens_used"), (int, float))
        ]
        tail_durations = [
            row["grade"]["duration_ms"]
            for row in ordered_rows[1:]
            if isinstance(row.get("grade", {}).get("duration_ms"), (int, float))
        ]
        summary[variant] = {
            "runs": len(rows),
            "passed": len(passed),
            "failed": len(rows) - len(passed),
            "avg_total_score": _mean([g["total_score"] for g in grades]),
            "median_total_score": _median([g["total_score"] for g in grades]),
            "avg_accuracy_score": _mean([g["accuracy_score"] for g in grades]),
            "median_accuracy_score": _median([g["accuracy_score"] for g in grades]),
            "avg_citation_score": _mean([g["citation_score"] for g in grades]),
            "median_citation_score": _median([g["citation_score"] for g in grades]),
            "avg_trace_score": _mean([g.get("trace_score", 0.0) for g in grades]),
            "median_trace_score": _median([g.get("trace_score", 0.0) for g in grades]),
            "avg_speed_score": _mean([g.get("speed_score", 0.0) for g in grades]),
            "median_speed_score": _median([g.get("speed_score", 0.0) for g in grades]),
            "avg_tokens_used": _mean(token_values),
            "median_tokens_used": _median(token_values),
            "p95_tokens_used": _p95(token_values),
            "correct_answer_count": len(correct_grades),
            "tokens_per_correct_answer": _mean([g["tokens_used"] for g in correct_grades]),
            "avg_cache_hit_reads": _mean(cache_hit_reads),
            "median_cache_hit_reads": _median(cache_hit_reads),
            "avg_cache_cold_reads": _mean(cache_cold_reads),
            "median_cache_cold_reads": _median(cache_cold_reads),
            "avg_cache_hit_rate": _mean(cache_hit_rates),
            "median_cache_hit_rate": _median(cache_hit_rates),
            "cold_run_count": len(cold_grades),
            "warm_run_count": len(warm_grades),
            "avg_cold_duration_ms": _mean([g["duration_ms"] for g in cold_grades]),
            "median_cold_duration_ms": _median([g["duration_ms"] for g in cold_grades]),
            "avg_warm_duration_ms": _mean([g["duration_ms"] for g in warm_grades]),
            "median_warm_duration_ms": _median([g["duration_ms"] for g in warm_grades]),
            "avg_duration_ms": _mean(durations),
            "median_duration_ms": _median(durations),
            "p95_duration_ms": _p95(durations),
            "first_duration_ms": round(ordered_rows[0]["grade"]["duration_ms"], 4) if ordered_rows else None,
            "steady_state_avg_duration_ms": _mean(tail_durations),
            "steady_state_median_duration_ms": _median(tail_durations),
            "avg_unique_files_read": _mean([g.get("unique_files_read", 0) for g in grades]),
            "median_unique_files_read": _median([g.get("unique_files_read", 0) for g in grades]),
            "avg_distractor_files_read": _mean([len(g.get("distractor_files_read", [])) for g in grades]),
            "median_distractor_files_read": _median([len(g.get("distractor_files_read", [])) for g in grades]),
        }
    return summary


def _build_ranking(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    token_baseline = min(
        (
            variant_summary.get("avg_tokens_used")
            for variant_summary in summary.values()
            if isinstance(variant_summary.get("avg_tokens_used"), (int, float)) and variant_summary.get("avg_tokens_used") > 0
        ),
        default=None,
    )

    for variant, variant_summary in summary.items():
        avg_accuracy = variant_summary.get("avg_accuracy_score")
        avg_speed = variant_summary.get("avg_speed_score")
        avg_tokens = variant_summary.get("avg_tokens_used")
        if not all(isinstance(value, (int, float)) for value in (avg_accuracy, avg_speed, avg_tokens)):
            continue
        if avg_tokens <= 0:
            continue
        token_efficiency = (token_baseline / avg_tokens) if token_baseline else None
        composite = (
            round((float(avg_accuracy) + float(avg_speed) + float(token_efficiency)) / 3, 4)
            if token_efficiency is not None
            else None
        )
        rows.append({
            "variant": variant,
            "avg_accuracy_score": round(float(avg_accuracy), 4),
            "avg_speed_score": round(float(avg_speed), 4),
            "avg_tokens_used": round(float(avg_tokens), 4),
            "token_efficiency": round(float(token_efficiency), 4) if token_efficiency is not None else None,
            "composite_score": composite,
        })

    rows.sort(
        key=lambda row: (
            -(row["composite_score"] or 0.0),
            -(row["avg_accuracy_score"] or 0.0),
            -(row["avg_speed_score"] or 0.0),
            row["avg_tokens_used"] or float("inf"),
            row["variant"],
        )
    )
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    return rows


def _format_ranking_table(ranking: list[dict[str, Any]]) -> str:
    lines = [
        "| Rank | Variant | Accuracy | Speed | Avg Tokens | Token Efficiency | Composite |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in ranking:
        lines.append(
            "| {rank} | {variant} | {accuracy:.4f} | {speed:.4f} | {tokens:.2f} | {efficiency:.4f} | {composite:.4f} |".format(
                rank=row["rank"],
                variant=row["variant"],
                accuracy=row["avg_accuracy_score"],
                speed=row["avg_speed_score"],
                tokens=row["avg_tokens_used"],
                efficiency=row["token_efficiency"] or 0.0,
                composite=row["composite_score"] or 0.0,
            )
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", default=ROOT / "tasks/enterprise-fnf-synthesis.json", type=Path)
    parser.add_argument("--agent-cmd", required=True)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--variants", nargs="+", choices=sorted(VARIANTS), default=sorted(VARIANTS))
    parser.add_argument("--jobs", type=int, default=1, help="Concurrent agent runs")
    parser.add_argument("--output-dir", default=Path("runs"), type=Path)
    parser.add_argument("--batch-id")
    parser.add_argument("--timeout-s", type=float, default=900)
    parser.add_argument("--cwd", type=Path)
    parser.add_argument("--allow-nonzero", action="store_true")
    parser.add_argument("--warmup-runs", type=int, default=0, help="Uncounted warmup runs per variant")
    parser.add_argument("--shuffle-variants", action="store_true", help="Shuffle variant order independently per iteration")
    parser.add_argument("--seed", type=int, help="Random seed for variant shuffling")
    args = parser.parse_args()

    if args.iterations < 1:
        parser.error("--iterations must be >= 1")
    if args.jobs < 1:
        parser.error("--jobs must be >= 1")
    if args.warmup_runs < 0:
        parser.error("--warmup-runs must be >= 0")

    batch_id = args.batch_id or datetime.now(timezone.utc).strftime("batch-%Y%m%dT%H%M%SZ")
    batch_dir = args.output_dir / batch_id
    batch_dir.mkdir(parents=True, exist_ok=False)

    rng = random.Random(args.seed)
    jobs = [
        _job_args(args, variant, -warmup_iteration, batch_dir)
        for warmup_iteration in range(1, args.warmup_runs + 1)
        for variant in args.variants
    ]
    for iteration in range(1, args.iterations + 1):
        variant_order = list(args.variants)
        if args.shuffle_variants:
            rng.shuffle(variant_order)
        jobs.extend(_job_args(args, variant, iteration, batch_dir) for variant in variant_order)
    results: list[dict[str, Any]] = []
    sys.stdout.reconfigure(line_buffering=True)
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = []
        for job in jobs:
            print(json.dumps({
                "variant": job.variant,
                "iteration": job.run_id,
                "status": "starting",
                "counted": job.counted,
            }, sort_keys=True), flush=True)
            futures.append(pool.submit(_run_one, job))
        all_results: list[dict[str, Any]] = []
        for future in as_completed(futures):
            result = future.result()
            grade = result.get("grade") or {}
            all_results.append(result)
            if result.get("counted", True):
                results.append(result)
            print(json.dumps({
                "variant": result["variant"],
                "iteration": result["iteration"],
                "status": result["status"],
                "counted": result.get("counted", True),
                "total_score": grade.get("total_score"),
                "accuracy_score": grade.get("accuracy_score"),
                "speed_score": grade.get("speed_score"),
                "tokens_used": grade.get("tokens_used"),
                "duration_ms": grade.get("duration_ms"),
                "run_dir": result.get("run_dir"),
                "error": result.get("error"),
            }, sort_keys=True), flush=True)

    _annotate_cache_metrics(all_results)
    results.sort(key=lambda row: (row["variant"], row["iteration"]))
    summary = summarize(results)
    ranking = _build_ranking(summary)
    if ranking:
        summary["ranking"] = ranking
    (batch_dir / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (batch_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"batch_dir": str(batch_dir), "summary": summary}, indent=2, sort_keys=True), flush=True)
    if ranking:
        print()
        print(_format_ranking_table(ranking), flush=True)
    return 0 if all(row["status"] == "pass" for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
