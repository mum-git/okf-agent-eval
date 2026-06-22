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
from field_analysis import (
    build_ablation_bundle,
    build_ablation_effects,
    collect_frontmatter_field_usage,
    collect_index_depth_coverage,
    collect_index_field_usage,
    slugify_field,
)


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
    "concept-matched-yaml": {
        "bundle": ROOT / "bundles/concept-matched-yaml-retail-ops",
        "mode": "extension",
    },
    "concept-drift-yaml": {
        "bundle": ROOT / "bundles/concept-drift-yaml-retail-ops",
        "mode": "extension",
    },
    "frontloaded-yaml": {
        "bundle": ROOT / "bundles/frontloaded-yaml-retail-ops",
        "mode": "extension",
    },
    "body-routed-indexes": {
        "bundle": ROOT / "bundles/body-routed-indexes-retail-ops",
        "mode": "extension",
    },
    "sparse-index": {
        "bundle": ROOT / "bundles/sparse-index-retail-ops",
        "mode": "extension",
    },
    "concept-frontmatter-canary": {
        "bundle": ROOT / "bundles/concept-frontmatter-canary-retail-ops",
        "mode": "extension",
    },
    "concept-frontmatter-expanded": {
        "bundle": ROOT / "bundles/concept-frontmatter-expanded-retail-ops",
        "mode": "extension",
    },
    "concept-frontmatter-quoted": {
        "bundle": ROOT / "bundles/concept-frontmatter-quoted-retail-ops",
        "mode": "extension",
    },
    "concept-frontmatter-sparse": {
        "bundle": ROOT / "bundles/concept-frontmatter-sparse-retail-ops",
        "mode": "extension",
    },
    "concept-clean-body": {
        "bundle": ROOT / "bundles/concept-clean-body-retail-ops",
        "mode": "extension",
    },
    "concept-clean-yaml-okf": {
        "bundle": ROOT / "bundles/concept-clean-yaml-okf-retail-ops",
        "mode": "extension",
    },
    "concept-clean-yaml-sparse": {
        "bundle": ROOT / "bundles/concept-clean-yaml-sparse-retail-ops",
        "mode": "extension",
    },
    "concept-real-control": {
        "bundle": ROOT / "bundles/concept-real-control-retail-ops",
        "mode": "extension",
    },
    "concept-real-yaml-sparse": {
        "bundle": ROOT / "bundles/concept-real-yaml-sparse-retail-ops",
        "mode": "extension",
    },
    "concept-real-yaml-minimal": {
        "bundle": ROOT / "bundles/concept-real-yaml-minimal-retail-ops",
        "mode": "extension",
    },
    "concept-real-yaml-typed": {
        "bundle": ROOT / "bundles/concept-real-yaml-typed-retail-ops",
        "mode": "extension",
    },
    "concept-real-yaml-relational": {
        "bundle": ROOT / "bundles/concept-real-yaml-relational-retail-ops",
        "mode": "extension",
    },
    "concept-real-yaml-provenance": {
        "bundle": ROOT / "bundles/concept-real-yaml-provenance-retail-ops",
        "mode": "extension",
    },
    "concept-real-yaml-frontloaded": {
        "bundle": ROOT / "bundles/concept-real-yaml-frontloaded-retail-ops",
        "mode": "extension",
    },
    "concept-real-yaml-provenance-lite": {
        "bundle": ROOT / "bundles/concept-real-yaml-provenance-lite-retail-ops",
        "mode": "extension",
    },
    "concept-real-yaml-relational-lite": {
        "bundle": ROOT / "bundles/concept-real-yaml-relational-lite-retail-ops",
        "mode": "extension",
    },
    "concept-real-yaml-minimal-linked": {
        "bundle": ROOT / "bundles/concept-real-yaml-minimal-linked-retail-ops",
        "mode": "extension",
    },
    "concept-real-yaml-okf": {
        "bundle": ROOT / "bundles/concept-real-yaml-okf-retail-ops",
        "mode": "extension",
    },
}


def _job_args(
    args: argparse.Namespace,
    variant: str,
    iteration: int,
    batch_dir: Path,
    *,
    bundle: Path | None = None,
    base_variant: str | None = None,
    ablation_field: str | None = None,
) -> SimpleNamespace:
    spec = VARIANTS[variant]
    counted = iteration > 0
    run_label = f"iter-{iteration:03d}" if counted else f"warmup-{abs(iteration):03d}"
    output_root = batch_dir / variant
    if not counted:
        output_root = batch_dir / "_warmup" / variant
    return SimpleNamespace(
        bundle=bundle or spec["bundle"],
        task=args.task,
        grade_task=getattr(args, "grade_task", None),
        variant=variant,
        base_variant=base_variant or variant,
        ablation_field=ablation_field,
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
            "base_variant": job.base_variant,
            "ablation_field": job.ablation_field,
            "bundle": str(job.bundle),
            "task": str(job.task),
            "grade_task": str(job.grade_task) if job.grade_task else None,
            "iteration": job.run_id,
            "status": "pass",
            "counted": job.counted,
            "run_dir": result["run_dir"],
            "grade": result["grade"],
        }
    except (RunnerError, json.JSONDecodeError, FileExistsError) as exc:
        return {
            "variant": job.variant,
            "base_variant": job.base_variant,
            "ablation_field": job.ablation_field,
            "bundle": str(job.bundle),
            "task": str(job.task),
            "grade_task": str(job.grade_task) if job.grade_task else None,
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
    if len(values) < 5:
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

    # Collect per-task accuracy for cross-task stability metrics
    per_task_accuracy: dict[tuple[str, str], list[float]] = {}
    for result in results:
        if result.get("status") != "pass":
            continue
        task_key = str(result.get("task") or "")
        variant = str(result.get("variant") or "")
        acc = (result.get("grade") or {}).get("accuracy_score")
        if isinstance(acc, (int, float)):
            per_task_accuracy.setdefault((variant, task_key), []).append(float(acc))
    unique_tasks = sorted({str(r.get("task") or "") for r in results if r.get("task")})

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
        if len(unique_tasks) > 1:
            task_medians = [
                statistics.median(per_task_accuracy[(variant, t)])
                for t in unique_tasks
                if (variant, t) in per_task_accuracy and per_task_accuracy[(variant, t)]
            ]
            summary[variant]["min_accuracy_across_tasks"] = round(min(task_medians), 4) if task_medians else None
            summary[variant]["accuracy_std_across_tasks"] = (
                round(statistics.stdev(task_medians), 4) if len(task_medians) > 1 else None
            )
    return summary


def _build_field_usage_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    baseline_variants = {
        str(row["variant"])
        for row in results
        if row.get("status") == "pass" and row.get("counted") and not row.get("ablation_field")
    }
    return collect_index_field_usage(results, baseline_variants=baseline_variants)


def _build_frontmatter_usage_report(results: list[dict[str, Any]], *, scope: str) -> dict[str, Any]:
    baseline_variants = {
        str(row["variant"])
        for row in results
        if row.get("status") == "pass" and row.get("counted") and not row.get("ablation_field")
    }
    return collect_frontmatter_field_usage(results, baseline_variants=baseline_variants, scope=scope)


def _build_index_depth_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    baseline_variants = {
        str(row["variant"])
        for row in results
        if row.get("status") == "pass" and row.get("counted") and not row.get("ablation_field")
    }
    return collect_index_depth_coverage(results, baseline_variants=baseline_variants)


def _prepare_ablation_jobs(
    args: argparse.Namespace,
    batch_dir: Path,
    selected_variants: list[str],
    ablate_fields: list[str],
) -> tuple[list[SimpleNamespace], dict[str, dict[str, str]]]:
    jobs: list[SimpleNamespace] = []
    specs: dict[str, dict[str, str]] = {}
    seen_bundles: dict[tuple[str, str], Path] = {}

    for variant in selected_variants:
        source_bundle = VARIANTS[variant]["bundle"]
        for field in ablate_fields:
            slug = slugify_field(field)
            ablated_variant = f"{variant}__no-{slug}"
            ablated_bundle = seen_bundles.get((variant, field))
            if ablated_bundle is None:
                ablated_bundle = batch_dir / "_ablations" / variant / f"no-{slug}" / source_bundle.name
                build_ablation_bundle(source_bundle, ablated_bundle, {field}, scope=args.ablate_scope)
                seen_bundles[(variant, field)] = ablated_bundle
            specs[ablated_variant] = {
                "base_variant": variant,
                "field": field,
                "scope": args.ablate_scope,
            }
            jobs.extend(
                _job_args(
                    args,
                    ablated_variant,
                    iteration,
                    batch_dir,
                    bundle=ablated_bundle,
                    base_variant=variant,
                    ablation_field=field,
                )
                for iteration in range(1, args.iterations + 1)
            )
            jobs.extend(
                _job_args(
                    args,
                    ablated_variant,
                    -warmup_iteration,
                    batch_dir,
                    bundle=ablated_bundle,
                    base_variant=variant,
                    ablation_field=field,
                )
                for warmup_iteration in range(1, args.warmup_runs + 1)
            )
    return jobs, specs


def _build_ranking(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for variant, variant_summary in summary.items():
        if not isinstance(variant_summary, dict):
            continue
        avg_accuracy = variant_summary.get("avg_accuracy_score")
        median_accuracy = variant_summary.get("median_accuracy_score")
        avg_speed = variant_summary.get("avg_speed_score")
        median_speed = variant_summary.get("median_speed_score")
        avg_tokens = variant_summary.get("avg_tokens_used")
        median_tokens = variant_summary.get("median_tokens_used")
        avg_duration = variant_summary.get("avg_duration_ms")
        median_duration = variant_summary.get("median_duration_ms")
        if not all(
            isinstance(value, (int, float))
            for value in (avg_accuracy, median_accuracy, avg_speed, median_speed, avg_tokens, median_tokens, avg_duration, median_duration)
        ):
            continue
        tokens_per_correct = variant_summary.get("tokens_per_correct_answer")
        median_cold_duration = variant_summary.get("median_cold_duration_ms")
        rows.append({
            "variant": variant,
            "avg_accuracy_score": round(float(avg_accuracy), 4),
            "median_accuracy_score": round(float(median_accuracy), 4),
            "avg_speed_score": round(float(avg_speed), 4),
            "median_speed_score": round(float(median_speed), 4),
            "avg_tokens_used": round(float(avg_tokens), 4),
            "median_tokens_used": round(float(median_tokens), 4),
            "avg_duration_ms": round(float(avg_duration), 4),
            "median_duration_ms": round(float(median_duration), 4),
            "tokens_per_correct_answer": round(float(tokens_per_correct), 4) if isinstance(tokens_per_correct, (int, float)) else None,
            "median_cold_duration_ms": round(float(median_cold_duration), 4) if isinstance(median_cold_duration, (int, float)) else None,
        })

    rows.sort(
        key=lambda row: (
            -(row["median_accuracy_score"] or 0.0),
            row["median_duration_ms"] or float("inf"),
            row["median_tokens_used"] or float("inf"),
            row.get("tokens_per_correct_answer") or float("inf"),
            row["avg_duration_ms"] or float("inf"),
            row["avg_tokens_used"] or float("inf"),
            row["variant"],
        )
    )
    for index, row in enumerate(rows, start=1):
        row["rank"] = index

    # Assign cold_rank based on median cold-start duration
    cold_sortable = [
        (row.get("median_cold_duration_ms") or float("inf"), row["variant"])
        for row in rows
    ]
    cold_order = sorted(range(len(rows)), key=lambda i: cold_sortable[i])
    for cold_rank, original_idx in enumerate(cold_order, start=1):
        rows[original_idx]["cold_rank"] = cold_rank

    return rows


def _format_ranking_table(ranking: list[dict[str, Any]]) -> str:
    lines = [
        "| Rank | Variant | Med Acc | Avg Acc | Med Dur ms | Avg Dur ms | Med Tokens | Avg Tokens | Med Speed | Avg Speed |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in ranking:
        lines.append(
            "| {rank} | {variant} | {median_accuracy:.4f} | {accuracy:.4f} | {median_duration:.2f} | {duration:.2f} | {median_tokens:.2f} | {tokens:.2f} | {median_speed:.4f} | {speed:.4f} |".format(
                rank=row["rank"],
                variant=row["variant"],
                median_accuracy=row["median_accuracy_score"],
                accuracy=row["avg_accuracy_score"],
                median_duration=row["median_duration_ms"],
                duration=row["avg_duration_ms"],
                median_tokens=row["median_tokens_used"],
                speed=row["avg_speed_score"],
                tokens=row["avg_tokens_used"],
                median_speed=row["median_speed_score"],
            )
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", default=ROOT / "tasks/enterprise-fnf-synthesis.json", type=Path)
    parser.add_argument("--grade-task", type=Path, help="Private grading task spec; defaults to --task")
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
    parser.add_argument(
        "--frontmatter-scope",
        choices=["index", "concept", "all"],
        default="index",
        help="Which Markdown frontmatter reads to summarize in field-usage reports",
    )
    parser.add_argument(
        "--ablate-scope",
        choices=["index", "concept", "all"],
        default="index",
        help="Which Markdown files lose ablated frontmatter fields",
    )
    parser.add_argument(
        "--ablate-field",
        action="append",
        default=[],
        dest="ablate_fields",
        help="Remove one index frontmatter field and run an ablated comparison batch",
    )
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
    ablation_specs: dict[str, dict[str, str]] = {}
    if args.ablate_fields:
        ablation_jobs, ablation_specs = _prepare_ablation_jobs(args, batch_dir, list(args.variants), list(dict.fromkeys(args.ablate_fields)))
        jobs.extend(ablation_jobs)
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
    field_usage = _build_field_usage_report(results)
    if field_usage.get("fields"):
        summary["field_usage"] = field_usage
    include_concept_usage = args.frontmatter_scope in {"concept", "all"} or args.task.name == "concept-frontmatter-canary.json"
    if include_concept_usage:
        concept_field_usage = _build_frontmatter_usage_report(results, scope="concept")
        if concept_field_usage.get("fields"):
            summary["concept_field_usage"] = concept_field_usage
    if args.frontmatter_scope == "all":
        frontmatter_field_usage = _build_frontmatter_usage_report(results, scope="all")
        if frontmatter_field_usage.get("fields"):
            summary["frontmatter_field_usage"] = frontmatter_field_usage
    index_depth = _build_index_depth_report(results)
    if index_depth.get("runs"):
        summary["index_depth"] = index_depth
    if ablation_specs:
        summary["field_ablation"] = build_ablation_effects(summary, ablation_specs)
    (batch_dir / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (batch_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"batch_dir": str(batch_dir), "summary": summary}, indent=2, sort_keys=True), flush=True)
    if ranking:
        print()
        print(_format_ranking_table(ranking), flush=True)
    if summary.get("field_usage", {}).get("fields"):
        print()
        print("| Field | Reads | Runs | Avg Accuracy | Avg Speed | Avg Tokens |", flush=True)
        print("| --- | ---: | ---: | ---: | ---: | ---: |", flush=True)
        for row in summary["field_usage"]["fields"]:
            print(
                "| {field} | {reads} | {runs} | {accuracy:.4f} | {speed:.4f} | {tokens:.2f} |".format(
                    field=row["field"],
                    reads=row["read_count"],
                    runs=row["run_count"],
                    accuracy=row["avg_accuracy_score_when_seen"] or 0.0,
                    speed=row["avg_speed_score_when_seen"] or 0.0,
                    tokens=row["avg_tokens_used_when_seen"] or 0.0,
                ),
                flush=True,
            )
    if summary.get("concept_field_usage", {}).get("fields"):
        print()
        print("| Concept Field | Reads | Runs | Avg Accuracy | Avg Speed | Avg Tokens |", flush=True)
        print("| --- | ---: | ---: | ---: | ---: | ---: |", flush=True)
        for row in summary["concept_field_usage"]["fields"]:
            print(
                "| {field} | {reads} | {runs} | {accuracy:.4f} | {speed:.4f} | {tokens:.2f} |".format(
                    field=row["field"],
                    reads=row["read_count"],
                    runs=row["run_count"],
                    accuracy=row["avg_accuracy_score_when_seen"] or 0.0,
                    speed=row["avg_speed_score_when_seen"] or 0.0,
                    tokens=row["avg_tokens_used_when_seen"] or 0.0,
                ),
                flush=True,
            )
    if summary.get("frontmatter_field_usage", {}).get("fields"):
        print()
        print("| Frontmatter Field | Reads | Runs | Avg Accuracy | Avg Speed | Avg Tokens |", flush=True)
        print("| --- | ---: | ---: | ---: | ---: | ---: |", flush=True)
        for row in summary["frontmatter_field_usage"]["fields"]:
            print(
                "| {field} | {reads} | {runs} | {accuracy:.4f} | {speed:.4f} | {tokens:.2f} |".format(
                    field=row["field"],
                    reads=row["read_count"],
                    runs=row["run_count"],
                    accuracy=row["avg_accuracy_score_when_seen"] or 0.0,
                    speed=row["avg_speed_score_when_seen"] or 0.0,
                    tokens=row["avg_tokens_used_when_seen"] or 0.0,
                ),
                flush=True,
            )
    if summary.get("index_depth", {}).get("runs"):
        print()
        print("| Variant | Index Reads | Concept Reads | Max Index Depth | Ancestor Chain Complete | Misses |", flush=True)
        print("| --- | ---: | ---: | ---: | ---: | ---: |", flush=True)
        for row in summary["index_depth"]["runs"]:
            print(
                "| {variant} | {index_reads} | {concept_reads} | {max_depth} | {complete} | {misses} |".format(
                    variant=row["variant"],
                    index_reads=row["index_read_count"],
                    concept_reads=row["concept_read_count"],
                    max_depth=row["max_index_depth_read"] if row["max_index_depth_read"] is not None else 0,
                    complete="yes" if row["ancestor_chain_complete"] else "no",
                    misses=row["ancestor_chain_miss_count"],
                ),
                flush=True,
            )
    if summary.get("field_ablation"):
        print()
        print("| Field | Base Variant | Ablated Variant | Med Acc Drop | Med Speed Drop | Med Token Inc | Impact |", flush=True)
        print("| --- | --- | --- | ---: | ---: | ---: | ---: |", flush=True)
        for row in summary["field_ablation"]:
            print(
                "| {field} | {base} | {ablated} | {accuracy:.4f} | {speed:.4f} | {tokens:.4f} | {impact:.4f} |".format(
                    field=row["field"],
                    base=row["base_variant"],
                    ablated=row["ablated_variant"],
                    accuracy=row.get("median_accuracy_drop") or 0.0,
                    speed=row.get("median_speed_drop") or 0.0,
                    tokens=row.get("median_token_increase_ratio") or 0.0,
                    impact=row["impact_score"] or 0.0,
                ),
                flush=True,
            )
    return 0 if all(row["status"] == "pass" for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
