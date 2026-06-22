import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_runner import _build_prompt, run_agent  # noqa: E402


def test_runner_public_task_prompt_does_not_expose_private_answers():
    public_task = ROOT / "tasks" / "concept-frontmatter-canary.public.json"
    private_task = ROOT / "tasks" / "concept-frontmatter-canary.json"
    public_spec = json.loads(public_task.read_text(encoding="utf-8"))
    private_spec = json.loads(private_task.read_text(encoding="utf-8"))

    prompt = _build_prompt(
        ROOT / "bundles" / "concept-real-yaml-sparse-retail-ops",
        public_task,
        "concept-real-yaml-sparse",
        public_spec,
    )

    assert "Task path:" in prompt
    assert "must not be used as a source of answer facts" in prompt
    for key in public_spec["fact_keys"]:
        assert f'"{key}"' in prompt
    for spec in private_spec["expected_facts"].values():
        for accepted in spec["accepted"]:
            assert accepted not in prompt


def test_runner_executes_agent_command_and_grades(tmp_path):
    fake_agent = tmp_path / "fake_agent.py"
    fake_agent.write_text(
        """
import json
import sys

sys.stdin.read()
print(json.dumps({
    "task_id": "retail-margin-anomaly-v1",
    "bundle_variant": "strict",
    "answer": "Net margin dropped because pricing shadow ledger duplicated promotional adjustments.",
    "facts": {
        "root_cause": "pricing shadow ledger duplicated promotional adjustments",
        "affected_metric": "net margin",
        "bad_join_key": "sku instead of order_line_id",
        "rollout_id": "ff-2026-06-pricing-shadow-ledger",
        "remediation": "roll back the feature flag and rebuild margin_daily from order_line_id"
    },
    "citations": [
        "/incidents/2026-06-margin-anomaly/root-cause.md",
        "/commerce/metrics/net-margin.md",
        "/platform/features/pricing-shadow-ledger.md",
        "/commerce/datasets/order-line-ledger.md",
        "/incidents/2026-06-margin-anomaly/remediation.md"
    ]
}))
print(json.dumps({
    "bundle_variant": "strict",
    "events": [
        {"type": "read", "path": "/incidents/2026-06-margin-anomaly/root-cause.md"},
        {"type": "read", "path": "/commerce/metrics/net-margin.md"},
        {"type": "read", "path": "/platform/features/pricing-shadow-ledger.md"},
        {"type": "read", "path": "/commerce/datasets/order-line-ledger.md"},
        {"type": "read", "path": "/incidents/2026-06-margin-anomaly/remediation.md"}
    ]
}))
""".strip(),
        encoding="utf-8",
    )
    args = argparse.Namespace(
        bundle=ROOT / "bundles" / "strict-retail-ops",
        task=ROOT / "tasks" / "synthesis.json",
        variant="strict",
        mode="strict",
        agent_cmd=f"{sys.executable} {fake_agent}",
        output_dir=tmp_path / "runs",
        run_id="fake-run",
        timeout_s=30,
        cwd=None,
        tool_log=None,
        allow_nonzero=False,
    )

    result = run_agent(args)
    run_dir = Path(result["run_dir"])
    trace = json.loads((run_dir / "trace.json").read_text())
    grade = json.loads((run_dir / "grade.json").read_text())

    assert trace["duration_ms"] >= 0
    assert trace["runner_recorded_duration"] is True
    assert grade["accuracy_score"] == 1.0
    assert grade["citation_score"] == 1.0
    assert grade["missing_required_files"] == []


def test_runner_canonicalizes_enterprise_fact_schema_and_prompt(tmp_path):
    prompt_path = tmp_path / "prompt.txt"
    fake_agent = tmp_path / "fake_enterprise_agent.py"
    fake_agent.write_text(
        f"""
import json
import sys
from pathlib import Path

prompt = sys.stdin.read()
Path({json.dumps(str(prompt_path))}).write_text(prompt, encoding="utf-8")

print(json.dumps({{
    "task_id": "enterprise-fnf-escrow-recon-v1",
    "bundle_variant": "strict",
    "answer": "Florida purchase closings for FNF National Title were overstated because settlement_disbursement_recon_v3 joined party_identity_bridge using normalized_tax_id and inflated finance.disbursement_recon_daily.",
    "facts": {{
        "root_cause": "settlement_disbursement_recon_v3 joined party_identity_bridge using normalized_tax_id",
        "affected_metric": "escrow disbursement reconciliation variance",
        "bad_join_key": "normalized_tax_id instead of closing_party_role_id",
        "rollout_id": "settlement_disbursement_recon_v3",
        "remediation": "switch the transform to closing_party_role_id, quarantine normalized_tax_id joins, and backfill florida purchase closings"
    }},
    "citations": [
        "/enterprise-fnf/data-platform/warehouses/enterprise-dw/schemas/finance/views/disbursement-recon-daily.md",
        "/enterprise-fnf/data-platform/warehouses/enterprise-dw/schemas/settlement/tables/escrow-disbursement-fact.md",
        "/enterprise-fnf/data-platform/warehouses/enterprise-dw/schemas/party/tables/party-identity-bridge.md",
        "/enterprise-fnf/data-platform/pipelines/settlement/disbursement-recon/v3-transform.md",
        "/enterprise-fnf/business/title/regions/florida/underwriters/fnf-national-title/purchase-closings.md",
        "/enterprise-fnf/incidents/2026-09-florida-escrow-recon/root-cause.md",
        "/enterprise-fnf/incidents/2026-09-florida-escrow-recon/remediation.md"
    ]
}}))
print(json.dumps({{
    "bundle_variant": "strict",
    "events": [
        {{"type": "read", "path": "/enterprise-fnf/data-platform/warehouses/enterprise-dw/schemas/finance/views/disbursement-recon-daily.md"}},
        {{"type": "read", "path": "/enterprise-fnf/data-platform/warehouses/enterprise-dw/schemas/settlement/tables/escrow-disbursement-fact.md"}},
        {{"type": "read", "path": "/enterprise-fnf/data-platform/warehouses/enterprise-dw/schemas/party/tables/party-identity-bridge.md"}},
        {{"type": "read", "path": "/enterprise-fnf/data-platform/pipelines/settlement/disbursement-recon/v3-transform.md"}},
        {{"type": "read", "path": "/enterprise-fnf/business/title/regions/florida/underwriters/fnf-national-title/purchase-closings.md"}},
        {{"type": "read", "path": "/enterprise-fnf/incidents/2026-09-florida-escrow-recon/root-cause.md"}},
        {{"type": "read", "path": "/enterprise-fnf/incidents/2026-09-florida-escrow-recon/remediation.md"}}
    ]
}}))
""".strip(),
        encoding="utf-8",
    )
    args = argparse.Namespace(
        bundle=ROOT / "bundles" / "strict-retail-ops",
        task=ROOT / "tasks" / "enterprise-fnf-synthesis.json",
        variant="strict",
        mode="strict",
        agent_cmd=f"{sys.executable} {fake_agent}",
        output_dir=tmp_path / "runs",
        run_id="enterprise-run",
        timeout_s=30,
        cwd=None,
        tool_log=None,
        allow_nonzero=False,
    )

    result = run_agent(args)
    run_dir = Path(result["run_dir"])
    prompt = prompt_path.read_text(encoding="utf-8")
    submission = json.loads((run_dir / "submission.json").read_text())
    grade = json.loads((run_dir / "grade.json").read_text())

    assert '"affected_kpi"' in prompt
    assert '"affected_metric"' not in prompt
    assert '"pipeline"' in prompt
    assert '"rollout_id"' not in prompt
    assert set(submission["facts"]) == {
        "affected_kpi",
        "affected_segment",
        "root_cause",
        "bad_join_key",
        "correct_join_key",
        "impacted_asset",
        "pipeline",
        "remediation",
    }
    assert grade["accuracy_score"] == 1.0


def test_runner_extracts_token_count_from_stderr(tmp_path):
    fake_agent = tmp_path / "fake_agent_with_tokens.py"
    fake_agent.write_text(
        """
import json
import sys

sys.stdin.read()
print("tokens used", file=sys.stderr)
print("12,512", file=sys.stderr)
print(json.dumps({
    "task_id": "retail-margin-anomaly-v1",
    "bundle_variant": "strict",
    "answer": "Net margin dropped because pricing shadow ledger duplicated promotional adjustments.",
    "facts": {
        "root_cause": "pricing shadow ledger duplicated promotional adjustments",
        "affected_metric": "net margin",
        "bad_join_key": "sku instead of order_line_id",
        "rollout_id": "ff-2026-06-pricing-shadow-ledger",
        "remediation": "roll back the feature flag and rebuild margin_daily from order_line_id"
    },
    "citations": [
        "/incidents/2026-06-margin-anomaly/root-cause.md",
        "/commerce/metrics/net-margin.md",
        "/platform/features/pricing-shadow-ledger.md",
        "/commerce/datasets/order-line-ledger.md",
        "/incidents/2026-06-margin-anomaly/remediation.md"
    ]
}))
print(json.dumps({
    "bundle_variant": "strict",
    "events": [
        {"type": "read", "path": "/incidents/2026-06-margin-anomaly/root-cause.md"},
        {"type": "read", "path": "/commerce/metrics/net-margin.md"},
        {"type": "read", "path": "/platform/features/pricing-shadow-ledger.md"},
        {"type": "read", "path": "/commerce/datasets/order-line-ledger.md"},
        {"type": "read", "path": "/incidents/2026-06-margin-anomaly/remediation.md"}
    ]
}))
""".strip(),
        encoding="utf-8",
    )
    args = argparse.Namespace(
        bundle=ROOT / "bundles" / "strict-retail-ops",
        task=ROOT / "tasks" / "synthesis.json",
        variant="strict",
        mode="strict",
        agent_cmd=f"{sys.executable} {fake_agent}",
        output_dir=tmp_path / "runs",
        run_id="token-run",
        timeout_s=30,
        cwd=None,
        tool_log=None,
        allow_nonzero=False,
    )

    result = run_agent(args)
    run_dir = Path(result["run_dir"])
    grade = json.loads((run_dir / "grade.json").read_text())
    runner = json.loads((run_dir / "runner.json").read_text())

    assert grade["tokens_used"] == 12512
    assert runner["tokens_used"] == 12512


def test_runner_prefers_runtime_tool_log_over_self_reported_trace(tmp_path):
    fake_agent = tmp_path / "fake_agent_with_tool_log.py"
    fake_agent.write_text(
        """
import json
import os
import sys

sys.stdin.read()
events = [
    {"type": "read_file", "path": "/incidents/2026-06-margin-anomaly/root-cause.md"},
    {"tool": "read_file", "arguments": {"path": "/commerce/metrics/net-margin.md"}},
    {"name": "read_file", "args": {"path": "/platform/features/pricing-shadow-ledger.md"}},
    {"action": "open", "file_path": "/commerce/datasets/order-line-ledger.md"},
    {"event": "inspect", "target": "/incidents/2026-06-margin-anomaly/remediation.md"}
]
with open(os.environ["OKF_TRACE_LOG"], "w", encoding="utf-8") as f:
    for event in events:
        f.write(json.dumps(event) + "\\n")

print(json.dumps({
    "task_id": "retail-margin-anomaly-v1",
    "bundle_variant": "strict",
    "answer": "Net margin dropped because pricing shadow ledger duplicated promotional adjustments.",
    "facts": {
        "root_cause": "pricing shadow ledger duplicated promotional adjustments",
        "affected_metric": "net margin",
        "bad_join_key": "sku instead of order_line_id",
        "rollout_id": "ff-2026-06-pricing-shadow-ledger",
        "remediation": "roll back the feature flag and rebuild margin_daily from order_line_id"
    },
    "citations": [
        "/incidents/2026-06-margin-anomaly/root-cause.md",
        "/commerce/metrics/net-margin.md",
        "/platform/features/pricing-shadow-ledger.md",
        "/commerce/datasets/order-line-ledger.md",
        "/incidents/2026-06-margin-anomaly/remediation.md"
    ]
}))
print(json.dumps({
    "bundle_variant": "strict",
    "events": [{"type": "read", "path": "/commerce/metrics/gross-margin.md"}]
}))
""".strip(),
        encoding="utf-8",
    )
    args = argparse.Namespace(
        bundle=ROOT / "bundles" / "strict-retail-ops",
        task=ROOT / "tasks" / "synthesis.json",
        variant="strict",
        mode="strict",
        agent_cmd=f"{sys.executable} {fake_agent}",
        output_dir=tmp_path / "runs",
        run_id="runtime-log-run",
        timeout_s=30,
        cwd=None,
        tool_log=None,
        allow_nonzero=False,
    )

    result = run_agent(args)
    run_dir = Path(result["run_dir"])
    trace = json.loads((run_dir / "trace.json").read_text())
    grade = json.loads((run_dir / "grade.json").read_text())

    assert trace["trace_source"] == "runtime-log"
    assert len(trace["events"]) == 5
    assert all(event["path"] != "/commerce/metrics/gross-margin.md" for event in trace["events"])
    assert grade["missing_required_files"] == []
    assert grade["distractor_files_read"] == []


def test_runner_ingests_okf_trace_stdout_markers(tmp_path):
    fake_agent = tmp_path / "fake_agent_with_stdout_markers.py"
    fake_agent.write_text(
        """
import json
import sys

sys.stdin.read()
for path in [
    "/incidents/2026-06-margin-anomaly/root-cause.md",
    "/commerce/metrics/net-margin.md",
    "/platform/features/pricing-shadow-ledger.md",
    "/commerce/datasets/order-line-ledger.md",
    "/incidents/2026-06-margin-anomaly/remediation.md"
]:
    print("OKF_TRACE: " + json.dumps({"type": "read", "path": path}))

print(json.dumps({
    "task_id": "retail-margin-anomaly-v1",
    "bundle_variant": "strict",
    "answer": "Net margin dropped because pricing shadow ledger duplicated promotional adjustments.",
    "facts": {
        "root_cause": "pricing shadow ledger duplicated promotional adjustments",
        "affected_metric": "net margin",
        "bad_join_key": "sku instead of order_line_id",
        "rollout_id": "ff-2026-06-pricing-shadow-ledger",
        "remediation": "roll back the feature flag and rebuild margin_daily from order_line_id"
    },
    "citations": [
        "/incidents/2026-06-margin-anomaly/root-cause.md",
        "/commerce/metrics/net-margin.md",
        "/platform/features/pricing-shadow-ledger.md",
        "/commerce/datasets/order-line-ledger.md",
        "/incidents/2026-06-margin-anomaly/remediation.md"
    ]
}))
""".strip(),
        encoding="utf-8",
    )
    args = argparse.Namespace(
        bundle=ROOT / "bundles" / "strict-retail-ops",
        task=ROOT / "tasks" / "synthesis.json",
        variant="strict",
        mode="strict",
        agent_cmd=f"{sys.executable} {fake_agent}",
        output_dir=tmp_path / "runs",
        run_id="stdout-marker-run",
        timeout_s=30,
        cwd=None,
        tool_log=None,
        allow_nonzero=False,
    )

    result = run_agent(args)
    run_dir = Path(result["run_dir"])
    trace = json.loads((run_dir / "trace.json").read_text())
    grade = json.loads((run_dir / "grade.json").read_text())

    assert trace["trace_source"] == "runtime-log"
    assert len(trace["events"]) == 5
    assert grade["missing_required_files"] == []
