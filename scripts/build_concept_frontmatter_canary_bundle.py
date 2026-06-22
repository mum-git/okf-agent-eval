#!/usr/bin/env python3
"""Build a bundle variant that isolates concept-file YAML frontmatter.

The canary task asks for facts that appear only in non-index Markdown
frontmatter. Index files provide navigation, but they intentionally avoid the
answer-bearing field values.
"""

from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_BUNDLE = ROOT / "bundles" / "uniform-yaml-retail-ops"
CLEAN_SOURCE_BUNDLE = ROOT / "bundles" / "body-routed-indexes-retail-ops"
TARGET_BUNDLE = ROOT / "bundles" / "concept-frontmatter-canary-retail-ops"
STYLE_TARGET_BUNDLES = {
    "concept-frontmatter-sparse": ROOT / "bundles" / "concept-frontmatter-sparse-retail-ops",
    "concept-frontmatter-expanded": ROOT / "bundles" / "concept-frontmatter-expanded-retail-ops",
    "concept-frontmatter-quoted": ROOT / "bundles" / "concept-frontmatter-quoted-retail-ops",
}
CLEAN_TARGET_BUNDLES = {
    "concept-clean-body": ROOT / "bundles" / "concept-clean-body-retail-ops",
    "concept-clean-yaml-sparse": ROOT / "bundles" / "concept-clean-yaml-sparse-retail-ops",
    "concept-clean-yaml-okf": ROOT / "bundles" / "concept-clean-yaml-okf-retail-ops",
}
REAL_TARGET_BUNDLES = {
    "concept-real-control": ROOT / "bundles" / "concept-real-control-retail-ops",
    "concept-real-yaml-minimal": ROOT / "bundles" / "concept-real-yaml-minimal-retail-ops",
    "concept-real-yaml-typed": ROOT / "bundles" / "concept-real-yaml-typed-retail-ops",
    "concept-real-yaml-relational": ROOT / "bundles" / "concept-real-yaml-relational-retail-ops",
    "concept-real-yaml-provenance": ROOT / "bundles" / "concept-real-yaml-provenance-retail-ops",
    "concept-real-yaml-frontloaded": ROOT / "bundles" / "concept-real-yaml-frontloaded-retail-ops",
    "concept-real-yaml-provenance-lite": ROOT / "bundles" / "concept-real-yaml-provenance-lite-retail-ops",
    "concept-real-yaml-relational-lite": ROOT / "bundles" / "concept-real-yaml-relational-lite-retail-ops",
    "concept-real-yaml-minimal-linked": ROOT / "bundles" / "concept-real-yaml-minimal-linked-retail-ops",
    "concept-real-yaml-sparse": ROOT / "bundles" / "concept-real-yaml-sparse-retail-ops",
    "concept-real-yaml-okf": ROOT / "bundles" / "concept-real-yaml-okf-retail-ops",
}
CANARY_ROOT = TARGET_BUNDLE / "enterprise-fnf" / "frontmatter-canary"
CANARY_REL = Path("enterprise-fnf") / "frontmatter-canary"


def _append_once(path: Path, marker: str, addition: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    path.write_text(text.rstrip() + "\n\n" + addition.rstrip() + "\n", encoding="utf-8")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _split_frontmatter(text: str) -> tuple[str | None, str]:
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        raise SystemExit("unterminated frontmatter")
    return text[4:end], text[end + 5 :]


def _replace_frontmatter(path: Path, lines: list[str]) -> None:
    _, body = _split_frontmatter(path.read_text(encoding="utf-8"))
    path.write_text("---\n" + "\n".join(lines) + "\n---\n" + body.lstrip("\n"), encoding="utf-8")


def _strip_frontmatter_fields(bundle: Path, fields: set[str]) -> None:
    for path in bundle.rglob("*.md"):
        frontmatter, body = _split_frontmatter(path.read_text(encoding="utf-8"))
        if frontmatter is None:
            continue
        lines = [
            line for line in frontmatter.splitlines()
            if line.split(":", 1)[0].strip() not in fields
        ]
        path.write_text("---\n" + "\n".join(lines) + "\n---\n" + body.lstrip("\n"), encoding="utf-8")


def _write_clean_indexes(canary_root: Path) -> None:
    _write(
        canary_root / "index.md",
        """# Frontmatter Canary

Routing note: markdown concept metadata canary. Follow the incident and
registry entries below; the linked concept files carry the decisive values.

## Key entries:

- [Canary incident](incidents/2026-11-md-frontmatter-canary/index.md)
- [Canary registry](registry/index.md)
""",
    )
    _write(
        canary_root / "incidents" / "index.md",
        """# Canary Incidents

Routing note: inspect the dated canary incident and its linked concept files.

## Key entries:

- [November Markdown canary](2026-11-md-frontmatter-canary/index.md)
""",
    )
    _write(
        canary_root / "incidents" / "2026-11-md-frontmatter-canary" / "index.md",
        """# November Markdown Canary

Routing note: inspect the root cause and remediation concept files.

## Key entries:

- [Root cause](root-cause.md)
- [Remediation](remediation.md)
""",
    )
    _write(
        canary_root / "registry" / "index.md",
        """# Canary Registry

Routing note: inspect the signal registry concept file.

## Key entries:

- [Signal registry](signal-registry.md)
""",
    )


BODY_EVIDENCE_SECTION = """
## Body Evidence

body_evidence_marker: md-body-canary-pass
"""


def _write_canary_files() -> None:
    _write(
        CANARY_ROOT / "index.md",
        """---
type: directory_index
domain: enterprise-fnf
area: frontmatter-canary
depth: 2
metadata_profile: concept-frontmatter-canary
owner: enterprise-data-governance
task_hint: markdown concept metadata canary
routing_hint: inspect the canary incident and remediation concept files
---
# Frontmatter Canary

This branch validates that concept-file metadata is read from Markdown files,
not only from directory indexes.

- [Canary incident](incidents/2026-11-md-frontmatter-canary/index.md)
- [Canary registry](registry/index.md)
""",
    )
    _write(
        CANARY_ROOT / "incidents" / "index.md",
        """---
type: directory_index
domain: enterprise-fnf
area: frontmatter-canary-incidents
depth: 3
metadata_profile: concept-frontmatter-canary
owner: enterprise-data-governance
task_hint: markdown concept metadata canary
routing_hint: inspect the dated canary incident
---
# Canary Incidents

- [November Markdown canary](2026-11-md-frontmatter-canary/index.md)
""",
    )
    _write(
        CANARY_ROOT / "incidents" / "2026-11-md-frontmatter-canary" / "index.md",
        """---
type: directory_index
domain: enterprise-fnf
area: frontmatter-canary-incident
depth: 4
metadata_profile: concept-frontmatter-canary
owner: enterprise-data-governance
task_hint: markdown concept metadata canary
routing_hint: inspect root cause and remediation metadata blocks
---
# November Markdown Canary

The decisive canary values are stored in the metadata blocks of the concept
files linked below.

- [Root cause](root-cause.md)
- [Remediation](remediation.md)
""",
    )
    _write(
        CANARY_ROOT / "registry" / "index.md",
        """---
type: directory_index
domain: enterprise-fnf
area: frontmatter-canary-registry
depth: 3
metadata_profile: concept-frontmatter-canary
owner: enterprise-data-governance
task_hint: markdown concept metadata canary
routing_hint: inspect the registry concept metadata
---
# Canary Registry

- [Signal registry](signal-registry.md)
""",
    )
    _write(
        CANARY_ROOT / "incidents" / "2026-11-md-frontmatter-canary" / "root-cause.md",
        """---
id: okf.canary.actual_md_frontmatter.root_cause
type: root_cause
title: Actual Markdown frontmatter root cause canary
incident_id: ix-7q4-lumen-931
affected_kpi: quadrant ballast drift ratio
affected_days: 2026-11-03, 2026-11-08, 2026-11-19
root_cause: atlas lane emitted stale cobalt token
metadata_source: fm_src_kilo_73
incorrect_source: prose_scan_delta_12
pipeline: pipe_ozone_41q
source_asset: asset.vellum_quartz_908
tags:
  - okf-canary
  - concept-frontmatter
---
# Root Cause Canary

This page is intentionally sparse. The narrative explains that the source of
record is the metadata block above this heading, and it avoids spelling out the
required values in prose.

Agents that read only directory metadata or body paragraphs should not be able
to recover every requested fact from this page.
""" + BODY_EVIDENCE_SECTION,
    )
    _write(
        CANARY_ROOT / "incidents" / "2026-11-md-frontmatter-canary" / "remediation.md",
        """---
id: okf.canary.actual_md_frontmatter.remediation
type: remediation
title: Actual Markdown frontmatter remediation canary
incident_id: ix-7q4-lumen-931
remediation: promote extractor gate rhea-44 before cobalt merge
validation_marker: vm-jade-772-ok
owner: team-rivet-echo
tags:
  - okf-canary
  - concept-frontmatter
---
# Remediation Canary

The corrective action for this canary is represented as structured concept
metadata. The body confirms that the metadata block is authoritative without
duplicating the exact action text.
""" + BODY_EVIDENCE_SECTION,
    )
    _write(
        CANARY_ROOT / "registry" / "signal-registry.md",
        """---
id: okf.canary.actual_md_frontmatter.signal_registry
type: metric_registry
title: Actual Markdown frontmatter signal registry
incident_id: ix-7q4-lumen-931
signal_family: sigfam_umber_204
validation_marker: vm-jade-772-ok
owner: team-rivet-echo
tags:
  - okf-canary
  - concept-frontmatter
---
# Signal Registry

This registry entry exists to provide a second concept file with canary
metadata. The exact validation marker is intentionally metadata-only.
""" + BODY_EVIDENCE_SECTION,
    )


def _rewrite_sparse_concept_frontmatter(bundle: Path) -> None:
    canary = bundle / CANARY_REL
    _replace_frontmatter(
        canary / "incidents" / "2026-11-md-frontmatter-canary" / "root-cause.md",
        [
            "id: okf.canary.actual_md_frontmatter.root_cause",
            "type: root_cause",
            "title: Actual Markdown frontmatter root cause canary",
            "incident_id: ix-7q4-lumen-931",
            "affected_kpi: quadrant ballast drift ratio",
            "affected_days: 2026-11-03, 2026-11-08, 2026-11-19",
            "root_cause: atlas lane emitted stale cobalt token",
            "metadata_source: fm_src_kilo_73",
            "incorrect_source: prose_scan_delta_12",
            "pipeline: pipe_ozone_41q",
            "source_asset: asset.vellum_quartz_908",
        ],
    )
    _replace_frontmatter(
        canary / "incidents" / "2026-11-md-frontmatter-canary" / "remediation.md",
        [
            "id: okf.canary.actual_md_frontmatter.remediation",
            "type: remediation",
            "title: Actual Markdown frontmatter remediation canary",
            "remediation: promote extractor gate rhea-44 before cobalt merge",
            "validation_marker: vm-jade-772-ok",
            "owner: team-rivet-echo",
        ],
    )
    _replace_frontmatter(
        canary / "registry" / "signal-registry.md",
        [
            "id: okf.canary.actual_md_frontmatter.signal_registry",
            "type: metric_registry",
            "title: Actual Markdown frontmatter signal registry",
            "signal_family: sigfam_umber_204",
            "validation_marker: vm-jade-772-ok",
        ],
    )


def _rewrite_expanded_concept_frontmatter(bundle: Path) -> None:
    canary = bundle / CANARY_REL
    common = [
        "domain: enterprise-fnf",
        "metadata_profile: concept-frontmatter-expanded",
        "owner: team-rivet-echo",
        "task_hint: markdown concept metadata canary",
        "routing_hint: answer-bearing values are in this non-index concept frontmatter",
    ]
    _replace_frontmatter(
        canary / "incidents" / "2026-11-md-frontmatter-canary" / "root-cause.md",
        [
            "id: okf.canary.actual_md_frontmatter.root_cause",
            "type: root_cause",
            "title: Actual Markdown frontmatter root cause canary",
            "incident_id: ix-7q4-lumen-931",
            "area: frontmatter-canary-root-cause",
            "depth: 5",
            *common,
            "affected_kpi: quadrant ballast drift ratio",
            "affected_days: 2026-11-03, 2026-11-08, 2026-11-19",
            "root_cause: atlas lane emitted stale cobalt token",
            "metadata_source: fm_src_kilo_73",
            "incorrect_source: prose_scan_delta_12",
            "pipeline: pipe_ozone_41q",
            "source_asset: asset.vellum_quartz_908",
            "tags:",
            "  - okf-canary",
            "  - concept-frontmatter",
            "  - expanded",
        ],
    )
    _replace_frontmatter(
        canary / "incidents" / "2026-11-md-frontmatter-canary" / "remediation.md",
        [
            "id: okf.canary.actual_md_frontmatter.remediation",
            "type: remediation",
            "title: Actual Markdown frontmatter remediation canary",
            "incident_id: ix-7q4-lumen-931",
            "area: frontmatter-canary-remediation",
            "depth: 5",
            *common,
            "remediation: promote extractor gate rhea-44 before cobalt merge",
            "validation_marker: vm-jade-772-ok",
            "tags:",
            "  - okf-canary",
            "  - concept-frontmatter",
            "  - expanded",
        ],
    )
    _replace_frontmatter(
        canary / "registry" / "signal-registry.md",
        [
            "id: okf.canary.actual_md_frontmatter.signal_registry",
            "type: metric_registry",
            "title: Actual Markdown frontmatter signal registry",
            "incident_id: ix-7q4-lumen-931",
            "area: frontmatter-canary-registry",
            "depth: 4",
            *common,
            "signal_family: sigfam_umber_204",
            "validation_marker: vm-jade-772-ok",
            "tags:",
            "  - okf-canary",
            "  - concept-frontmatter",
            "  - expanded",
        ],
    )


def _rewrite_quoted_concept_frontmatter(bundle: Path) -> None:
    canary = bundle / CANARY_REL
    _replace_frontmatter(
        canary / "incidents" / "2026-11-md-frontmatter-canary" / "root-cause.md",
        [
            'id: "okf.canary.actual_md_frontmatter.root_cause"',
            'type: "root_cause"',
            'title: "Actual Markdown frontmatter root cause canary"',
            'incident_id: "ix-7q4-lumen-931"',
            'affected_kpi: "quadrant ballast drift ratio"',
            'affected_days: "2026-11-03, 2026-11-08, 2026-11-19"',
            'root_cause: "atlas lane emitted stale cobalt token"',
            'metadata_source: "fm_src_kilo_73"',
            'incorrect_source: "prose_scan_delta_12"',
            'pipeline: "pipe_ozone_41q"',
            'source_asset: "asset.vellum_quartz_908"',
            "tags:",
            '  - "okf-canary"',
            '  - "concept-frontmatter"',
        ],
    )
    _replace_frontmatter(
        canary / "incidents" / "2026-11-md-frontmatter-canary" / "remediation.md",
        [
            'id: "okf.canary.actual_md_frontmatter.remediation"',
            'type: "remediation"',
            'title: "Actual Markdown frontmatter remediation canary"',
            'incident_id: "ix-7q4-lumen-931"',
            'remediation: "promote extractor gate rhea-44 before cobalt merge"',
            'validation_marker: "vm-jade-772-ok"',
            'owner: "team-rivet-echo"',
            "tags:",
            '  - "okf-canary"',
            '  - "concept-frontmatter"',
        ],
    )
    _replace_frontmatter(
        canary / "registry" / "signal-registry.md",
        [
            'id: "okf.canary.actual_md_frontmatter.signal_registry"',
            'type: "metric_registry"',
            'title: "Actual Markdown frontmatter signal registry"',
            'incident_id: "ix-7q4-lumen-931"',
            'signal_family: "sigfam_umber_204"',
            'validation_marker: "vm-jade-772-ok"',
            'owner: "team-rivet-echo"',
            "tags:",
            '  - "okf-canary"',
            '  - "concept-frontmatter"',
        ],
    )


def _build_style_bundles() -> None:
    style_rewriters = {
        "concept-frontmatter-sparse": _rewrite_sparse_concept_frontmatter,
        "concept-frontmatter-expanded": _rewrite_expanded_concept_frontmatter,
        "concept-frontmatter-quoted": _rewrite_quoted_concept_frontmatter,
    }
    for style, target in STYLE_TARGET_BUNDLES.items():
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(TARGET_BUNDLE, target)
        style_rewriters[style](target)


def _write_clean_body_concepts(canary_root: Path) -> None:
    _write(
        canary_root / "incidents" / "2026-11-md-frontmatter-canary" / "root-cause.md",
        """---
id: okf.canary.actual_md_frontmatter.root_cause
type: root_cause
title: Actual Markdown frontmatter root cause canary
metadata_profile: clean-body-baseline
tags:
  - okf-canary
  - concept-body
---
# Root Cause Canary

This body-text baseline stores the decisive values in ordinary Markdown:

- incident_id: ix-7q4-lumen-931
- affected_kpi: quadrant ballast drift ratio
- affected_days: 2026-11-03, 2026-11-08, 2026-11-19
- root_cause: atlas lane emitted stale cobalt token
- metadata_source: fm_src_kilo_73
- incorrect_source: prose_scan_delta_12
- pipeline: pipe_ozone_41q
- source_asset: asset.vellum_quartz_908
""" + BODY_EVIDENCE_SECTION,
    )
    _write(
        canary_root / "incidents" / "2026-11-md-frontmatter-canary" / "remediation.md",
        """---
id: okf.canary.actual_md_frontmatter.remediation
type: remediation
title: Actual Markdown frontmatter remediation canary
metadata_profile: clean-body-baseline
tags:
  - okf-canary
  - concept-body
---
# Remediation Canary

This body-text baseline stores the decisive values in ordinary Markdown:

- remediation: promote extractor gate rhea-44 before cobalt merge
- owner: team-rivet-echo
- validation_marker: vm-jade-772-ok
""" + BODY_EVIDENCE_SECTION,
    )
    _write(
        canary_root / "registry" / "signal-registry.md",
        """---
id: okf.canary.actual_md_frontmatter.signal_registry
type: metric_registry
title: Actual Markdown frontmatter signal registry
metadata_profile: clean-body-baseline
tags:
  - okf-canary
  - concept-body
---
# Signal Registry

This body-text baseline stores the decisive value in ordinary Markdown:

- validation_marker: vm-jade-772-ok
- signal_family: sigfam_umber_204
""" + BODY_EVIDENCE_SECTION,
    )


def _write_clean_yaml_sparse_concepts(canary_root: Path) -> None:
    _write(
        canary_root / "incidents" / "2026-11-md-frontmatter-canary" / "root-cause.md",
        """---
id: okf.canary.actual_md_frontmatter.root_cause
type: root_cause
title: Actual Markdown frontmatter root cause canary
incident_id: ix-7q4-lumen-931
affected_kpi: quadrant ballast drift ratio
affected_days: 2026-11-03, 2026-11-08, 2026-11-19
root_cause: atlas lane emitted stale cobalt token
metadata_source: fm_src_kilo_73
incorrect_source: prose_scan_delta_12
pipeline: pipe_ozone_41q
source_asset: asset.vellum_quartz_908
---
# Root Cause Canary

The decisive values for this sparse-YAML treatment are intentionally stored only
in the metadata block above.
""" + BODY_EVIDENCE_SECTION,
    )
    _write(
        canary_root / "incidents" / "2026-11-md-frontmatter-canary" / "remediation.md",
        """---
id: okf.canary.actual_md_frontmatter.remediation
type: remediation
title: Actual Markdown frontmatter remediation canary
remediation: promote extractor gate rhea-44 before cobalt merge
owner: team-rivet-echo
validation_marker: vm-jade-772-ok
---
# Remediation Canary

The decisive values for this sparse-YAML treatment are intentionally stored only
in the metadata block above.
""" + BODY_EVIDENCE_SECTION,
    )
    _write(
        canary_root / "registry" / "signal-registry.md",
        """---
id: okf.canary.actual_md_frontmatter.signal_registry
type: metric_registry
title: Actual Markdown frontmatter signal registry
signal_family: sigfam_umber_204
validation_marker: vm-jade-772-ok
---
# Signal Registry

The decisive value for this sparse-YAML treatment is intentionally stored only
in the metadata block above.
""" + BODY_EVIDENCE_SECTION,
    )


def _write_clean_yaml_okf_concepts(canary_root: Path) -> None:
    common = [
        "domain: enterprise-fnf",
        "metadata_profile: clean-okf-concept-yaml",
        "owner: team-rivet-echo",
        "task_hint: markdown concept metadata canary",
        "routing_hint: inspect non-index concept frontmatter",
    ]
    _write(
        canary_root / "incidents" / "2026-11-md-frontmatter-canary" / "root-cause.md",
        "---\n"
        + "\n".join([
            "id: okf.canary.actual_md_frontmatter.root_cause",
            "type: root_cause",
            "title: Actual Markdown frontmatter root cause canary",
            "incident_id: ix-7q4-lumen-931",
            "area: frontmatter-canary-root-cause",
            "depth: 5",
            *common,
            "affected_kpi: quadrant ballast drift ratio",
            "affected_days: 2026-11-03, 2026-11-08, 2026-11-19",
            "root_cause: atlas lane emitted stale cobalt token",
            "metadata_source: fm_src_kilo_73",
            "incorrect_source: prose_scan_delta_12",
            "pipeline: pipe_ozone_41q",
            "source_asset: asset.vellum_quartz_908",
            "tags:",
            "  - okf-canary",
            "  - concept-frontmatter",
            "  - clean-okf",
        ])
        + "\n---\n"
        + """# Root Cause Canary

The decisive values for this OKF-style YAML treatment are intentionally stored
only in the metadata block above.
""" + BODY_EVIDENCE_SECTION,
    )
    _write(
        canary_root / "incidents" / "2026-11-md-frontmatter-canary" / "remediation.md",
        "---\n"
        + "\n".join([
            "id: okf.canary.actual_md_frontmatter.remediation",
            "type: remediation",
            "title: Actual Markdown frontmatter remediation canary",
            "incident_id: ix-7q4-lumen-931",
            "area: frontmatter-canary-remediation",
            "depth: 5",
            *common,
            "remediation: promote extractor gate rhea-44 before cobalt merge",
            "validation_marker: vm-jade-772-ok",
            "tags:",
            "  - okf-canary",
            "  - concept-frontmatter",
            "  - clean-okf",
        ])
        + "\n---\n"
        + """# Remediation Canary

The decisive values for this OKF-style YAML treatment are intentionally stored
only in the metadata block above.
""" + BODY_EVIDENCE_SECTION,
    )
    _write(
        canary_root / "registry" / "signal-registry.md",
        "---\n"
        + "\n".join([
            "id: okf.canary.actual_md_frontmatter.signal_registry",
            "type: metric_registry",
            "title: Actual Markdown frontmatter signal registry",
            "incident_id: ix-7q4-lumen-931",
            "area: frontmatter-canary-registry",
            "depth: 4",
            *common,
            "signal_family: sigfam_umber_204",
            "validation_marker: vm-jade-772-ok",
            "tags:",
            "  - okf-canary",
            "  - concept-frontmatter",
            "  - clean-okf",
        ])
        + "\n---\n"
        + """# Signal Registry

The decisive value for this OKF-style YAML treatment is intentionally stored
only in the metadata block above.
""" + BODY_EVIDENCE_SECTION,
    )


REAL_ROOT_CAUSE_BODY = """# Root Cause Canary

This concept file is part of the November metadata canary investigation. The
Markdown body is deliberately identical across clean real variants so benchmark
results isolate the value and shape of the frontmatter block.

## Analyst Notes

Use this file together with the remediation and signal registry concept files
when preparing citations.
"""


REAL_REMEDIATION_BODY = """# Remediation Canary

This concept file is part of the November metadata canary investigation. The
Markdown body is deliberately identical across clean real variants so benchmark
results isolate the value and shape of the frontmatter block.

## Analyst Notes

Use this file together with the root cause and signal registry concept files
when preparing citations.
"""


REAL_SIGNAL_BODY = """# Signal Registry

This concept file is part of the November metadata canary investigation. The
Markdown body is deliberately identical across clean real variants so benchmark
results isolate the value and shape of the frontmatter block.

## Analyst Notes

Use this file together with the root cause and remediation concept files when
preparing citations.
"""


def _write_real_concepts(canary_root: Path, *, style: str) -> None:
    if style == "control":
        root_fm = [
            "id: okf.canary.actual_md_frontmatter.root_cause",
            "type: root_cause",
            "title: Actual Markdown frontmatter root cause canary",
        ]
        remediation_fm = [
            "id: okf.canary.actual_md_frontmatter.remediation",
            "type: remediation",
            "title: Actual Markdown frontmatter remediation canary",
        ]
        signal_fm = [
            "id: okf.canary.actual_md_frontmatter.signal_registry",
            "type: metric_registry",
            "title: Actual Markdown frontmatter signal registry",
        ]
    elif style in {"sparse", "minimal"}:
        root_fm = [
            "id: okf.canary.actual_md_frontmatter.root_cause",
            "type: root_cause",
            "title: Actual Markdown frontmatter root cause canary",
            "incident_id: ix-7q4-lumen-931",
            "affected_kpi: quadrant ballast drift ratio",
            "affected_days: 2026-11-03, 2026-11-08, 2026-11-19",
            "root_cause: atlas lane emitted stale cobalt token",
            "metadata_source: fm_src_kilo_73",
            "incorrect_source: prose_scan_delta_12",
            "pipeline: pipe_ozone_41q",
            "source_asset: asset.vellum_quartz_908",
        ]
        remediation_fm = [
            "id: okf.canary.actual_md_frontmatter.remediation",
            "type: remediation",
            "title: Actual Markdown frontmatter remediation canary",
            "remediation: promote extractor gate rhea-44 before cobalt merge",
            "owner: team-rivet-echo",
        ]
        signal_fm = [
            "id: okf.canary.actual_md_frontmatter.signal_registry",
            "type: metric_registry",
            "title: Actual Markdown frontmatter signal registry",
            "signal_family: sigfam_umber_204",
            "validation_marker: vm-jade-772-ok",
        ]
    elif style == "typed":
        common = [
            "domain: enterprise-fnf",
            "system: metadata-ingestion",
            "record_status: active",
            "owner: team-rivet-echo",
        ]
        root_fm = [
            "id: okf.canary.actual_md_frontmatter.root_cause",
            "type: root_cause",
            "title: Actual Markdown frontmatter root cause canary",
            *common,
            "incident_id: ix-7q4-lumen-931",
            "affected_kpi: quadrant ballast drift ratio",
            "affected_days: 2026-11-03, 2026-11-08, 2026-11-19",
            "root_cause: atlas lane emitted stale cobalt token",
            "metadata_source: fm_src_kilo_73",
            "incorrect_source: prose_scan_delta_12",
            "pipeline: pipe_ozone_41q",
            "source_asset: asset.vellum_quartz_908",
        ]
        remediation_fm = [
            "id: okf.canary.actual_md_frontmatter.remediation",
            "type: remediation",
            "title: Actual Markdown frontmatter remediation canary",
            *common,
            "incident_id: ix-7q4-lumen-931",
            "remediation: promote extractor gate rhea-44 before cobalt merge",
        ]
        signal_fm = [
            "id: okf.canary.actual_md_frontmatter.signal_registry",
            "type: metric_registry",
            "title: Actual Markdown frontmatter signal registry",
            *common,
            "incident_id: ix-7q4-lumen-931",
            "signal_family: sigfam_umber_204",
            "validation_marker: vm-jade-772-ok",
        ]
    elif style == "relational":
        common = [
            "domain: enterprise-fnf",
            "system: metadata-ingestion",
            "owner: team-rivet-echo",
            "record_status: active",
        ]
        root_fm = [
            "id: okf.canary.actual_md_frontmatter.root_cause",
            "type: root_cause",
            "title: Actual Markdown frontmatter root cause canary",
            *common,
            "incident_id: ix-7q4-lumen-931",
            "affected_kpi: quadrant ballast drift ratio",
            "affected_days: 2026-11-03, 2026-11-08, 2026-11-19",
            "root_cause: atlas lane emitted stale cobalt token",
            "metadata_source: fm_src_kilo_73",
            "incorrect_source: prose_scan_delta_12",
            "pipeline: pipe_ozone_41q",
            "source_asset: asset.vellum_quartz_908",
            "related_assets:",
            "  - asset.vellum_quartz_908",
            "related_signals:",
            "  - sigfam_umber_204",
            "related_files:",
            "  - remediation.md",
            "  - ../../registry/signal-registry.md",
        ]
        remediation_fm = [
            "id: okf.canary.actual_md_frontmatter.remediation",
            "type: remediation",
            "title: Actual Markdown frontmatter remediation canary",
            *common,
            "incident_id: ix-7q4-lumen-931",
            "remediation: promote extractor gate rhea-44 before cobalt merge",
            "related_incidents:",
            "  - ix-7q4-lumen-931",
            "related_files:",
            "  - root-cause.md",
            "  - ../../registry/signal-registry.md",
        ]
        signal_fm = [
            "id: okf.canary.actual_md_frontmatter.signal_registry",
            "type: metric_registry",
            "title: Actual Markdown frontmatter signal registry",
            *common,
            "incident_id: ix-7q4-lumen-931",
            "signal_family: sigfam_umber_204",
            "validation_marker: vm-jade-772-ok",
            "related_assets:",
            "  - asset.vellum_quartz_908",
            "related_files:",
            "  - ../incidents/2026-11-md-frontmatter-canary/root-cause.md",
            "  - ../incidents/2026-11-md-frontmatter-canary/remediation.md",
        ]
    elif style == "provenance":
        common = [
            "domain: enterprise-fnf",
            "system: metadata-ingestion",
            "owner: team-rivet-echo",
            "record_status: active",
            "last_verified: 2026-11-21",
            "verification_method: source-replay",
        ]
        root_fm = [
            "id: okf.canary.actual_md_frontmatter.root_cause",
            "type: root_cause",
            "title: Actual Markdown frontmatter root cause canary",
            *common,
            "incident_id: ix-7q4-lumen-931",
            "affected_kpi: quadrant ballast drift ratio",
            "affected_days: 2026-11-03, 2026-11-08, 2026-11-19",
            "root_cause: atlas lane emitted stale cobalt token",
            "metadata_source: fm_src_kilo_73",
            "incorrect_source: prose_scan_delta_12",
            "pipeline: pipe_ozone_41q",
            "source_asset: asset.vellum_quartz_908",
            "source_system: fm_src_kilo_73",
            "lineage_status: verified",
        ]
        remediation_fm = [
            "id: okf.canary.actual_md_frontmatter.remediation",
            "type: remediation",
            "title: Actual Markdown frontmatter remediation canary",
            *common,
            "incident_id: ix-7q4-lumen-931",
            "remediation: promote extractor gate rhea-44 before cobalt merge",
            "remediation_status: approved",
            "reviewed_by: team-rivet-echo",
        ]
        signal_fm = [
            "id: okf.canary.actual_md_frontmatter.signal_registry",
            "type: metric_registry",
            "title: Actual Markdown frontmatter signal registry",
            *common,
            "incident_id: ix-7q4-lumen-931",
            "signal_family: sigfam_umber_204",
            "validation_marker: vm-jade-772-ok",
            "source_system: fm_src_kilo_73",
            "lineage_status: verified",
        ]
    elif style == "frontloaded":
        common = [
            "domain: enterprise-fnf",
            "system: metadata-ingestion",
            "owner: team-rivet-echo",
            "record_status: active",
        ]
        root_fm = [
            "incident_id: ix-7q4-lumen-931",
            "affected_kpi: quadrant ballast drift ratio",
            "affected_days: 2026-11-03, 2026-11-08, 2026-11-19",
            "root_cause: atlas lane emitted stale cobalt token",
            "metadata_source: fm_src_kilo_73",
            "incorrect_source: prose_scan_delta_12",
            "pipeline: pipe_ozone_41q",
            "source_asset: asset.vellum_quartz_908",
            "id: okf.canary.actual_md_frontmatter.root_cause",
            "type: root_cause",
            "title: Actual Markdown frontmatter root cause canary",
            *common,
        ]
        remediation_fm = [
            "remediation: promote extractor gate rhea-44 before cobalt merge",
            "owner: team-rivet-echo",
            "incident_id: ix-7q4-lumen-931",
            "id: okf.canary.actual_md_frontmatter.remediation",
            "type: remediation",
            "title: Actual Markdown frontmatter remediation canary",
            "domain: enterprise-fnf",
            "system: metadata-ingestion",
            "record_status: active",
        ]
        signal_fm = [
            "signal_family: sigfam_umber_204",
            "validation_marker: vm-jade-772-ok",
            "incident_id: ix-7q4-lumen-931",
            "id: okf.canary.actual_md_frontmatter.signal_registry",
            "type: metric_registry",
            "title: Actual Markdown frontmatter signal registry",
            *common,
        ]
    elif style == "provenance-lite":
        common = [
            "domain: enterprise-fnf",
            "system: metadata-ingestion",
            "owner: team-rivet-echo",
            "record_status: active",
            "last_verified: 2026-11-21",
        ]
        root_fm = [
            "id: okf.canary.actual_md_frontmatter.root_cause",
            "type: root_cause",
            "title: Actual Markdown frontmatter root cause canary",
            *common,
            "incident_id: ix-7q4-lumen-931",
            "affected_kpi: quadrant ballast drift ratio",
            "affected_days: 2026-11-03, 2026-11-08, 2026-11-19",
            "root_cause: atlas lane emitted stale cobalt token",
            "metadata_source: fm_src_kilo_73",
            "incorrect_source: prose_scan_delta_12",
            "pipeline: pipe_ozone_41q",
            "source_asset: asset.vellum_quartz_908",
            "lineage_status: verified",
        ]
        remediation_fm = [
            "id: okf.canary.actual_md_frontmatter.remediation",
            "type: remediation",
            "title: Actual Markdown frontmatter remediation canary",
            *common,
            "incident_id: ix-7q4-lumen-931",
            "remediation: promote extractor gate rhea-44 before cobalt merge",
            "remediation_status: approved",
        ]
        signal_fm = [
            "id: okf.canary.actual_md_frontmatter.signal_registry",
            "type: metric_registry",
            "title: Actual Markdown frontmatter signal registry",
            *common,
            "incident_id: ix-7q4-lumen-931",
            "signal_family: sigfam_umber_204",
            "validation_marker: vm-jade-772-ok",
            "lineage_status: verified",
        ]
    elif style == "relational-lite":
        common = [
            "domain: enterprise-fnf",
            "system: metadata-ingestion",
            "owner: team-rivet-echo",
            "record_status: active",
        ]
        root_fm = [
            "id: okf.canary.actual_md_frontmatter.root_cause",
            "type: root_cause",
            "title: Actual Markdown frontmatter root cause canary",
            *common,
            "incident_id: ix-7q4-lumen-931",
            "affected_kpi: quadrant ballast drift ratio",
            "affected_days: 2026-11-03, 2026-11-08, 2026-11-19",
            "root_cause: atlas lane emitted stale cobalt token",
            "metadata_source: fm_src_kilo_73",
            "incorrect_source: prose_scan_delta_12",
            "pipeline: pipe_ozone_41q",
            "source_asset: asset.vellum_quartz_908",
            "related_files:",
            "  - remediation.md",
            "  - ../../registry/signal-registry.md",
        ]
        remediation_fm = [
            "id: okf.canary.actual_md_frontmatter.remediation",
            "type: remediation",
            "title: Actual Markdown frontmatter remediation canary",
            *common,
            "incident_id: ix-7q4-lumen-931",
            "remediation: promote extractor gate rhea-44 before cobalt merge",
            "related_files:",
            "  - root-cause.md",
            "  - ../../registry/signal-registry.md",
        ]
        signal_fm = [
            "id: okf.canary.actual_md_frontmatter.signal_registry",
            "type: metric_registry",
            "title: Actual Markdown frontmatter signal registry",
            *common,
            "incident_id: ix-7q4-lumen-931",
            "signal_family: sigfam_umber_204",
            "validation_marker: vm-jade-772-ok",
            "related_files:",
            "  - ../incidents/2026-11-md-frontmatter-canary/root-cause.md",
            "  - ../incidents/2026-11-md-frontmatter-canary/remediation.md",
        ]
    elif style == "minimal-linked":
        root_fm = [
            "id: okf.canary.actual_md_frontmatter.root_cause",
            "type: root_cause",
            "title: Actual Markdown frontmatter root cause canary",
            "incident_id: ix-7q4-lumen-931",
            "affected_kpi: quadrant ballast drift ratio",
            "affected_days: 2026-11-03, 2026-11-08, 2026-11-19",
            "root_cause: atlas lane emitted stale cobalt token",
            "metadata_source: fm_src_kilo_73",
            "incorrect_source: prose_scan_delta_12",
            "pipeline: pipe_ozone_41q",
            "source_asset: asset.vellum_quartz_908",
            "related_files:",
            "  - remediation.md",
            "  - ../../registry/signal-registry.md",
        ]
        remediation_fm = [
            "id: okf.canary.actual_md_frontmatter.remediation",
            "type: remediation",
            "title: Actual Markdown frontmatter remediation canary",
            "remediation: promote extractor gate rhea-44 before cobalt merge",
            "owner: team-rivet-echo",
            "related_files:",
            "  - root-cause.md",
            "  - ../../registry/signal-registry.md",
        ]
        signal_fm = [
            "id: okf.canary.actual_md_frontmatter.signal_registry",
            "type: metric_registry",
            "title: Actual Markdown frontmatter signal registry",
            "signal_family: sigfam_umber_204",
            "validation_marker: vm-jade-772-ok",
            "related_files:",
            "  - ../incidents/2026-11-md-frontmatter-canary/root-cause.md",
            "  - ../incidents/2026-11-md-frontmatter-canary/remediation.md",
        ]
    elif style == "okf":
        common = [
            "domain: enterprise-fnf",
            "metadata_profile: real-okf-concept-yaml",
            "owner: team-rivet-echo",
            "task_hint: november metadata canary investigation",
            "routing_hint: combine root cause, remediation, and signal registry concept metadata",
        ]
        root_fm = [
            "id: okf.canary.actual_md_frontmatter.root_cause",
            "type: root_cause",
            "title: Actual Markdown frontmatter root cause canary",
            "incident_id: ix-7q4-lumen-931",
            "area: frontmatter-canary-root-cause",
            "depth: 5",
            *common,
            "affected_kpi: quadrant ballast drift ratio",
            "affected_days: 2026-11-03, 2026-11-08, 2026-11-19",
            "root_cause: atlas lane emitted stale cobalt token",
            "metadata_source: fm_src_kilo_73",
            "incorrect_source: prose_scan_delta_12",
            "pipeline: pipe_ozone_41q",
            "source_asset: asset.vellum_quartz_908",
            "tags:",
            "  - okf-canary",
            "  - concept-frontmatter",
            "  - real-okf",
        ]
        remediation_fm = [
            "id: okf.canary.actual_md_frontmatter.remediation",
            "type: remediation",
            "title: Actual Markdown frontmatter remediation canary",
            "incident_id: ix-7q4-lumen-931",
            "area: frontmatter-canary-remediation",
            "depth: 5",
            *common,
            "remediation: promote extractor gate rhea-44 before cobalt merge",
            "tags:",
            "  - okf-canary",
            "  - concept-frontmatter",
            "  - real-okf",
        ]
        signal_fm = [
            "id: okf.canary.actual_md_frontmatter.signal_registry",
            "type: metric_registry",
            "title: Actual Markdown frontmatter signal registry",
            "incident_id: ix-7q4-lumen-931",
            "area: frontmatter-canary-registry",
            "depth: 4",
            *common,
            "signal_family: sigfam_umber_204",
            "validation_marker: vm-jade-772-ok",
            "tags:",
            "  - okf-canary",
            "  - concept-frontmatter",
            "  - real-okf",
        ]
    else:
        raise ValueError(f"unknown real concept style: {style}")

    _write(
        canary_root / "incidents" / "2026-11-md-frontmatter-canary" / "root-cause.md",
        "---\n" + "\n".join(root_fm) + "\n---\n" + REAL_ROOT_CAUSE_BODY,
    )
    _write(
        canary_root / "incidents" / "2026-11-md-frontmatter-canary" / "remediation.md",
        "---\n" + "\n".join(remediation_fm) + "\n---\n" + REAL_REMEDIATION_BODY,
    )
    _write(
        canary_root / "registry" / "signal-registry.md",
        "---\n" + "\n".join(signal_fm) + "\n---\n" + REAL_SIGNAL_BODY,
    )


def _build_clean_bundle(target: Path, writer) -> None:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(CLEAN_SOURCE_BUNDLE, target)
    _append_once(
        target / "enterprise-fnf" / "index.md",
        "frontmatter-canary/index.md",
        "- [Frontmatter canary](frontmatter-canary/index.md)",
    )
    canary_root = target / CANARY_REL
    _write_clean_indexes(canary_root)
    writer(canary_root)


def _build_clean_bundles() -> None:
    _build_clean_bundle(CLEAN_TARGET_BUNDLES["concept-clean-body"], _write_clean_body_concepts)
    _build_clean_bundle(CLEAN_TARGET_BUNDLES["concept-clean-yaml-sparse"], _write_clean_yaml_sparse_concepts)
    _build_clean_bundle(CLEAN_TARGET_BUNDLES["concept-clean-yaml-okf"], _write_clean_yaml_okf_concepts)


def _build_real_bundle(target: Path, *, style: str) -> None:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(CLEAN_SOURCE_BUNDLE, target)
    if style in {
        "minimal",
        "typed",
        "relational",
        "provenance",
        "frontloaded",
        "provenance-lite",
        "relational-lite",
        "minimal-linked",
    }:
        _strip_frontmatter_fields(target, {"task_hint", "routing_hint", "answer_fields"})
    _append_once(
        target / "enterprise-fnf" / "index.md",
        "frontmatter-canary/index.md",
        "- [Frontmatter canary](frontmatter-canary/index.md)",
    )
    canary_root = target / CANARY_REL
    _write_clean_indexes(canary_root)
    _write_real_concepts(canary_root, style=style)


def _build_real_bundles() -> None:
    _build_real_bundle(REAL_TARGET_BUNDLES["concept-real-control"], style="control")
    _build_real_bundle(REAL_TARGET_BUNDLES["concept-real-yaml-minimal"], style="minimal")
    _build_real_bundle(REAL_TARGET_BUNDLES["concept-real-yaml-typed"], style="typed")
    _build_real_bundle(REAL_TARGET_BUNDLES["concept-real-yaml-relational"], style="relational")
    _build_real_bundle(REAL_TARGET_BUNDLES["concept-real-yaml-provenance"], style="provenance")
    _build_real_bundle(REAL_TARGET_BUNDLES["concept-real-yaml-frontloaded"], style="frontloaded")
    _build_real_bundle(REAL_TARGET_BUNDLES["concept-real-yaml-provenance-lite"], style="provenance-lite")
    _build_real_bundle(REAL_TARGET_BUNDLES["concept-real-yaml-relational-lite"], style="relational-lite")
    _build_real_bundle(REAL_TARGET_BUNDLES["concept-real-yaml-minimal-linked"], style="minimal-linked")
    _build_real_bundle(REAL_TARGET_BUNDLES["concept-real-yaml-sparse"], style="sparse")
    _build_real_bundle(REAL_TARGET_BUNDLES["concept-real-yaml-okf"], style="okf")


def main() -> int:
    if not SOURCE_BUNDLE.exists():
        raise SystemExit(f"source bundle not found: {SOURCE_BUNDLE}")
    if not CLEAN_SOURCE_BUNDLE.exists():
        raise SystemExit(f"clean source bundle not found: {CLEAN_SOURCE_BUNDLE}")

    if TARGET_BUNDLE.exists():
        shutil.rmtree(TARGET_BUNDLE)
    shutil.copytree(SOURCE_BUNDLE, TARGET_BUNDLE)

    _append_once(
        TARGET_BUNDLE / "enterprise-fnf" / "index.md",
        "frontmatter-canary/index.md",
        "- [Frontmatter canary](frontmatter-canary/index.md)",
    )
    _write_canary_files()
    _build_style_bundles()
    _build_clean_bundles()
    _build_real_bundles()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
