import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from grader import parse_frontmatter, score_submission, validate_bundle  # noqa: E402


STRICT = ROOT / "bundles" / "strict-retail-ops"
EXTENDED = ROOT / "bundles" / "extended-retail-ops"
UNIFORM = ROOT / "bundles" / "uniform-yaml-retail-ops"
CONCEPT_MATCHED = ROOT / "bundles" / "concept-matched-yaml-retail-ops"
CONCEPT_DRIFT = ROOT / "bundles" / "concept-drift-yaml-retail-ops"
FRONTLOADED = ROOT / "bundles" / "frontloaded-yaml-retail-ops"
BODY_ROUTED = ROOT / "bundles" / "body-routed-indexes-retail-ops"
SPARSE = ROOT / "bundles" / "sparse-index-retail-ops"
CONCEPT_FRONTMATTER_CANARY = ROOT / "bundles" / "concept-frontmatter-canary-retail-ops"
CONCEPT_FRONTMATTER_SPARSE = ROOT / "bundles" / "concept-frontmatter-sparse-retail-ops"
CONCEPT_FRONTMATTER_EXPANDED = ROOT / "bundles" / "concept-frontmatter-expanded-retail-ops"
CONCEPT_FRONTMATTER_QUOTED = ROOT / "bundles" / "concept-frontmatter-quoted-retail-ops"
CONCEPT_CLEAN_BODY = ROOT / "bundles" / "concept-clean-body-retail-ops"
CONCEPT_CLEAN_YAML_SPARSE = ROOT / "bundles" / "concept-clean-yaml-sparse-retail-ops"
CONCEPT_CLEAN_YAML_OKF = ROOT / "bundles" / "concept-clean-yaml-okf-retail-ops"
CONCEPT_REAL_CONTROL = ROOT / "bundles" / "concept-real-control-retail-ops"
CONCEPT_REAL_YAML_SPARSE = ROOT / "bundles" / "concept-real-yaml-sparse-retail-ops"
CONCEPT_REAL_YAML_MINIMAL = ROOT / "bundles" / "concept-real-yaml-minimal-retail-ops"
CONCEPT_REAL_YAML_TYPED = ROOT / "bundles" / "concept-real-yaml-typed-retail-ops"
CONCEPT_REAL_YAML_RELATIONAL = ROOT / "bundles" / "concept-real-yaml-relational-retail-ops"
CONCEPT_REAL_YAML_PROVENANCE = ROOT / "bundles" / "concept-real-yaml-provenance-retail-ops"
CONCEPT_REAL_YAML_FRONTLOADED = ROOT / "bundles" / "concept-real-yaml-frontloaded-retail-ops"
CONCEPT_REAL_YAML_PROVENANCE_LITE = ROOT / "bundles" / "concept-real-yaml-provenance-lite-retail-ops"
CONCEPT_REAL_YAML_RELATIONAL_LITE = ROOT / "bundles" / "concept-real-yaml-relational-lite-retail-ops"
CONCEPT_REAL_YAML_MINIMAL_LINKED = ROOT / "bundles" / "concept-real-yaml-minimal-linked-retail-ops"
CONCEPT_REAL_YAML_OKF = ROOT / "bundles" / "concept-real-yaml-okf-retail-ops"
TASK = ROOT / "tasks" / "synthesis.json"
DEEP_TASK = ROOT / "tasks" / "deep-synthesis.json"
ENTERPRISE_TASK = ROOT / "tasks" / "enterprise-fnf-synthesis.json"
CA_TASK = ROOT / "tasks" / "california-refi-fee-synthesis.json"
CONCEPT_FRONTMATTER_CANARY_TASK = ROOT / "tasks" / "concept-frontmatter-canary.json"

CONCEPT_FRONTMATTER_TARGET_PATHS = [
    Path("enterprise-fnf/frontmatter-canary/incidents/2026-11-md-frontmatter-canary/root-cause.md"),
    Path("enterprise-fnf/frontmatter-canary/incidents/2026-11-md-frontmatter-canary/remediation.md"),
    Path("enterprise-fnf/frontmatter-canary/registry/signal-registry.md"),
]
CONCEPT_REAL_APPLICABLE_VARIANTS = (
    CONCEPT_REAL_YAML_MINIMAL,
    CONCEPT_REAL_YAML_TYPED,
    CONCEPT_REAL_YAML_RELATIONAL,
    CONCEPT_REAL_YAML_PROVENANCE,
    CONCEPT_REAL_YAML_FRONTLOADED,
    CONCEPT_REAL_YAML_PROVENANCE_LITE,
    CONCEPT_REAL_YAML_RELATIONAL_LITE,
    CONCEPT_REAL_YAML_MINIMAL_LINKED,
)


def _expected_fact_acceptance_sets() -> dict[str, list[str]]:
    task = json.loads(CONCEPT_FRONTMATTER_CANARY_TASK.read_text(encoding="utf-8"))
    return {
        key: list(spec["accepted"])
        for key, spec in task["expected_facts"].items()
    }


def _all_expected_fact_values() -> set[str]:
    return {
        accepted
        for accepted_values in _expected_fact_acceptance_sets().values()
        for accepted in accepted_values
    }


def _metadata_text(data: dict | None) -> str:
    return json.dumps(data or {}, sort_keys=True)


def _frontmatter_keys_in_order(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    frontmatter = text.split("\n---\n", 1)[0].removeprefix("---\n")
    return [
        line.split(":", 1)[0].strip()
        for line in frontmatter.splitlines()
        if line and not line.startswith("  ") and ":" in line
    ]


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


def test_concept_matched_bundle_aligns_concept_metadata_with_indexes():
    index_fm, _ = parse_frontmatter(
        (UNIFORM / "enterprise-fnf" / "incidents" / "2026-09-florida-escrow-recon" / "index.md").read_text(encoding="utf-8")
    )
    concept_fm, _ = parse_frontmatter(
        (CONCEPT_MATCHED / "enterprise-fnf" / "incidents" / "2026-09-florida-escrow-recon" / "root-cause.md").read_text(encoding="utf-8")
    )

    assert validate_bundle(CONCEPT_MATCHED, mode="extension")["parseability"] == "pass"
    assert isinstance(index_fm, dict)
    assert isinstance(concept_fm, dict)
    for key in ("domain", "area", "depth", "metadata_profile", "owner", "task_hint", "routing_hint"):
        if key in index_fm:
            assert concept_fm[key] == index_fm[key]


def test_concept_drift_bundle_changes_three_inherited_metadata_fields():
    index_fm, _ = parse_frontmatter(
        (UNIFORM / "enterprise-fnf" / "incidents" / "2026-09-florida-escrow-recon" / "index.md").read_text(encoding="utf-8")
    )
    concept_fm, _ = parse_frontmatter(
        (CONCEPT_DRIFT / "enterprise-fnf" / "incidents" / "2026-09-florida-escrow-recon" / "root-cause.md").read_text(encoding="utf-8")
    )

    assert validate_bundle(CONCEPT_DRIFT, mode="extension")["parseability"] == "pass"
    assert isinstance(index_fm, dict)
    assert isinstance(concept_fm, dict)
    assert concept_fm["metadata_profile"] != index_fm["metadata_profile"]
    assert concept_fm["owner"] != index_fm["owner"]
    assert concept_fm["depth"] == index_fm["depth"] + 1


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


def test_concept_frontmatter_canary_bundle_passes_extension_mode():
    for bundle in (
        CONCEPT_FRONTMATTER_CANARY,
        CONCEPT_FRONTMATTER_SPARSE,
        CONCEPT_FRONTMATTER_EXPANDED,
        CONCEPT_FRONTMATTER_QUOTED,
        CONCEPT_CLEAN_YAML_SPARSE,
        CONCEPT_CLEAN_YAML_OKF,
        CONCEPT_REAL_CONTROL,
        CONCEPT_REAL_YAML_SPARSE,
        *CONCEPT_REAL_APPLICABLE_VARIANTS,
        CONCEPT_REAL_YAML_OKF,
    ):
        result = validate_bundle(bundle, mode="extension")

        assert result["parseability"] == "pass", bundle.name
        assert result["concept_count"] >= 8


def test_concept_frontmatter_canary_correct_submission_gets_full_score():
    for bundle in (
        CONCEPT_FRONTMATTER_CANARY,
        CONCEPT_FRONTMATTER_SPARSE,
        CONCEPT_FRONTMATTER_EXPANDED,
        CONCEPT_FRONTMATTER_QUOTED,
        CONCEPT_CLEAN_YAML_SPARSE,
        CONCEPT_CLEAN_YAML_OKF,
        CONCEPT_REAL_YAML_SPARSE,
        *CONCEPT_REAL_APPLICABLE_VARIANTS,
        CONCEPT_REAL_YAML_OKF,
    ):
        result = score_submission(
            bundle,
            CONCEPT_FRONTMATTER_CANARY_TASK,
            ROOT / "answers" / "concept-frontmatter-canary-correct.json",
            mode="extension",
            trace_path=ROOT / "traces" / "concept-frontmatter-canary-efficient.json",
        )

        assert result["accuracy_score"] == 1.0, bundle.name
        assert result["citation_score"] == 1.0, bundle.name
        assert result["trace_score"] == 1.0, bundle.name
        assert result["total_score"] == 1.0, bundle.name
        assert result["required_files_read"] == 3


def test_concept_frontmatter_control_does_not_credit_unsupported_fact_guesses():
    result = score_submission(
        CONCEPT_REAL_CONTROL,
        CONCEPT_FRONTMATTER_CANARY_TASK,
        ROOT / "answers" / "concept-frontmatter-canary-correct.json",
        mode="extension",
        trace_path=ROOT / "traces" / "concept-frontmatter-canary-efficient.json",
    )

    assert result["accuracy_score"] == 0.0
    assert sorted(result["unsupported"]) == sorted(_expected_fact_acceptance_sets())


def test_concept_frontmatter_canary_values_are_not_in_bodies_or_indexes():
    canary_values = _all_expected_fact_values()
    for bundle in (
        CONCEPT_FRONTMATTER_CANARY,
        CONCEPT_FRONTMATTER_SPARSE,
        CONCEPT_FRONTMATTER_EXPANDED,
        CONCEPT_FRONTMATTER_QUOTED,
        CONCEPT_CLEAN_YAML_SPARSE,
        CONCEPT_CLEAN_YAML_OKF,
        CONCEPT_REAL_YAML_SPARSE,
        *CONCEPT_REAL_APPLICABLE_VARIANTS,
        CONCEPT_REAL_YAML_OKF,
    ):
        canary_root = bundle / "enterprise-fnf" / "frontmatter-canary"
        for path in canary_root.rglob("*.md"):
            fm, body = parse_frontmatter(path.read_text(encoding="utf-8"))
            if path.name == "index.md":
                fm_text = _metadata_text(fm)
                for value in canary_values:
                    assert value not in fm_text, f"{bundle.name}: {path}"
            for value in canary_values:
                assert value not in body, f"{bundle.name}: {path}"


def test_clean_concept_variants_hold_indexes_and_non_targets_constant():
    variants = (
        CONCEPT_CLEAN_BODY,
        CONCEPT_CLEAN_YAML_SPARSE,
        CONCEPT_CLEAN_YAML_OKF,
    )
    target_paths = {
        Path("enterprise-fnf/frontmatter-canary/incidents/2026-11-md-frontmatter-canary/root-cause.md"),
        Path("enterprise-fnf/frontmatter-canary/incidents/2026-11-md-frontmatter-canary/remediation.md"),
        Path("enterprise-fnf/frontmatter-canary/registry/signal-registry.md"),
    }

    base = CONCEPT_CLEAN_BODY
    for bundle in variants:
        for index_path in sorted(bundle.rglob("index.md")):
            rel = index_path.relative_to(bundle)
            text = index_path.read_text(encoding="utf-8")
            assert not text.startswith("---\n"), f"{bundle.name}: {rel}"
            assert text == (base / rel).read_text(encoding="utf-8"), f"{bundle.name}: {rel}"

        for path in sorted(bundle.rglob("*.md")):
            rel = path.relative_to(bundle)
            if path.name == "index.md" or rel in target_paths:
                continue
            assert path.read_text(encoding="utf-8") == (base / rel).read_text(encoding="utf-8"), f"{bundle.name}: {rel}"


def test_clean_concept_variants_place_answer_values_only_in_intended_location():
    acceptance_sets = _expected_fact_acceptance_sets()
    variants = {
        CONCEPT_CLEAN_BODY: "body",
        CONCEPT_CLEAN_YAML_SPARSE: "frontmatter",
        CONCEPT_CLEAN_YAML_OKF: "frontmatter",
    }

    for bundle, expected_location in variants.items():
        combined_frontmatter = []
        combined_body = []
        for rel in CONCEPT_FRONTMATTER_TARGET_PATHS:
            fm, body = parse_frontmatter((bundle / rel).read_text(encoding="utf-8"))
            combined_frontmatter.append(_metadata_text(fm))
            combined_body.append(body)
        frontmatter_text = "\n".join(combined_frontmatter)
        body_text = "\n".join(combined_body)

        for key, accepted_values in acceptance_sets.items():
            if expected_location == "body":
                assert any(value in body_text for value in accepted_values), f"{bundle.name}: {key}"
                for value in accepted_values:
                    assert value not in frontmatter_text, f"{bundle.name}: {value}"
            else:
                assert any(value in frontmatter_text for value in accepted_values), f"{bundle.name}: {key}"
                for value in accepted_values:
                    assert value not in body_text, f"{bundle.name}: {value}"


def test_real_concept_variants_hold_indexes_and_bodies_constant():
    variants = (
        CONCEPT_REAL_CONTROL,
        CONCEPT_REAL_YAML_SPARSE,
        *CONCEPT_REAL_APPLICABLE_VARIANTS,
        CONCEPT_REAL_YAML_OKF,
    )
    base = CONCEPT_REAL_CONTROL

    for bundle in variants:
        for index_path in sorted(bundle.rglob("index.md")):
            rel = index_path.relative_to(bundle)
            text = index_path.read_text(encoding="utf-8")
            assert not text.startswith("---\n"), f"{bundle.name}: {rel}"
            assert text == (base / rel).read_text(encoding="utf-8"), f"{bundle.name}: {rel}"

        for path in sorted(bundle.rglob("*.md")):
            if path.name == "index.md":
                continue
            rel = path.relative_to(bundle)
            _, body = parse_frontmatter(path.read_text(encoding="utf-8"))
            _, base_body = parse_frontmatter((base / rel).read_text(encoding="utf-8"))
            assert body == base_body, f"{bundle.name}: {rel}"


def test_real_concept_variants_place_answer_values_only_in_frontmatter():
    acceptance_sets = _expected_fact_acceptance_sets()

    for bundle in (CONCEPT_REAL_YAML_SPARSE, *CONCEPT_REAL_APPLICABLE_VARIANTS, CONCEPT_REAL_YAML_OKF):
        combined_frontmatter = []
        combined_body = []
        for rel in CONCEPT_FRONTMATTER_TARGET_PATHS:
            fm, body = parse_frontmatter((bundle / rel).read_text(encoding="utf-8"))
            combined_frontmatter.append(_metadata_text(fm))
            combined_body.append(body)
        frontmatter_text = "\n".join(combined_frontmatter)
        body_text = "\n".join(combined_body)

        for key, accepted_values in acceptance_sets.items():
            assert any(value in frontmatter_text for value in accepted_values), f"{bundle.name}: {key}"
            for value in accepted_values:
                assert value not in body_text, f"{bundle.name}: {value}"

    control_text = []
    for rel in CONCEPT_FRONTMATTER_TARGET_PATHS:
        fm, body = parse_frontmatter((CONCEPT_REAL_CONTROL / rel).read_text(encoding="utf-8"))
        control_text.append(_metadata_text(fm))
        control_text.append(body)
    combined_control_text = "\n".join(control_text)
    for value in _all_expected_fact_values():
        assert value not in combined_control_text, value


def test_real_applicable_variants_use_only_practical_metadata():
    expected_fields = {
        CONCEPT_REAL_YAML_MINIMAL: {"id", "type", "title"},
        CONCEPT_REAL_YAML_TYPED: {"domain", "system", "record_status", "owner"},
        CONCEPT_REAL_YAML_RELATIONAL: {"related_assets", "related_signals", "related_files"},
        CONCEPT_REAL_YAML_PROVENANCE: {"last_verified", "verification_method", "source_system", "lineage_status"},
        CONCEPT_REAL_YAML_FRONTLOADED: {
            "incident_id",
            "affected_kpi",
            "root_cause",
            "id",
            "type",
            "title",
        },
        CONCEPT_REAL_YAML_PROVENANCE_LITE: {"last_verified", "lineage_status", "remediation_status"},
        CONCEPT_REAL_YAML_RELATIONAL_LITE: {"related_files"},
        CONCEPT_REAL_YAML_MINIMAL_LINKED: {"id", "type", "title", "related_files"},
    }
    forbidden_fields = {"task_hint", "routing_hint", "answer_fields"}

    for bundle, required_fields in expected_fields.items():
        all_fields = set()
        for path in bundle.rglob("*.md"):
            fm, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
            if fm is None:
                continue
            assert forbidden_fields.isdisjoint(fm), f"{bundle.name}: {path.relative_to(bundle)}"
            assert not any(key.startswith("fact_") for key in fm), f"{bundle.name}: {path.relative_to(bundle)}"

        for rel in CONCEPT_FRONTMATTER_TARGET_PATHS:
            fm, _ = parse_frontmatter((bundle / rel).read_text(encoding="utf-8"))
            assert fm is not None, f"{bundle.name}: {rel}"
            all_fields.update(fm)

        assert required_fields <= all_fields, bundle.name


def test_frontloaded_real_variant_puts_operational_fields_first():
    root_cause = (
        CONCEPT_REAL_YAML_FRONTLOADED
        / "enterprise-fnf"
        / "frontmatter-canary"
        / "incidents"
        / "2026-11-md-frontmatter-canary"
        / "root-cause.md"
    )

    assert _frontmatter_keys_in_order(root_cause)[:8] == [
        "incident_id",
        "affected_kpi",
        "affected_days",
        "root_cause",
        "metadata_source",
        "incorrect_source",
        "pipeline",
        "source_asset",
    ]


def test_lite_real_variants_omit_removed_noise_fields():
    provenance_noise = {"verification_method", "source_system", "reviewed_by"}
    relational_noise = {"related_assets", "related_signals", "related_incidents"}

    for rel in CONCEPT_FRONTMATTER_TARGET_PATHS:
        provenance_fm, _ = parse_frontmatter((CONCEPT_REAL_YAML_PROVENANCE_LITE / rel).read_text(encoding="utf-8"))
        relational_fm, _ = parse_frontmatter((CONCEPT_REAL_YAML_RELATIONAL_LITE / rel).read_text(encoding="utf-8"))
        minimal_linked_fm, _ = parse_frontmatter((CONCEPT_REAL_YAML_MINIMAL_LINKED / rel).read_text(encoding="utf-8"))

        assert provenance_fm is not None
        assert relational_fm is not None
        assert minimal_linked_fm is not None
        assert provenance_noise.isdisjoint(provenance_fm), rel
        assert relational_noise.isdisjoint(relational_fm), rel
        assert relational_noise.isdisjoint(minimal_linked_fm), rel
        assert {"domain", "system", "record_status", "last_verified"}.isdisjoint(minimal_linked_fm), rel


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


def test_graduated_no_distractor_score_for_single_stray_read(tmp_path):
    """One distractor read out of many should not zero out the no-distractors sub-score."""
    trace = {
        "duration_ms": 60000,
        "events": [
            {"type": "read", "path": "/incidents/2026-06-margin-anomaly/root-cause.md"},
            {"type": "read", "path": "/incidents/2026-06-margin-anomaly/remediation.md"},
            {"type": "read", "path": "/commerce/metrics/net-margin.md"},
            {"type": "read", "path": "/platform/features/pricing-shadow-ledger.md"},
            {"type": "read", "path": "/commerce/datasets/order-line-ledger.md"},
            {"type": "read", "path": "/incidents/2026-06-margin-anomaly/timeline.md"},
            {"type": "read", "path": "/commerce/index.md"},
            {"type": "read", "path": "/index.md"},
            {"type": "read", "path": "/incidents/index.md"},
            {"type": "read", "path": "/incidents/2026-06-margin-anomaly/index.md"},
            {"type": "read", "path": "/commerce/metrics/gross-margin.md"},  # one distractor
        ],
    }
    path = tmp_path / "single-distractor-trace.json"
    path.write_text(json.dumps(trace), encoding="utf-8")

    result = score_submission(
        STRICT,
        TASK,
        ROOT / "answers" / "example-correct.json",
        mode="strict",
        trace_path=path,
    )
    distractor_count = len(result["distractor_files_read"])
    unique_count = result["unique_files_read"]
    assert distractor_count == 1
    expected_no_distractors = max(0.0, 1.0 - distractor_count / unique_count)
    assert expected_no_distractors > 0.0, "one stray read should not fully zero out no-distractors"
    assert result["trace_score"] < 1.0


def test_empty_expected_facts_returns_perfect_accuracy(tmp_path):
    bundle = tmp_path / "bundle"
    concept_dir = bundle / "concepts"
    concept_dir.mkdir(parents=True)
    (bundle / "index.md").write_text("---\nokf_version: 0.1\n---\n# Root\n", encoding="utf-8")
    (concept_dir / "doc.md").write_text("---\ntype: concept\ntitle: Doc\n---\n# Doc\n", encoding="utf-8")

    task = {
        "task_id": "empty-facts-test",
        "expected_facts": {},
        "required_citations": [],
        "distractors": [],
    }
    task_path = tmp_path / "task.json"
    task_path.write_text(json.dumps(task), encoding="utf-8")

    submission = {"answer": "anything", "citations": []}
    sub_path = tmp_path / "submission.json"
    sub_path.write_text(json.dumps(submission), encoding="utf-8")

    result = score_submission(bundle, task_path, sub_path, mode="strict")
    assert result["accuracy_score"] == 1.0


def test_concept_file_body_text_ignored_by_evidence_validation():
    """Values in concept file body (not frontmatter) must NOT satisfy evidence validation."""
    result = score_submission(
        CONCEPT_CLEAN_BODY,
        CONCEPT_FRONTMATTER_CANARY_TASK,
        ROOT / "answers" / "concept-frontmatter-canary-correct.json",
        mode="extension",
    )
    assert result["accuracy_score"] == 0.0, (
        "body-only bundle must score 0 — evidence validation requires frontmatter, not body text"
    )
    assert len(result["unsupported"]) > 0, "facts must appear in unsupported, not incorrect"


def test_unsupported_count_appears_in_result():
    result = score_submission(
        CONCEPT_REAL_CONTROL,
        CONCEPT_FRONTMATTER_CANARY_TASK,
        ROOT / "answers" / "concept-frontmatter-canary-correct.json",
        mode="extension",
    )
    assert "unsupported_count" in result
    assert result["unsupported_count"] == len(result["unsupported"])
    assert result["unsupported_count"] > 0


def test_malformed_frontmatter_is_reported(tmp_path):
    bundle = tmp_path / "bundle"
    concept_dir = bundle / "bad"
    concept_dir.mkdir(parents=True)
    (bundle / "index.md").write_text("---\nokf_version: 0.1\n---\n# Root\n", encoding="utf-8")
    (concept_dir / "broken.md").write_text("---\ntype concept\n---\n# Broken\n", encoding="utf-8")

    result = validate_bundle(bundle, mode="strict")
    assert result["parseability"] == "fail"
    assert any("invalid frontmatter" in err for err in result["errors"])
