#!/usr/bin/env python3
"""Compare OKF-only vs postgres-accelerated batch runs side by side.

Usage:
    python3 scripts/compare_postgres_runs.py \
        --baseline runs/<level>-<harness>-okf/summary.json \
        --postgres runs/<level>-<harness>-pg/summary.json \
        [--label "codex L2"]

Or compare a whole matrix by passing repeated --pair baseline:postgres:label.
Reads batch_runner summary.json files (one variant each) and prints a table of
accuracy, speed, files read, and token efficiency with deltas.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

# (key in summary, label, lower_is_better)
METRICS = [
    ("median_accuracy_score", "accuracy", False),
    ("median_citation_score", "citation", False),
    ("median_duration_ms", "speed (ms)", True),
    ("median_unique_files_read", "files read", True),
    ("median_tokens_used", "tokens", True),
    ("tokens_per_correct_answer", "tokens/correct", True),
    ("median_trace_score", "trace score", False),
]


def _first_variant(summary: dict) -> dict:
    """summary.json maps variant -> metrics; return the single variant's metrics."""
    if not summary:
        return {}
    return next(iter(summary.values()))


def _fmt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:,.2f}" if abs(v) < 1000 else f"{v:,.0f}"
    return f"{v:,}"


def _delta(base, pg, lower_is_better: bool) -> str:
    if base is None or pg is None or base == 0:
        return "—"
    pct = (pg - base) / base * 100.0
    # Improvement sign depends on metric direction.
    improved = (pct < 0) if lower_is_better else (pct > 0)
    arrow = "✓" if improved else "✗" if abs(pct) > 0.5 else "="
    return f"{pct:+.0f}% {arrow}"


def compare_pair(baseline_path: Path, postgres_path: Path, label: str) -> None:
    base = _first_variant(json.loads(baseline_path.read_text()))
    pg = _first_variant(json.loads(postgres_path.read_text()))

    print(f"\n=== {label} ===")
    print(f"{'metric':<18}{'OKF':>14}{'postgres':>14}{'delta':>14}")
    print("-" * 60)
    for key, name, lower in METRICS:
        b, p = base.get(key), pg.get(key)
        print(f"{name:<18}{_fmt(b):>14}{_fmt(p):>14}{_delta(b, p, lower):>14}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--postgres", type=Path)
    parser.add_argument("--label", default="comparison")
    parser.add_argument("--pair", action="append", default=[],
                        help="baseline.json:postgres.json:label (repeatable)")
    args = parser.parse_args()

    pairs: list[tuple[Path, Path, str]] = []
    if args.baseline and args.postgres:
        pairs.append((args.baseline, args.postgres, args.label))
    for spec in args.pair:
        b, p, *rest = spec.split(":")
        pairs.append((Path(b), Path(p), rest[0] if rest else "comparison"))

    if not pairs:
        parser.error("provide --baseline/--postgres or at least one --pair")

    print("Legend: delta is postgres vs OKF.  ✓ = postgres better, ✗ = worse.")
    for baseline, postgres, label in pairs:
        compare_pair(baseline, postgres, label)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
