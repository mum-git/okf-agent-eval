import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from batch_runner import _job_args, _run_one, summarize  # noqa: E402


def test_batch_runner_job_and_summary(tmp_path):
    fake_agent = tmp_path / "fake_agent.py"
    fake_agent.write_text(
        """
import json
import sys

prompt = sys.stdin.read()
variant = "strict"
if "Bundle variant: extended" in prompt:
    variant = "extended"
elif "Bundle variant: uniform-yaml" in prompt:
    variant = "uniform-yaml"
elif "Bundle variant: concept-matched-yaml" in prompt:
    variant = "concept-matched-yaml"
elif "Bundle variant: concept-drift-yaml" in prompt:
    variant = "concept-drift-yaml"
elif "Bundle variant: frontloaded-yaml" in prompt:
    variant = "frontloaded-yaml"
elif "Bundle variant: body-routed-indexes" in prompt:
    variant = "body-routed-indexes"
elif "Bundle variant: sparse-index" in prompt:
    variant = "sparse-index"

print(json.dumps({
    "task_id": "enterprise-fnf-escrow-recon-v1",
    "bundle_variant": variant,
    "answer": "Escrow disbursement reconciliation variance was overstated for Florida purchase closings for FNF National Title.",
    "facts": {
        "affected_kpi": "escrow disbursement reconciliation variance",
        "affected_segment": "Florida purchase closings for FNF National Title",
        "root_cause": "disbursement recon transform joined party_identity_bridge by normalized_tax_id",
        "bad_join_key": "normalized_tax_id instead of closing_party_role_id",
        "correct_join_key": "closing_party_role_id",
        "impacted_asset": "finance.disbursement_recon_daily",
        "pipeline": "settlement_disbursement_recon_v3",
        "remediation": "switch the transform to closing_party_role_id, quarantine normalized_tax_id joins, and backfill florida purchase closings"
    },
    "citations": [
        "/enterprise-fnf/data-platform/warehouses/enterprise-dw/schemas/finance/views/disbursement-recon-daily.md",
        "/enterprise-fnf/data-platform/warehouses/enterprise-dw/schemas/settlement/tables/escrow-disbursement-fact.md",
        "/enterprise-fnf/data-platform/warehouses/enterprise-dw/schemas/party/tables/party-identity-bridge.md",
        "/enterprise-fnf/data-platform/pipelines/settlement/disbursement-recon/v3-transform.md",
        "/enterprise-fnf/business/title/regions/florida/underwriters/fnf-national-title/purchase-closings.md",
        "/enterprise-fnf/incidents/2026-09-florida-escrow-recon/root-cause.md",
        "/enterprise-fnf/incidents/2026-09-florida-escrow-recon/remediation.md"
    ]
}))
print(json.dumps({
    "bundle_variant": variant,
    "events": [
        {"type": "read", "path": "/enterprise-fnf/data-platform/warehouses/enterprise-dw/schemas/finance/views/disbursement-recon-daily.md"},
        {"type": "read", "path": "/enterprise-fnf/data-platform/warehouses/enterprise-dw/schemas/settlement/tables/escrow-disbursement-fact.md"},
        {"type": "read", "path": "/enterprise-fnf/data-platform/warehouses/enterprise-dw/schemas/party/tables/party-identity-bridge.md"},
        {"type": "read", "path": "/enterprise-fnf/data-platform/pipelines/settlement/disbursement-recon/v3-transform.md"},
        {"type": "read", "path": "/enterprise-fnf/business/title/regions/florida/underwriters/fnf-national-title/purchase-closings.md"},
        {"type": "read", "path": "/enterprise-fnf/incidents/2026-09-florida-escrow-recon/root-cause.md"},
        {"type": "read", "path": "/enterprise-fnf/incidents/2026-09-florida-escrow-recon/remediation.md"}
    ]
}))
""".strip(),
        encoding="utf-8",
    )
    args = argparse.Namespace(
        task=ROOT / "tasks" / "enterprise-fnf-synthesis.json",
        agent_cmd=f"{sys.executable} {fake_agent}",
        timeout_s=30,
        cwd=None,
        allow_nonzero=False,
    )
    batch_dir = tmp_path / "batch"

    jobs = [
        _job_args(args, "strict", 1, batch_dir),
        _job_args(args, "extended", 1, batch_dir),
    ]
    results = [_run_one(job) for job in jobs]
    summary = summarize(results)

    assert all(result["status"] == "pass" for result in results)
    assert summary["strict"]["avg_total_score"] == 1.0
    assert summary["extended"]["avg_accuracy_score"] == 1.0
    assert (batch_dir / "strict" / "iter-001" / "grade.json").exists()
    assert (batch_dir / "extended" / "iter-001" / "grade.json").exists()


def test_batch_runner_job_preserves_private_grade_task(tmp_path):
    args = argparse.Namespace(
        task=ROOT / "tasks" / "concept-frontmatter-canary.public.json",
        grade_task=ROOT / "tasks" / "concept-frontmatter-canary.json",
        agent_cmd="fake-agent",
        timeout_s=30,
        cwd=None,
        allow_nonzero=False,
    )

    job = _job_args(args, "concept-real-yaml-sparse", 1, tmp_path / "batch")

    assert job.task == ROOT / "tasks" / "concept-frontmatter-canary.public.json"
    assert job.grade_task == ROOT / "tasks" / "concept-frontmatter-canary.json"


def test_batch_runner_summary_includes_medians_and_speed():
    results = [
        {
            "variant": "strict",
            "status": "pass",
            "grade": {
                "total_score": 0.8,
                "accuracy_score": 0.9,
                "citation_score": 1.0,
                "trace_score": 0.7,
                "speed_score": 0.5,
                "tokens_used": 12000,
                "duration_ms": 100.0,
                "unique_files_read": 8,
                "distractor_files_read": [],
            },
        },
        {
            "variant": "strict",
            "status": "pass",
            "grade": {
                "total_score": 1.0,
                "accuracy_score": 1.0,
                "citation_score": 1.0,
                "trace_score": 1.0,
                "speed_score": 1.0,
                "tokens_used": 10000,
                "duration_ms": 50.0,
                "unique_files_read": 7,
                "distractor_files_read": [],
            },
        },
    ]

    summary = summarize(results)
    strict = summary["strict"]

    assert strict["avg_total_score"] == 0.9
    assert strict["median_total_score"] == 0.9
    assert strict["avg_speed_score"] == 0.75
    assert strict["median_speed_score"] == 0.75
    assert strict["avg_tokens_used"] == 11000.0
    assert strict["median_tokens_used"] == 11000.0
    assert strict["p95_tokens_used"] is None  # n=2 is below the minimum of 5 for P95
    assert strict["correct_answer_count"] == 1
    assert strict["tokens_per_correct_answer"] == 10000.0
    assert strict["median_duration_ms"] == 75.0
    assert strict["p95_duration_ms"] is None  # n=2 is below the minimum of 5 for P95
    assert strict["first_duration_ms"] == 100.0
    assert strict["steady_state_avg_duration_ms"] == 50.0


def test_batch_runner_cache_metrics_split_cold_and_warm_runs(tmp_path):
    batch_dir = tmp_path / "batch"
    warmup_dir = batch_dir / "_warmup" / "strict" / "warmup-001"
    cold_dir = batch_dir / "strict" / "iter-001"
    warm_dir = batch_dir / "strict" / "iter-002"
    warmup_dir.mkdir(parents=True)
    cold_dir.mkdir(parents=True)
    warm_dir.mkdir(parents=True)

    (warmup_dir / "trace.json").write_text(json.dumps({
        "duration_ms": 12.0,
        "events": [
            {"type": "read", "path": "/alpha.md"},
        ],
    }), encoding="utf-8")
    (cold_dir / "trace.json").write_text(json.dumps({
        "duration_ms": 20.0,
        "events": [
            {"type": "read", "path": "/beta.md"},
        ],
    }), encoding="utf-8")
    (warm_dir / "trace.json").write_text(json.dumps({
        "duration_ms": 8.0,
        "events": [
            {"type": "read", "path": "/alpha.md"},
            {"type": "read", "path": "/beta.md"},
        ],
    }), encoding="utf-8")

    results = [
        {
            "variant": "strict",
            "iteration": "iter-001",
            "status": "pass",
            "counted": True,
            "run_dir": str(cold_dir),
            "grade": {
                "total_score": 1.0,
                "accuracy_score": 1.0,
                "citation_score": 1.0,
                "trace_score": 1.0,
                "speed_score": 1.0,
                "tokens_used": 10000,
                "duration_ms": 20.0,
                "unique_files_read": 1,
                "distractor_files_read": [],
            },
        },
        {
            "variant": "strict",
            "iteration": "iter-002",
            "status": "pass",
            "counted": True,
            "run_dir": str(warm_dir),
            "grade": {
                "total_score": 0.8,
                "accuracy_score": 0.9,
                "citation_score": 1.0,
                "trace_score": 0.7,
                "speed_score": 0.5,
                "tokens_used": 12000,
                "duration_ms": 8.0,
                "unique_files_read": 2,
                "distractor_files_read": [],
            },
        },
        {
            "variant": "strict",
            "iteration": "warmup-001",
            "status": "pass",
            "counted": False,
            "run_dir": str(warmup_dir),
            "grade": {
                "total_score": 1.0,
                "accuracy_score": 1.0,
                "citation_score": 1.0,
                "trace_score": 1.0,
                "speed_score": 1.0,
                "tokens_used": 9000,
                "duration_ms": 12.0,
                "unique_files_read": 1,
                "distractor_files_read": [],
            },
        },
    ]

    from batch_runner import _annotate_cache_metrics

    _annotate_cache_metrics(results)
    summary = summarize([row for row in results if row["counted"]])
    strict = summary["strict"]

    assert results[0]["grade"]["cache_state"] == "cold"
    assert results[0]["grade"]["cache_hit_reads"] == 0
    assert results[1]["grade"]["cache_state"] == "warm"
    assert results[1]["grade"]["cache_hit_reads"] == 2
    assert results[2]["grade"]["cache_state"] == "cold"
    assert results[2]["grade"]["cache_hit_reads"] == 0
    assert strict["cold_run_count"] == 1
    assert strict["warm_run_count"] == 1
    assert strict["avg_cache_hit_rate"] == 0.5
    assert strict["median_cache_hit_rate"] == 0.5
    assert strict["avg_cold_duration_ms"] == 20.0
    assert strict["avg_warm_duration_ms"] == 8.0


def test_batch_runner_ranking_uses_raw_medians_for_ordering():
    summary = {
        "fastest": {
            "avg_accuracy_score": 1.0,
            "median_accuracy_score": 1.0,
            "avg_speed_score": 0.85,
            "median_speed_score": 0.9,
            "avg_tokens_used": 12000.0,
            "median_tokens_used": 12000.0,
            "avg_duration_ms": 70.0,
            "median_duration_ms": 50.0,
        },
        "leanest": {
            "avg_accuracy_score": 1.0,
            "median_accuracy_score": 1.0,
            "avg_speed_score": 0.95,
            "median_speed_score": 0.95,
            "avg_tokens_used": 10000.0,
            "median_tokens_used": 10000.0,
            "avg_duration_ms": 80.0,
            "median_duration_ms": 60.0,
        },
        "slowest": {
            "avg_accuracy_score": 1.0,
            "median_accuracy_score": 1.0,
            "avg_speed_score": 0.8,
            "median_speed_score": 0.8,
            "avg_tokens_used": 9000.0,
            "median_tokens_used": 9000.0,
            "avg_duration_ms": 90.0,
            "median_duration_ms": 90.0,
        },
    }

    from batch_runner import _build_ranking

    ranking = _build_ranking(summary)

    assert [row["variant"] for row in ranking] == ["fastest", "leanest", "slowest"]
    assert ranking[0]["rank"] == 1
    assert ranking[0]["median_duration_ms"] < ranking[1]["median_duration_ms"] < ranking[2]["median_duration_ms"]
    assert ranking[1]["median_tokens_used"] == 10000.0


def test_ablation_bundle_removes_selected_index_field(tmp_path):
    from field_analysis import build_ablation_bundle

    source = ROOT / "bundles" / "uniform-yaml-retail-ops"
    target = tmp_path / "ablated"

    build_ablation_bundle(source, target, {"routing_hint"})

    text = (target / "enterprise-fnf" / "incidents" / "index.md").read_text(encoding="utf-8")
    assert "routing_hint:" not in text
    assert "task_hint:" in text
    assert text.startswith("---\n")


def test_ablation_bundle_can_scope_to_concept_fields(tmp_path):
    from field_analysis import build_ablation_bundle

    source = tmp_path / "source"
    target = tmp_path / "target"
    (source / "dir").mkdir(parents=True)
    (source / "index.md").write_text(
        """---
routing_hint: keep index
---
# Root
""",
        encoding="utf-8",
    )
    (source / "dir" / "concept.md").write_text(
        """---
type: concept
routing_hint: remove concept
---
# Concept
""",
        encoding="utf-8",
    )

    build_ablation_bundle(source, target, {"routing_hint"}, scope="concept")

    assert "routing_hint: keep index" in (target / "index.md").read_text(encoding="utf-8")
    assert "routing_hint:" not in (target / "dir" / "concept.md").read_text(encoding="utf-8")


def test_field_usage_and_ablation_effect_reports(tmp_path):
    from field_analysis import build_ablation_effects, collect_frontmatter_field_usage, collect_index_field_usage

    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "index.md").write_text(
        """---
type: directory_index
title: Root
description: Root index
task_hint: alpha routing
routing_hint: inspect alpha
---
# Root

- [Alpha](alpha/index.md)
""".strip() + "\n",
        encoding="utf-8",
    )
    (bundle / "alpha").mkdir()
    (bundle / "alpha" / "concept.md").write_text(
        """---
type: canary
concept_hint: concept metadata
---
# Concept
""".strip() + "\n",
        encoding="utf-8",
    )
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "trace.json").write_text(json.dumps({
        "events": [
            {"type": "read", "path": "/index.md"},
            {"type": "read", "path": "/alpha/concept.md"},
        ]
    }), encoding="utf-8")

    results = [
        {
            "variant": "strict",
            "status": "pass",
            "counted": True,
            "run_dir": str(run_dir),
            "bundle": str(bundle),
            "grade": {
                "accuracy_score": 1.0,
                "speed_score": 0.8,
                "tokens_used": 1000,
                "duration_ms": 10.0,
            },
        }
    ]
    usage = collect_index_field_usage(results, baseline_variants={"strict"})
    fields = {row["field"]: row for row in usage["fields"]}
    assert usage["baseline_run_count"] == 1
    assert usage["frontmatter_scope"] == "index"
    assert fields["task_hint"]["read_count"] == 1
    assert fields["routing_hint"]["run_count"] == 1
    assert "concept_hint" not in fields

    concept_usage = collect_frontmatter_field_usage(results, baseline_variants={"strict"}, scope="concept")
    concept_fields = {row["field"]: row for row in concept_usage["fields"]}
    assert concept_usage["frontmatter_scope"] == "concept"
    assert concept_fields["concept_hint"]["read_count"] == 1
    assert "task_hint" not in concept_fields

    all_usage = collect_frontmatter_field_usage(results, baseline_variants={"strict"}, scope="all")
    all_fields = {row["field"]: row for row in all_usage["fields"]}
    assert all_usage["frontmatter_scope"] == "all"
    assert all_fields["task_hint"]["read_count"] == 1
    assert all_fields["concept_hint"]["read_count"] == 1

    summary = {
        "strict": {
            "avg_accuracy_score": 1.0,
            "median_accuracy_score": 1.0,
            "avg_speed_score": 0.8,
            "median_speed_score": 0.8,
            "avg_tokens_used": 1000.0,
            "median_tokens_used": 1000.0,
        },
        "strict__no-task-hint": {
            "avg_accuracy_score": 0.75,
            "median_accuracy_score": 0.75,
            "avg_speed_score": 0.7,
            "median_speed_score": 0.7,
            "avg_tokens_used": 1250.0,
            "median_tokens_used": 1250.0,
        },
    }
    impacts = build_ablation_effects(summary, {"strict__no-task-hint": {"base_variant": "strict", "field": "task_hint"}})
    assert impacts[0]["field"] == "task_hint"
    assert impacts[0]["avg_accuracy_drop"] == 0.25
    assert impacts[0]["avg_token_increase_ratio"] == 0.25


def test_index_depth_report_tracks_ancestor_chain_coverage(tmp_path):
    from field_analysis import collect_index_depth_coverage

    bundle = tmp_path / "bundle"
    (bundle / "dir").mkdir(parents=True)
    (bundle / "index.md").write_text("# Root\n", encoding="utf-8")
    (bundle / "dir" / "index.md").write_text("# Dir\n", encoding="utf-8")
    (bundle / "dir" / "leaf.md").write_text("# Leaf\n", encoding="utf-8")

    complete_run = tmp_path / "complete"
    incomplete_run = tmp_path / "incomplete"
    complete_run.mkdir()
    incomplete_run.mkdir()
    (complete_run / "trace.json").write_text(json.dumps({
        "events": [
            {"type": "read", "path": "/index.md"},
            {"type": "read", "path": "/dir/index.md"},
            {"type": "read", "path": "/dir/leaf.md"},
        ]
    }), encoding="utf-8")
    (incomplete_run / "trace.json").write_text(json.dumps({
        "events": [
            {"type": "read", "path": "/index.md"},
            {"type": "read", "path": "/dir/leaf.md"},
            {"type": "read", "path": "/dir/index.md"},
        ]
    }), encoding="utf-8")

    results = [
        {
            "variant": "strict",
            "status": "pass",
            "counted": True,
            "run_dir": str(complete_run),
            "bundle": str(bundle),
            "grade": {"accuracy_score": 1.0, "speed_score": 1.0, "tokens_used": 1000, "duration_ms": 10.0},
        },
        {
            "variant": "strict",
            "status": "pass",
            "counted": True,
            "run_dir": str(incomplete_run),
            "bundle": str(bundle),
            "grade": {"accuracy_score": 0.5, "speed_score": 0.5, "tokens_used": 1200, "duration_ms": 12.0},
        },
    ]

    report = collect_index_depth_coverage(results, baseline_variants={"strict"})

    assert report["baseline_run_count"] == 2
    assert report["avg_index_read_count"] == 2.0
    assert report["median_index_read_count"] == 2.0
    assert report["avg_concept_read_count"] == 1.0
    assert report["avg_max_index_depth_read"] == 1.0
    assert report["ancestor_chain_complete_run_count"] == 1
    assert report["ancestor_chain_complete_rate"] == 0.5
    assert report["depth_histogram"] == {0: 2, 1: 2}
    assert report["runs"][0]["ancestor_chain_complete"] is True
    assert report["runs"][1]["ancestor_chain_complete"] is False
    assert report["runs"][1]["ancestor_chain_miss_count"] == 1


def test_p95_returns_none_for_small_samples():
    from batch_runner import _p95
    assert _p95([]) is None
    assert _p95([1.0]) is None
    assert _p95([1.0, 2.0]) is None
    assert _p95([1.0, 2.0, 3.0, 4.0]) is None
    assert _p95([1.0, 2.0, 3.0, 4.0, 5.0]) is not None


def test_ablation_impact_score_formula():
    from field_analysis import build_ablation_effects

    summary = {
        "base": {
            "avg_accuracy_score": 1.0,
            "median_accuracy_score": 1.0,
            "avg_speed_score": 1.0,
            "median_speed_score": 1.0,
            "avg_tokens_used": 1000.0,
            "median_tokens_used": 1000.0,
        },
        "base__no-hint": {
            "avg_accuracy_score": 0.5,
            "median_accuracy_score": 0.5,
            "avg_speed_score": 0.7,
            "median_speed_score": 0.7,
            "avg_tokens_used": 1300.0,
            "median_tokens_used": 1300.0,
        },
    }
    impacts = build_ablation_effects(summary, {"base__no-hint": {"base_variant": "base", "field": "hint"}})
    row = impacts[0]

    # accuracy_drop=0.5, speed_drop=0.3, token_ratio=0.3
    # impact = 0.4*0.5 + 0.3*0.3 + 0.3*0.3 = 0.20 + 0.09 + 0.09 = 0.38
    assert row["avg_accuracy_drop"] == 0.5
    assert row["avg_speed_drop"] == 0.3
    assert row["avg_token_increase_ratio"] == 0.3
    assert row["avg_impact_score"] == 0.38
    assert row["median_impact_score"] == 0.38
    assert row["impact_score"] == 0.38


def test_ranking_tiebreakers_all_levels():
    from batch_runner import _build_ranking

    def _make_variant(median_acc, median_dur, median_tok, tokens_per_correct, avg_dur, avg_tok, name):
        return {
            "avg_accuracy_score": median_acc,
            "median_accuracy_score": median_acc,
            "avg_speed_score": 0.9,
            "median_speed_score": 0.9,
            "avg_tokens_used": avg_tok,
            "median_tokens_used": median_tok,
            "avg_duration_ms": avg_dur,
            "median_duration_ms": median_dur,
            "tokens_per_correct_answer": tokens_per_correct,
        }

    summary = {
        # Different accuracy → sorted by accuracy first
        "high-acc": _make_variant(1.0, 50.0, 10000.0, 10000.0, 50.0, 10000.0, "high-acc"),
        "low-acc": _make_variant(0.5, 10.0, 1000.0, 1000.0, 10.0, 1000.0, "low-acc"),
        # Same accuracy, different median_duration → sorted by median_duration
        "fast-dur": _make_variant(1.0, 30.0, 10000.0, 10000.0, 30.0, 10000.0, "fast-dur"),
        "slow-dur": _make_variant(1.0, 80.0, 10000.0, 10000.0, 80.0, 10000.0, "slow-dur"),
        # Same accuracy + median_duration, different median_tokens → sorted by median_tokens
        "lean-tok": _make_variant(1.0, 50.0, 5000.0, 5000.0, 50.0, 5000.0, "lean-tok"),
        "heavy-tok": _make_variant(1.0, 50.0, 20000.0, 20000.0, 50.0, 20000.0, "heavy-tok"),
        # Same acc/med_dur/med_tok, different tokens_per_correct → sorted by tokens_per_correct
        "eff-correct": _make_variant(1.0, 50.0, 10000.0, 8000.0, 50.0, 10000.0, "eff-correct"),
        "ineff-correct": _make_variant(1.0, 50.0, 10000.0, 15000.0, 50.0, 10000.0, "ineff-correct"),
    }
    ranking = _build_ranking(summary)
    variant_order = [row["variant"] for row in ranking]

    # high-acc and fast-dur both have accuracy 1.0 and should beat low-acc
    assert variant_order.index("high-acc") < variant_order.index("low-acc")
    assert variant_order.index("fast-dur") < variant_order.index("slow-dur")
    assert variant_order.index("lean-tok") < variant_order.index("heavy-tok")
    assert variant_order.index("eff-correct") < variant_order.index("ineff-correct")
    # low-acc ranks last
    assert variant_order[-1] == "low-acc"


def test_ranking_includes_cold_rank_and_tokens_per_correct():
    from batch_runner import _build_ranking

    summary = {
        "alpha": {
            "avg_accuracy_score": 1.0,
            "median_accuracy_score": 1.0,
            "avg_speed_score": 0.9,
            "median_speed_score": 0.9,
            "avg_tokens_used": 10000.0,
            "median_tokens_used": 10000.0,
            "avg_duration_ms": 50.0,
            "median_duration_ms": 50.0,
            "tokens_per_correct_answer": 10000.0,
            "median_cold_duration_ms": 80.0,
        },
        "beta": {
            "avg_accuracy_score": 1.0,
            "median_accuracy_score": 1.0,
            "avg_speed_score": 0.9,
            "median_speed_score": 0.9,
            "avg_tokens_used": 10000.0,
            "median_tokens_used": 10000.0,
            "avg_duration_ms": 50.0,
            "median_duration_ms": 50.0,
            "tokens_per_correct_answer": 10000.0,
            "median_cold_duration_ms": 40.0,
        },
    }
    ranking = _build_ranking(summary)
    by_name = {row["variant"]: row for row in ranking}

    assert "tokens_per_correct_answer" in by_name["alpha"]
    assert "cold_rank" in by_name["alpha"]
    # beta has lower cold duration so should have better (lower) cold_rank
    assert by_name["beta"]["cold_rank"] < by_name["alpha"]["cold_rank"]


def test_cross_task_stability_added_for_multi_task_batches():
    results = [
        {
            "variant": "v1",
            "status": "pass",
            "task": "/tasks/task-a.json",
            "grade": {
                "total_score": 1.0,
                "accuracy_score": 1.0,
                "citation_score": 1.0,
                "trace_score": 1.0,
                "speed_score": 1.0,
                "tokens_used": 10000,
                "duration_ms": 30.0,
                "unique_files_read": 5,
                "distractor_files_read": [],
            },
        },
        {
            "variant": "v1",
            "status": "pass",
            "task": "/tasks/task-b.json",
            "grade": {
                "total_score": 0.5,
                "accuracy_score": 0.0,
                "citation_score": 0.5,
                "trace_score": 0.5,
                "speed_score": 0.5,
                "tokens_used": 15000,
                "duration_ms": 90.0,
                "unique_files_read": 8,
                "distractor_files_read": [],
            },
        },
    ]
    summary = summarize(results)
    v1 = summary["v1"]
    assert "min_accuracy_across_tasks" in v1
    assert v1["min_accuracy_across_tasks"] == 0.0
    assert "accuracy_std_across_tasks" in v1
    assert v1["accuracy_std_across_tasks"] is not None


def test_cross_task_stability_absent_for_single_task_batches():
    results = [
        {
            "variant": "v1",
            "status": "pass",
            "task": "/tasks/task-a.json",
            "grade": {
                "total_score": 1.0,
                "accuracy_score": 1.0,
                "citation_score": 1.0,
                "trace_score": 1.0,
                "speed_score": 1.0,
                "tokens_used": 10000,
                "duration_ms": 30.0,
                "unique_files_read": 5,
                "distractor_files_read": [],
            },
        },
    ]
    summary = summarize(results)
    assert "min_accuracy_across_tasks" not in summary["v1"]
    assert "accuracy_std_across_tasks" not in summary["v1"]
