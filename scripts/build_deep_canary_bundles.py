#!/usr/bin/env python3
"""Build deep-canary L2 and L3 levels into all viable canary bundle variants.

L1 (baseline, existing): 3 files in 1 branch under enterprise-fnf/frontmatter-canary/
  — ~5 hops to deepest concept file.

L2 (multi-branch, ~6-7 hops): 3 files across 3 separate branches inside a new
  deep-retail-ops/canary-l2/ area. Incident branch at depth 5, pipeline/wallet
  branch at depth 7, registry branch at depth 4. Different incident
  (ix-4m7-prism-602) so facts cannot bleed from L1 memory.

L3 (cross-branch, max depth, ~5-10 hops): 3 files in a new
  deep-retail-ops/nexus-canary/ area with three branches of radically different
  depths — incident at depth 5, regions/experiments branch at depth 10,
  warehouse/tables branch at depth 7. Different incident (ix-9r2-nexus-774).

Run AFTER build_concept_frontmatter_canary_bundle.py.

Usage:
    python3 scripts/build_deep_canary_bundles.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# ─── Level fact values ────────────────────────────────────────────────────────

L2_FACTS: dict[str, str] = {
    "incident_id": "ix-4m7-prism-602",
    "affected_kpi": "azimuth freight yield variance",
    "affected_days": "2026-12-01, 2026-12-05, 2026-12-14",
    "root_cause": "solstice relay injected expired cadmium snapshot",
    "metadata_source": "fm_src_delta_88",
    "incorrect_source": "cache_scan_epsilon_31",
    "pipeline": "pipe_argon_77x",
    "source_asset": "asset.tungsten_slate_441",
    "remediation": "rotate cadmium snapshot before solstice relay sync",
    "owner": "team-cobalt-sigma",
    "signal_family": "sigfam_violet_115",
    "validation_marker": "vm-obsidian-334-ok",
}

L3_FACTS: dict[str, str] = {
    "incident_id": "ix-9r2-nexus-774",
    "affected_kpi": "boreal margin capture index",
    "affected_days": "2027-01-07, 2027-01-13, 2027-01-22",
    "root_cause": "helios bridge wrote misaligned quartz ledger epoch",
    "metadata_source": "fm_src_gamma_51",
    "incorrect_source": "stream_scan_zeta_09",
    "pipeline": "pipe_krypton_19b",
    "source_asset": "asset.obsidian_reef_207",
    "remediation": "flush quartz ledger epoch before helios bridge warmup",
    "owner": "team-mercury-delta",
    "signal_family": "sigfam_crimson_088",
    "validation_marker": "vm-beryl-559-ok",
}

# Required citation paths relative to bundle root
L2_REQUIRED_CITATIONS = [
    "/deep-retail-ops/canary-l2/incidents/2026-12-prism/root-cause.md",
    "/deep-retail-ops/canary-l2/pipelines/commerce/checkout/wallet/canary-remediation.md",
    "/deep-retail-ops/canary-l2/registry/signal-registry.md",
]

L3_REQUIRED_CITATIONS = [
    "/deep-retail-ops/nexus-canary/incident/2027-01-nexus/root-cause.md",
    "/deep-retail-ops/nexus-canary/regions/na/pacific/commerce/checkout/experiments/2027-q1/canary-remediation.md",
    "/deep-retail-ops/nexus-canary/warehouse/schemas/settlement/tables/canary-signal.md",
]

# Variants: bundle name (without -retail-ops) → concept frontmatter style
VARIANTS: dict[str, str] = {
    "concept-real-yaml-minimal": "minimal",
    "concept-real-yaml-minimal-linked": "minimal-linked",
    "concept-real-yaml-relational-lite": "relational-lite",
    "concept-clean-body": "clean-body",
    "concept-clean-yaml-sparse": "clean-yaml-sparse",
    "concept-clean-yaml-okf": "clean-yaml-okf",
    "concept-frontmatter-canary": "canary",
    "concept-frontmatter-sparse": "frontmatter-sparse",
    "concept-frontmatter-expanded": "frontmatter-expanded",
    "concept-frontmatter-quoted": "frontmatter-quoted",
}

# Styles where index files carry OKF YAML (task_hint, routing_hint)
YAML_INDEX_STYLES = frozenset({"canary", "frontmatter-sparse", "frontmatter-expanded", "frontmatter-quoted"})

# ─── Utilities ────────────────────────────────────────────────────────────────

def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _append_once(path: Path, marker: str, addition: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    path.write_text(text.rstrip() + "\n\n" + addition.rstrip() + "\n", encoding="utf-8")


# ─── Index file content ───────────────────────────────────────────────────────

def _body_index(title: str, routing_note: str, entries: list[tuple[str, str]]) -> str:
    lines = [f"# {title}", "", f"Routing note: {routing_note}.", "", "## Key entries:", ""]
    lines += [f"- [{label}]({path})" for label, path in entries]
    return "\n".join(lines) + "\n"


def _yaml_index(
    title: str,
    area: str,
    depth: int,
    task_hint: str,
    routing_hint: str,
    entries: list[tuple[str, str]],
    domain: str = "deep-retail-ops",
) -> str:
    fm = "\n".join([
        "---",
        "type: directory_index",
        f"domain: {domain}",
        f"area: {area}",
        f"depth: {depth}",
        "metadata_profile: deep-canary",
        "owner: knowledge-team",
        f"task_hint: {task_hint}",
        f"routing_hint: {routing_hint}",
        "---",
    ])
    body = f"# {title}\n\n" + "\n".join(f"- [{l}]({p})" for l, p in entries) + "\n"
    return fm + "\n" + body


def _index(
    title: str,
    area: str,
    depth: int,
    task_hint: str,
    routing_hint: str,
    entries: list[tuple[str, str]],
    style: str,
    domain: str = "deep-retail-ops",
) -> str:
    if style in YAML_INDEX_STYLES:
        return _yaml_index(title, area, depth, task_hint, routing_hint, entries, domain)
    return _body_index(title, routing_hint, entries)


# ─── Concept file content ─────────────────────────────────────────────────────

_CONCEPT_BODY = """
This concept file is part of the deep canary investigation. The Markdown body
is deliberately identical across variants so benchmark results isolate the
value and shape of the frontmatter block.

## Analyst Notes

Use this file together with the other deep canary concept files when preparing
citations.
"""


def _fm_lines(
    file_role: str,
    facts: dict[str, str],
    style: str,
    level: str,
    related_files: list[str] | None = None,
) -> list[str]:
    """Return YAML frontmatter lines (without --- delimiters) for a concept file."""
    base_id = f"okf.canary.{level}.{file_role.replace('-', '_')}"
    base_type = {
        "root-cause": "root_cause",
        "remediation": "remediation",
        "signal-registry": "metric_registry",
    }[file_role]
    base_title = f"Deep canary {level} {file_role}"

    identity = [
        f"id: {base_id}",
        f"type: {base_type}",
        f"title: {base_title}",
    ]

    if file_role == "root-cause":
        answer = [
            f"incident_id: {facts['incident_id']}",
            f"affected_kpi: {facts['affected_kpi']}",
            f"affected_days: {facts['affected_days']}",
            f"root_cause: {facts['root_cause']}",
            f"metadata_source: {facts['metadata_source']}",
            f"incorrect_source: {facts['incorrect_source']}",
            f"pipeline: {facts['pipeline']}",
            f"source_asset: {facts['source_asset']}",
        ]
    elif file_role == "remediation":
        answer = [
            f"incident_id: {facts['incident_id']}",
            f"remediation: {facts['remediation']}",
            f"owner: {facts['owner']}",
        ]
    else:  # signal-registry
        answer = [
            f"incident_id: {facts['incident_id']}",
            f"signal_family: {facts['signal_family']}",
            f"validation_marker: {facts['validation_marker']}",
        ]

    def _with_related(base: list[str]) -> list[str]:
        if related_files:
            return base + ["related_files:"] + [f"  - {f}" for f in related_files]
        return base

    if style in ("minimal", "clean-yaml-sparse", "frontmatter-sparse"):
        return _with_related(identity + answer) if style == "minimal-linked" else identity + answer

    if style == "minimal-linked":
        return _with_related(identity + answer)

    if style == "relational-lite":
        common = [
            "domain: deep-retail-ops",
            "system: metadata-ingestion",
            f"owner: {facts['owner']}",
            "record_status: active",
        ]
        return _with_related(identity + common + answer)

    if style == "clean-body":
        # No answer facts in frontmatter
        return identity + [
            "metadata_profile: clean-body-baseline",
            "tags:",
            "  - okf-canary",
            "  - concept-body",
        ]

    if style == "clean-yaml-okf":
        common = [
            "domain: deep-retail-ops",
            "metadata_profile: clean-okf-concept-yaml",
            f"owner: {facts['owner']}",
            "task_hint: deep canary investigation",
            "routing_hint: inspect non-index concept frontmatter",
        ]
        return identity + common + answer + ["tags:", "  - okf-canary", "  - deep-canary", "  - clean-okf"]

    if style == "canary":
        common = [
            "domain: deep-retail-ops",
            "metadata_profile: concept-frontmatter-canary",
            f"owner: {facts['owner']}",
            "task_hint: deep canary investigation",
            "routing_hint: answer-bearing values are in this non-index concept frontmatter",
        ]
        return identity + common + answer + ["tags:", "  - okf-canary", "  - deep-canary"]

    if style == "frontmatter-expanded":
        common = [
            "domain: deep-retail-ops",
            "metadata_profile: concept-frontmatter-expanded",
            f"owner: {facts['owner']}",
            "task_hint: deep canary investigation",
            "routing_hint: answer-bearing values are in this non-index concept frontmatter",
        ]
        return identity + common + answer + ["tags:", "  - okf-canary", "  - deep-canary", "  - expanded"]

    if style == "frontmatter-quoted":
        def q(v: str) -> str:
            return f'"{v}"'
        qidentity = [f'id: {q(base_id)}', f'type: {q(base_type)}', f'title: {q(base_title)}']
        if file_role == "root-cause":
            qanswer = [
                f'incident_id: {q(facts["incident_id"])}',
                f'affected_kpi: {q(facts["affected_kpi"])}',
                f'affected_days: {q(facts["affected_days"])}',
                f'root_cause: {q(facts["root_cause"])}',
                f'metadata_source: {q(facts["metadata_source"])}',
                f'incorrect_source: {q(facts["incorrect_source"])}',
                f'pipeline: {q(facts["pipeline"])}',
                f'source_asset: {q(facts["source_asset"])}',
            ]
        elif file_role == "remediation":
            qanswer = [
                f'incident_id: {q(facts["incident_id"])}',
                f'remediation: {q(facts["remediation"])}',
                f'owner: {q(facts["owner"])}',
            ]
        else:
            qanswer = [
                f'incident_id: {q(facts["incident_id"])}',
                f'signal_family: {q(facts["signal_family"])}',
                f'validation_marker: {q(facts["validation_marker"])}',
            ]
        return qidentity + qanswer + ["tags:", '  - "okf-canary"', '  - "deep-canary"']

    raise ValueError(f"unknown style: {style!r}")


def _concept_file(
    file_role: str,
    facts: dict[str, str],
    style: str,
    level: str,
    heading: str,
    related_files: list[str] | None = None,
) -> str:
    lines = _fm_lines(file_role, facts, style, level, related_files=related_files)
    if style == "clean-body":
        if file_role == "root-cause":
            body_facts = "\n".join([
                f"- incident_id: {facts['incident_id']}",
                f"- affected_kpi: {facts['affected_kpi']}",
                f"- affected_days: {facts['affected_days']}",
                f"- root_cause: {facts['root_cause']}",
                f"- metadata_source: {facts['metadata_source']}",
                f"- incorrect_source: {facts['incorrect_source']}",
                f"- pipeline: {facts['pipeline']}",
                f"- source_asset: {facts['source_asset']}",
            ])
        elif file_role == "remediation":
            body_facts = "\n".join([
                f"- remediation: {facts['remediation']}",
                f"- owner: {facts['owner']}",
            ])
        else:
            body_facts = "\n".join([
                f"- signal_family: {facts['signal_family']}",
                f"- validation_marker: {facts['validation_marker']}",
            ])
        body = f"# {heading}\n\n{body_facts}\n{_CONCEPT_BODY}"
    else:
        body = f"# {heading}\n{_CONCEPT_BODY}"
    return "---\n" + "\n".join(lines) + "\n---\n" + body


# ─── L2 builder ──────────────────────────────────────────────────────────────
#
# Layout under deep-retail-ops/canary-l2/:
#
#   index.md                                          (2 hops from deep-retail-ops)
#   incidents/index.md                                (3)
#   incidents/2026-12-prism/index.md                  (4)
#   incidents/2026-12-prism/root-cause.md             (5) ← FILE A
#   pipelines/index.md                                (3)
#   pipelines/commerce/index.md                       (4)
#   pipelines/commerce/checkout/index.md              (5)
#   pipelines/commerce/checkout/wallet/index.md       (6)
#   pipelines/commerce/checkout/wallet/canary-remediation.md  (7) ← FILE B
#   registry/index.md                                 (3)
#   registry/signal-registry.md                       (4) ← FILE C
#
# Total hops from bundle root index.md:
#   FILE A: root→deep→canary-l2→incidents→2026-12-prism→root-cause  = 5
#   FILE B: root→deep→canary-l2→pipelines→commerce→checkout→wallet→canary-remediation = 7
#   FILE C: root→deep→canary-l2→registry→signal-registry = 4

def _build_l2_canary(bundle: Path, style: str) -> None:
    root = bundle / "deep-retail-ops" / "canary-l2"
    facts = L2_FACTS
    level = "l2"
    task_hint = "prism metadata canary"

    # Related file paths for linked/relational styles (from each concept file location)
    rc_related = [  # from incidents/2026-12-prism/
        "../../pipelines/commerce/checkout/wallet/canary-remediation.md",
        "../../registry/signal-registry.md",
    ]
    rem_related = [  # from pipelines/commerce/checkout/wallet/
        "../../../../incidents/2026-12-prism/root-cause.md",
        "../../../../registry/signal-registry.md",
    ]
    sig_related = [  # from registry/
        "../incidents/2026-12-prism/root-cause.md",
        "../pipelines/commerce/checkout/wallet/canary-remediation.md",
    ]
    use_related = style in ("minimal-linked", "relational-lite")

    # Indexes
    _write(root / "index.md", _index(
        "Prism Canary L2", "canary-l2", 2, task_hint,
        "inspect the incident, pipeline wallet, and registry branches",
        [("Incidents", "incidents/index.md"),
         ("Pipelines", "pipelines/index.md"),
         ("Registry", "registry/index.md")],
        style,
    ))
    _write(root / "incidents" / "index.md", _index(
        "Canary L2 Incidents", "canary-l2-incidents", 3, task_hint,
        "inspect the prism incident",
        [("Prism canary", "2026-12-prism/index.md")],
        style,
    ))
    _write(root / "incidents" / "2026-12-prism" / "index.md", _index(
        "Prism Canary Incident", "canary-l2-incident", 4, task_hint,
        "inspect the root cause concept file",
        [("Root cause", "root-cause.md")],
        style,
    ))
    _write(root / "pipelines" / "index.md", _index(
        "Canary L2 Pipelines", "canary-l2-pipelines", 3, task_hint,
        "inspect the commerce checkout wallet pipeline",
        [("Commerce", "commerce/index.md")],
        style,
    ))
    _write(root / "pipelines" / "commerce" / "index.md", _index(
        "Canary L2 Commerce", "canary-l2-commerce", 4, task_hint,
        "inspect the checkout pipeline",
        [("Checkout", "checkout/index.md")],
        style,
    ))
    _write(root / "pipelines" / "commerce" / "checkout" / "index.md", _index(
        "Canary L2 Checkout", "canary-l2-checkout", 5, task_hint,
        "inspect the wallet pipeline",
        [("Wallet", "wallet/index.md")],
        style,
    ))
    _write(root / "pipelines" / "commerce" / "checkout" / "wallet" / "index.md", _index(
        "Canary L2 Wallet", "canary-l2-wallet", 6, task_hint,
        "inspect the canary remediation concept file",
        [("Canary remediation", "canary-remediation.md")],
        style,
    ))
    _write(root / "registry" / "index.md", _index(
        "Canary L2 Registry", "canary-l2-registry", 3, task_hint,
        "inspect the signal registry concept file",
        [("Signal registry", "signal-registry.md")],
        style,
    ))

    # Concept files
    _write(root / "incidents" / "2026-12-prism" / "root-cause.md", _concept_file(
        "root-cause", facts, style, level, "Root Cause Canary L2",
        related_files=rc_related if use_related else None,
    ))
    _write(root / "pipelines" / "commerce" / "checkout" / "wallet" / "canary-remediation.md", _concept_file(
        "remediation", facts, style, level, "Remediation Canary L2",
        related_files=rem_related if use_related else None,
    ))
    _write(root / "registry" / "signal-registry.md", _concept_file(
        "signal-registry", facts, style, level, "Signal Registry Canary L2",
        related_files=sig_related if use_related else None,
    ))

    # Wire into deep-retail-ops/index.md
    _append_once(
        bundle / "deep-retail-ops" / "index.md",
        "canary-l2/index.md",
        "- [Canary L2](canary-l2/index.md): multi-branch prism metadata canary.",
    )


# ─── L3 builder ──────────────────────────────────────────────────────────────
#
# Layout under deep-retail-ops/nexus-canary/:
#
# Branch A — incident (shallow inside nexus-canary):
#   incident/index.md                                 (3)
#   incident/2027-01-nexus/index.md                   (4)
#   incident/2027-01-nexus/root-cause.md              (5) ← FILE A
#
# Branch B — regions/experiments (very deep):
#   regions/index.md                                  (3)
#   regions/na/index.md                               (4)
#   regions/na/pacific/index.md                       (5)
#   regions/na/pacific/commerce/index.md              (6)
#   regions/na/pacific/commerce/checkout/index.md     (7)
#   regions/na/pacific/commerce/checkout/experiments/index.md (8)
#   regions/na/pacific/commerce/checkout/experiments/2027-q1/index.md (9)
#   regions/na/pacific/commerce/checkout/experiments/2027-q1/canary-remediation.md (10) ← FILE B
#
# Branch C — warehouse/schemas (medium-deep):
#   warehouse/index.md                                (3)
#   warehouse/schemas/index.md                        (4)
#   warehouse/schemas/settlement/index.md             (5)
#   warehouse/schemas/settlement/tables/index.md      (6)
#   warehouse/schemas/settlement/tables/canary-signal.md (7) ← FILE C
#
# Total hops from bundle root index.md:
#   FILE A: root→deep→nexus-canary→incident→2027-01-nexus→root-cause  = 5
#   FILE B: root→deep→nexus-canary→regions→na→pacific→commerce→checkout→experiments→2027-q1→canary-remediation = 10
#   FILE C: root→deep→nexus-canary→warehouse→schemas→settlement→tables→canary-signal = 7

def _build_l3_canary(bundle: Path, style: str) -> None:
    root = bundle / "deep-retail-ops" / "nexus-canary"
    facts = L3_FACTS
    level = "l3"
    task_hint = "nexus metadata canary"

    # Related file paths for linked/relational styles
    # FILE A at: nexus-canary/incident/2027-01-nexus/  → 3 dirs up to nexus-canary/
    rc_related = [
        "../../../regions/na/pacific/commerce/checkout/experiments/2027-q1/canary-remediation.md",
        "../../../warehouse/schemas/settlement/tables/canary-signal.md",
    ]
    # FILE B at: nexus-canary/regions/na/pacific/commerce/checkout/experiments/2027-q1/  → 7 dirs up
    rem_related = [
        "../../../../../../../incident/2027-01-nexus/root-cause.md",
        "../../../../../../../warehouse/schemas/settlement/tables/canary-signal.md",
    ]
    # FILE C at: nexus-canary/warehouse/schemas/settlement/tables/  → 4 dirs up
    sig_related = [
        "../../../../incident/2027-01-nexus/root-cause.md",
        "../../../../regions/na/pacific/commerce/checkout/experiments/2027-q1/canary-remediation.md",
    ]
    use_related = style in ("minimal-linked", "relational-lite")

    # Root index
    _write(root / "index.md", _index(
        "Nexus Canary L3", "nexus-canary-l3", 2, task_hint,
        "inspect the incident, regions, and warehouse branches",
        [("Incident", "incident/index.md"),
         ("Regions", "regions/index.md"),
         ("Warehouse", "warehouse/index.md")],
        style,
    ))

    # Branch A — incident
    _write(root / "incident" / "index.md", _index(
        "Nexus Canary Incident", "nexus-l3-incident", 3, task_hint,
        "inspect the 2027-01 nexus incident",
        [("2027-01 nexus", "2027-01-nexus/index.md")],
        style,
    ))
    _write(root / "incident" / "2027-01-nexus" / "index.md", _index(
        "2027-01 Nexus Incident", "nexus-l3-incident-detail", 4, task_hint,
        "inspect the root cause concept file",
        [("Root cause", "root-cause.md")],
        style,
    ))
    _write(root / "incident" / "2027-01-nexus" / "root-cause.md", _concept_file(
        "root-cause", facts, style, level, "Root Cause Canary L3",
        related_files=rc_related if use_related else None,
    ))

    # Branch B — regions (deep)
    _write(root / "regions" / "index.md", _index(
        "Nexus Canary Regions", "nexus-l3-regions", 3, task_hint,
        "inspect the NA pacific region",
        [("NA", "na/index.md")],
        style,
    ))
    _write(root / "regions" / "na" / "index.md", _index(
        "NA Region", "nexus-l3-na", 4, task_hint,
        "inspect pacific commerce checkout experiments",
        [("Pacific", "pacific/index.md")],
        style,
    ))
    _write(root / "regions" / "na" / "pacific" / "index.md", _index(
        "Pacific Region", "nexus-l3-pacific", 5, task_hint,
        "inspect commerce checkout experiments",
        [("Commerce", "commerce/index.md")],
        style,
    ))
    _write(root / "regions" / "na" / "pacific" / "commerce" / "index.md", _index(
        "Pacific Commerce", "nexus-l3-commerce", 6, task_hint,
        "inspect checkout experiments",
        [("Checkout", "checkout/index.md")],
        style,
    ))
    _write(root / "regions" / "na" / "pacific" / "commerce" / "checkout" / "index.md", _index(
        "Pacific Commerce Checkout", "nexus-l3-checkout", 7, task_hint,
        "inspect 2027 Q1 checkout experiments",
        [("Experiments", "experiments/index.md")],
        style,
    ))
    _write(root / "regions" / "na" / "pacific" / "commerce" / "checkout" / "experiments" / "index.md", _index(
        "Pacific Checkout Experiments", "nexus-l3-experiments", 8, task_hint,
        "inspect the 2027 Q1 experiments",
        [("2027 Q1", "2027-q1/index.md")],
        style,
    ))
    _write(root / "regions" / "na" / "pacific" / "commerce" / "checkout" / "experiments" / "2027-q1" / "index.md", _index(
        "2027 Q1 Pacific Experiments", "nexus-l3-2027-q1", 9, task_hint,
        "inspect the canary remediation concept file",
        [("Canary remediation", "canary-remediation.md")],
        style,
    ))
    _write(
        root / "regions" / "na" / "pacific" / "commerce" / "checkout" / "experiments" / "2027-q1" / "canary-remediation.md",
        _concept_file(
            "remediation", facts, style, level, "Remediation Canary L3",
            related_files=rem_related if use_related else None,
        ),
    )

    # Branch C — warehouse (medium-deep)
    _write(root / "warehouse" / "index.md", _index(
        "Nexus Canary Warehouse", "nexus-l3-warehouse", 3, task_hint,
        "inspect settlement schema tables",
        [("Schemas", "schemas/index.md")],
        style,
    ))
    _write(root / "warehouse" / "schemas" / "index.md", _index(
        "Warehouse Schemas", "nexus-l3-schemas", 4, task_hint,
        "inspect the settlement schema",
        [("Settlement", "settlement/index.md")],
        style,
    ))
    _write(root / "warehouse" / "schemas" / "settlement" / "index.md", _index(
        "Settlement Schema", "nexus-l3-settlement", 5, task_hint,
        "inspect settlement tables for the signal registry",
        [("Tables", "tables/index.md")],
        style,
    ))
    _write(root / "warehouse" / "schemas" / "settlement" / "tables" / "index.md", _index(
        "Settlement Tables", "nexus-l3-tables", 6, task_hint,
        "inspect the canary signal registry",
        [("Canary signal", "canary-signal.md")],
        style,
    ))
    _write(root / "warehouse" / "schemas" / "settlement" / "tables" / "canary-signal.md", _concept_file(
        "signal-registry", facts, style, level, "Signal Registry Canary L3",
        related_files=sig_related if use_related else None,
    ))

    # Wire into deep-retail-ops/index.md
    _append_once(
        bundle / "deep-retail-ops" / "index.md",
        "nexus-canary/index.md",
        "- [Nexus Canary L3](nexus-canary/index.md): deep cross-branch nexus metadata canary.",
    )


# ─── Task JSON files ──────────────────────────────────────────────────────────

def _write_task_files() -> None:
    tasks_dir = ROOT / "tasks"

    def _expected(facts: dict[str, str]) -> dict:
        result = {k: {"accepted": [v]} for k, v in facts.items()}
        # Accept open-ended date range as alternative
        result["affected_days"]["accepted"].append(
            facts["affected_days"].split(",")[0].strip()
            + " through "
            + facts["affected_days"].split(",")[-1].strip()
        )
        return result

    l2_prompt = (
        "Use the OKF bundle to investigate the prism metadata canary. "
        "Provide the incident id, affected KPI, affected days, root cause, "
        "metadata source, incorrect source, pipeline, source asset, remediation, "
        "owner, signal family, validation marker, and citations."
    )
    l3_prompt = (
        "Use the OKF bundle to investigate the nexus metadata canary. "
        "Provide the incident id, affected KPI, affected days, root cause, "
        "metadata source, incorrect source, pipeline, source asset, remediation, "
        "owner, signal family, validation marker, and citations."
    )

    l2_private = {
        "task_id": "deep-canary-l2-v1",
        "prompt": l2_prompt,
        "expected_facts": _expected(L2_FACTS),
        "required_citations": L2_REQUIRED_CITATIONS,
        "fact_evidence": {"scope": "required_citation_frontmatter"},
        "distractors": [
            "pacific gold loyalty",
            "atlantic mobile checkout",
            "escrow disbursement",
            "fraud step-up",
        ],
        "distractor_penalty": 0.25,
        "trace_expectations": {
            "target_duration_ms": 50000,
            "max_unique_files_read": 20,
            "relevant_paths": [
                "/index.md",
                "/deep-retail-ops/index.md",
                "/deep-retail-ops/canary-l2/index.md",
                "/deep-retail-ops/canary-l2/incidents/index.md",
                "/deep-retail-ops/canary-l2/incidents/2026-12-prism/index.md",
                "/deep-retail-ops/canary-l2/pipelines/index.md",
                "/deep-retail-ops/canary-l2/pipelines/commerce/index.md",
                "/deep-retail-ops/canary-l2/pipelines/commerce/checkout/index.md",
                "/deep-retail-ops/canary-l2/pipelines/commerce/checkout/wallet/index.md",
                "/deep-retail-ops/canary-l2/registry/index.md",
            ],
            "distractor_paths": [
                "/deep-retail-ops/incidents/2026-08-pacific-loyalty-drop/root-cause.md",
                "/deep-retail-ops/incidents/2026-08-pacific-fraud-friction/root-cause.md",
                "/enterprise-fnf/incidents/2026-09-florida-escrow-recon/root-cause.md",
                "/enterprise-fnf/frontmatter-canary/incidents/2026-11-md-frontmatter-canary/root-cause.md",
            ],
        },
    }

    l2_public = {
        "task_id": "deep-canary-l2-v1",
        "prompt": l2_prompt,
        "fact_keys": list(L2_FACTS.keys()),
    }

    l3_private = {
        "task_id": "deep-canary-l3-v1",
        "prompt": l3_prompt,
        "expected_facts": _expected(L3_FACTS),
        "required_citations": L3_REQUIRED_CITATIONS,
        "fact_evidence": {"scope": "required_citation_frontmatter"},
        "distractors": [
            "loyalty wallet accelerator",
            "fraud step-up",
            "escrow disbursement",
            "pacific fraud friction",
            "azimuth freight",
        ],
        "distractor_penalty": 0.25,
        "trace_expectations": {
            "target_duration_ms": 70000,
            "max_unique_files_read": 30,
            "relevant_paths": [
                "/index.md",
                "/deep-retail-ops/index.md",
                "/deep-retail-ops/nexus-canary/index.md",
                "/deep-retail-ops/nexus-canary/incident/index.md",
                "/deep-retail-ops/nexus-canary/incident/2027-01-nexus/index.md",
                "/deep-retail-ops/nexus-canary/regions/index.md",
                "/deep-retail-ops/nexus-canary/regions/na/index.md",
                "/deep-retail-ops/nexus-canary/regions/na/pacific/index.md",
                "/deep-retail-ops/nexus-canary/regions/na/pacific/commerce/index.md",
                "/deep-retail-ops/nexus-canary/regions/na/pacific/commerce/checkout/index.md",
                "/deep-retail-ops/nexus-canary/regions/na/pacific/commerce/checkout/experiments/index.md",
                "/deep-retail-ops/nexus-canary/regions/na/pacific/commerce/checkout/experiments/2027-q1/index.md",
                "/deep-retail-ops/nexus-canary/warehouse/index.md",
                "/deep-retail-ops/nexus-canary/warehouse/schemas/index.md",
                "/deep-retail-ops/nexus-canary/warehouse/schemas/settlement/index.md",
                "/deep-retail-ops/nexus-canary/warehouse/schemas/settlement/tables/index.md",
            ],
            "distractor_paths": [
                "/deep-retail-ops/regions/na/pacific/commerce/checkout/experiments/2026-q3/fraud-step-up/variant-b.md",
                "/deep-retail-ops/regions/na/pacific/commerce/checkout/experiments/2026-q3/loyalty-wallet-accelerator/variant-b.md",
                "/deep-retail-ops/canary-l2/incidents/2026-12-prism/root-cause.md",
                "/enterprise-fnf/frontmatter-canary/incidents/2026-11-md-frontmatter-canary/root-cause.md",
            ],
        },
    }

    l3_public = {
        "task_id": "deep-canary-l3-v1",
        "prompt": l3_prompt,
        "fact_keys": list(L3_FACTS.keys()),
    }

    (tasks_dir / "deep-canary-l2.json").write_text(json.dumps(l2_private, indent=2) + "\n")
    (tasks_dir / "deep-canary-l2.public.json").write_text(json.dumps(l2_public, indent=2) + "\n")
    (tasks_dir / "deep-canary-l3.json").write_text(json.dumps(l3_private, indent=2) + "\n")
    (tasks_dir / "deep-canary-l3.public.json").write_text(json.dumps(l3_public, indent=2) + "\n")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    built = 0
    for variant, style in VARIANTS.items():
        bundle = ROOT / "bundles" / f"{variant}-retail-ops"
        if not bundle.exists():
            print(f"  skip {variant} (bundle not found)")
            continue
        _build_l2_canary(bundle, style)
        _build_l3_canary(bundle, style)
        print(f"  ok   {variant} ({style})")
        built += 1

    _write_task_files()
    print(f"\nBuilt {built} bundles. Task files written to tasks/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
