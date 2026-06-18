import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from grader import score_submission, validate_bundle  # noqa: E402


STRICT = ROOT / "bundles" / "strict-retail-ops"
EXTENDED = ROOT / "bundles" / "extended-retail-ops"
UNIFORM = ROOT / "bundles" / "uniform-yaml-retail-ops"
FRONTLOADED = ROOT / "bundles" / "frontloaded-yaml-retail-ops"
BODY_ROUTED = ROOT / "bundles" / "body-routed-indexes-retail-ops"
SPARSE = ROOT / "bundles" / "sparse-index-retail-ops"
TASK = ROOT / "tasks" / "synthesis.json"
DEEP_TASK = ROOT / "tasks" / "deep-synthesis.json"
ENTERPRISE_TASK = ROOT / "tasks" / "enterprise-fnf-synthesis.json"
CA_TASK = ROOT / "tasks" / "california-refi-fee-synthesis.json"


def test_strict_bundle_passes_strict_parseability():
    result = validate_bundle(STRICT, mode="strict")
    assert result["parseability"] == "pass"
    assert result["concept_count"] >= 22


def test_extended_bundle_fails_strict_but_passes_extension_mode():
    strict_result = validate_bundle(EXTENDED, mode="strict")
    extension_result = validate_bundle(EXTENDED, mode="extension")
    assert strict_result["parseability"] == "fail"
    assert any("reserved file" in err for err in strict_result["errors"])
    assert extension_result["parseability"] == "pass"


def test_uniform_yaml_bundle_fails_strict_but_passes_extension_mode():
    strict_result = validate_bundle(UNIFORM, mode="strict")
    extension_result = validate_bundle(UNIFORM, mode="extension")
    assert strict_result["parseability"] == "fail"
    assert extension_result["parseability"] == "pass"
    assert extension_result["concept_count"] >= 8


def test_frontloaded_bundle_fails_strict_but_passes_extension_mode():
    strict_result = validate_bundle(FRONTLOADED, mode="strict")
    extension_result = validate_bundle(FRONTLOADED, mode="extension")
    assert strict_result["parseability"] == "fail"
    assert extension_result["parseability"] == "pass"


def test_body_routed_bundle_has_no_yaml_on_indexes_and_passes_extension_mode():
    root_text = (BODY_ROUTED / "index.md").read_text(encoding="utf-8")
    child_text = (BODY_ROUTED / "incidents" / "index.md").read_text(encoding="utf-8")
    extension_result = validate_bundle(BODY_ROUTED, mode="extension")

    assert not root_text.startswith("---\n")
    assert "## Key entries:" in root_text
    assert not child_text.startswith("---\n")
    assert extension_result["parseability"] == "pass"


def test_sparse_bundle_keeps_minimal_index_frontmatter():
    root_text = (SPARSE / "index.md").read_text(encoding="utf-8")
    strict_result = validate_bundle(SPARSE, mode="strict")
    extension_result = validate_bundle(SPARSE, mode="extension")

    assert root_text.startswith("---\n")
    assert "type: directory_index" in root_text
    assert "title:" in root_text
    assert "description:" in root_text
    assert "owner:" not in root_text
    assert strict_result["parseability"] == "fail"
    assert extension_result["parseability"] == "pass"


def test_deep_correct_submission_gets_full_score():
    result = score_submission(
        STRICT,
        DEEP_TASK,
        ROOT / "answers" / "deep-example-correct.json",
        mode="strict",
        trace_path=ROOT / "traces" / "deep-example-efficient.json",
    )
    assert result["accuracy_score"] == 1.0
    assert result["citation_score"] == 1.0
    assert result["trace_score"] == 1.0
    assert result["total_score"] == 1.0
    assert result["required_files_read"] == 6


def test_deep_task_required_citations_exist_in_all_variants():
    task = json.loads(DEEP_TASK.read_text())
    for bundle in (STRICT, EXTENDED, UNIFORM):
        missing = [
            citation for citation in task["required_citations"]
            if not (bundle / citation.lstrip("/")).exists()
        ]
        assert missing == []


def test_enterprise_fnf_correct_submission_gets_full_score():
    result = score_submission(
        STRICT,
        ENTERPRISE_TASK,
        ROOT / "answers" / "enterprise-fnf-example-correct.json",
        mode="strict",
        trace_path=ROOT / "traces" / "enterprise-fnf-example-efficient.json",
    )
    assert result["accuracy_score"] == 1.0
    assert result["citation_score"] == 1.0
    assert result["trace_score"] == 1.0
    assert result["total_score"] == 1.0
    assert result["required_files_read"] == 7


def test_enterprise_fnf_required_citations_exist_in_all_variants():
    task = json.loads(ENTERPRISE_TASK.read_text())
    for bundle in (STRICT, EXTENDED, UNIFORM):
        missing = [
            citation for citation in task["required_citations"]
            if not (bundle / citation.lstrip("/")).exists()
        ]
        assert missing == []


def test_ca_refi_fee_correct_submission_gets_full_score():
    result = score_submission(
        STRICT,
        CA_TASK,
        ROOT / "answers" / "california-refi-fee-correct.json",
        mode="strict",
        trace_path=ROOT / "traces" / "california-refi-fee-efficient.json",
    )
    assert result["accuracy_score"] == 1.0
    assert result["citation_score"] == 1.0
    assert result["trace_score"] == 1.0
    assert result["total_score"] == 1.0
    assert result["required_files_read"] == 6


def test_ca_refi_fee_required_citations_exist_in_all_variants():
    task = json.loads(CA_TASK.read_text())
    for bundle in (STRICT, EXTENDED, UNIFORM):
        missing = [
            citation for citation in task["required_citations"]
            if not (bundle / citation.lstrip("/")).exists()
        ]
        assert missing == [], f"{bundle.name}: {missing}"


def test_fl_task_rejects_ca_answer():
    """CA answer must score badly on FL task — shared vocabulary should not help."""
    result = score_submission(
        STRICT,
        ENTERPRISE_TASK,
        ROOT / "answers" / "california-refi-fee-correct.json",
        mode="strict",
    )
    assert result["accuracy_score"] < 0.5


def test_ca_task_rejects_fl_answer():
    """FL answer must score badly on CA task — shared vocabulary should not help."""
    result = score_submission(
        STRICT,
        CA_TASK,
        ROOT / "answers" / "enterprise-fnf-example-correct.json",
        mode="strict",
    )
    assert result["accuracy_score"] < 0.5


def test_fl_task_impacted_asset_now_strict():
    """escrow_disbursement_fact is the source, not the impacted view — must not score."""
    import tempfile, os
    submission = json.loads((ROOT / "answers" / "enterprise-fnf-example-correct.json").read_text())
    submission["facts"]["impacted_asset"] = "settlement.escrow_disbursement_fact"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(submission, f)
        tmp = f.name
    try:
        result = score_submission(STRICT, ENTERPRISE_TASK, Path(tmp), mode="strict")
        assert result["accuracy_score"] < 1.0
        assert "impacted_asset" in result["incorrect"]
    finally:
        os.unlink(tmp)


def test_correct_submission_gets_full_score():
    result = score_submission(
        STRICT,
        TASK,
        ROOT / "answers" / "example-correct.json",
        mode="strict",
    )
    assert result["parseability"] == "pass"
    assert result["accuracy_score"] == 1.0
    assert result["citation_score"] == 1.0
    assert result["total_score"] == 1.0
    assert result["missing"] == []
    assert result["incorrect"] == []


def test_correct_submission_with_efficient_trace_gets_trace_score():
    result = score_submission(
        STRICT,
        TASK,
        ROOT / "answers" / "example-correct.json",
        mode="strict",
        trace_path=ROOT / "traces" / "example-efficient.json",
    )
    assert result["accuracy_score"] == 1.0
    assert result["citation_score"] == 1.0
    assert result["trace_score"] == 1.0
    assert result["total_score"] == 1.0
    assert result["missing_required_files"] == []
    assert result["distractor_files_read"] == []


def test_trace_reports_speed_separately():
    result = score_submission(
        STRICT,
        ENTERPRISE_TASK,
        ROOT / "answers" / "enterprise-fnf-example-correct.json",
        mode="strict",
        trace_path=ROOT / "traces" / "enterprise-fnf-example-efficient.json",
    )
    assert "speed_score" in result
    assert 0.0 <= result["speed_score"] <= 1.0
    assert result["trace_score"] == 1.0


def test_top_level_fact_submission_is_accepted(tmp_path):
    submission = {
        "task_id": "retail-margin-anomaly-v1",
        "bundle_variant": "strict",
        "answer": "Net margin dropped because pricing shadow ledger duplicated promotional adjustments.",
        "root_cause": "pricing shadow ledger duplicated promotional adjustments",
        "affected_metric": "net margin",
        "bad_join_key": "sku instead of order_line_id",
        "rollout_id": "ff-2026-06-pricing-shadow-ledger",
        "remediation": "roll back the feature flag and rebuild margin_daily from order_line_id",
        "citations": json.loads(TASK.read_text())["required_citations"],
    }
    path = tmp_path / "top-level-facts.json"
    path.write_text(json.dumps(submission), encoding="utf-8")

    result = score_submission(STRICT, TASK, path, mode="strict")
    assert result["accuracy_score"] == 1.0


def test_trace_event_alias_is_accepted(tmp_path):
    trace = {
        "duration_ms": 60000,
        "events": [
            {"event": "file_read", "path": "/incidents/2026-06-margin-anomaly/root-cause.md"},
            {"event": "file-read", "path": "/commerce/metrics/net-margin.md"},
            {"event": "read", "path": "/platform/features/pricing-shadow-ledger.md"},
            {"event": "read_file", "path": "/commerce/datasets/order-line-ledger.md"},
            {"event": "open", "path": "/incidents/2026-06-margin-anomaly/remediation.md"},
        ],
    }
    path = tmp_path / "event-alias-trace.json"
    path.write_text(json.dumps(trace), encoding="utf-8")

    result = score_submission(
        STRICT,
        TASK,
        ROOT / "answers" / "example-correct.json",
        mode="strict",
        trace_path=path,
    )
    assert result["required_files_read"] == 5
    assert result["missing_required_files"] == []


def test_absolute_bundle_paths_are_normalized_in_trace(tmp_path):
    bundle = STRICT.resolve()
    trace = {
        "duration_ms": 60000,
        "events": [
            {"type": "read", "path": str(bundle / "incidents/2026-06-margin-anomaly/root-cause.md")},
            {"type": "read", "path": str(bundle / "commerce/metrics/net-margin.md")},
            {"type": "read", "path": str(bundle / "platform/features/pricing-shadow-ledger.md")},
            {"type": "read", "path": str(bundle / "commerce/datasets/order-line-ledger.md")},
            {"type": "read", "path": str(bundle / "incidents/2026-06-margin-anomaly/remediation.md")},
            {"type": "read", "path": str(ROOT / "tasks/synthesis.json")},
        ],
    }
    path = tmp_path / "absolute-path-trace.json"
    path.write_text(json.dumps(trace), encoding="utf-8")

    result = score_submission(
        STRICT,
        TASK,
        ROOT / "answers" / "example-correct.json",
        mode="strict",
        trace_path=path,
    )
    assert result["required_files_read"] == 5
    assert result["unique_files_read"] == 5


def test_noisy_trace_loses_efficiency_and_completeness_points():
    result = score_submission(
        STRICT,
        TASK,
        ROOT / "answers" / "example-correct.json",
        mode="strict",
        trace_path=ROOT / "traces" / "example-noisy.json",
    )
    assert result["accuracy_score"] == 1.0
    assert result["trace_score"] < 1.0
    assert result["total_score"] < 1.0
    assert result["missing_required_files"]
    assert result["distractor_files_read"]


def test_missing_citations_loses_citation_points(tmp_path):
    submission = json.loads((ROOT / "answers" / "example-correct.json").read_text())
    submission["citations"] = submission["citations"][:2]
    path = tmp_path / "missing-citations.json"
    path.write_text(json.dumps(submission), encoding="utf-8")

    result = score_submission(STRICT, TASK, path, mode="strict")
    assert result["accuracy_score"] == 1.0
    assert result["citation_score"] < 1.0
    assert result["missing_citations"]


def test_distractor_submission_loses_accuracy_points():
    result = score_submission(
        STRICT,
        TASK,
        ROOT / "answers" / "example-distractor.json",
        mode="strict",
    )
    assert result["accuracy_score"] < 1.0
    assert result["distractor_hits"]
    assert "root_cause" in result["incorrect"]


def test_malformed_frontmatter_is_reported(tmp_path):
    bundle = tmp_path / "bundle"
    concept_dir = bundle / "bad"
    concept_dir.mkdir(parents=True)
    (bundle / "index.md").write_text("---\nokf_version: 0.1\n---\n# Root\n", encoding="utf-8")
    (concept_dir / "broken.md").write_text("---\ntype concept\n---\n# Broken\n", encoding="utf-8")

    result = validate_bundle(bundle, mode="strict")
    assert result["parseability"] == "fail"
    assert any("invalid frontmatter" in err for err in result["errors"])
