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
    assert strict["p95_tokens_used"] == 12000.0
    assert strict["correct_answer_count"] == 1
    assert strict["tokens_per_correct_answer"] == 10000.0
    assert strict["median_duration_ms"] == 75.0
    assert strict["p95_duration_ms"] == 100.0
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


def test_batch_runner_ranking_uses_accuracy_speed_and_tokens():
    summary = {
        "accuracy-first": {
            "avg_accuracy_score": 1.0,
            "avg_speed_score": 0.85,
            "avg_tokens_used": 12000.0,
        },
        "speed-first": {
            "avg_accuracy_score": 0.9,
            "avg_speed_score": 0.95,
            "avg_tokens_used": 20000.0,
        },
        "token-first": {
            "avg_accuracy_score": 0.95,
            "avg_speed_score": 0.8,
            "avg_tokens_used": 10000.0,
        },
    }

    from batch_runner import _build_ranking

    ranking = _build_ranking(summary)

    assert [row["variant"] for row in ranking] == [
        "token-first",
        "accuracy-first",
        "speed-first",
    ]
    assert ranking[0]["rank"] == 1
    assert ranking[0]["composite_score"] > ranking[1]["composite_score"] > ranking[2]["composite_score"]
