#!/usr/bin/env python3
"""Generate hard-mode expansion for the enterprise-fnf benchmark.

Changes:
  1. ~30 new plausible distractor files in all bundle variants so the
     22-file retrieval budget is genuinely tight.
  2. A second task (California refi fee) that shares vocabulary with the FL
     escrow task but needs different files and different answers.
  3. Stricter accepted-answer lists in the existing FL task (removes loose
     paraphrases that reward partial retrieval).

Run from the repo root:
  python3 scripts/build_hard_mode.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLES = {
    "strict":   ROOT / "bundles" / "strict-retail-ops",
    "extended": ROOT / "bundles" / "extended-retail-ops",
    "uniform":  ROOT / "bundles" / "uniform-yaml-retail-ops",
    "frontloaded": ROOT / "bundles" / "frontloaded-yaml-retail-ops",
}
EFP = "enterprise-fnf"  # prefix inside each bundle


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def concept(path: Path, text: str) -> None:
    """Write a concept file identically to all three bundle variants."""
    for bundle in BUNDLES.values():
        write(bundle / EFP / path, text)


def index_strict(rel: Path, heading: str, items: list[tuple[str, str]]) -> None:
    body = "\n".join(f"- [{label}]({href})" for label, href in items)
    write(BUNDLES["strict"] / EFP / rel, f"# {heading}\n\n{body}\n")


def index_extended(
    rel: Path,
    heading: str,
    items: list[tuple[str, str]],
    *,
    domain: str,
    area: str,
    depth: int,
    task_hint: str = "",
    routing_hint: str = "",
    priority_hint: str = "",
) -> None:
    lines = [
        "---",
        "type: directory_index",
        f"domain: {domain}",
        f"area: {area}",
        f"depth: {depth}",
        "metadata_profile: progressive-enterprise",
    ]
    if task_hint:
        lines.append(f"task_hint: {task_hint}")
    if routing_hint:
        lines.append(f"routing_hint: {routing_hint}")
    if priority_hint:
        lines.append(f"priority_hint: {priority_hint}")
    lines.append("---")
    fm = "\n".join(lines) + "\n"
    body = "\n".join(f"- [{label}]({href})" for label, href in items)
    write(BUNDLES["extended"] / EFP / rel, f"{fm}# {heading}\n\n{body}\n")


def index_uniform(
    rel: Path,
    heading: str,
    items: list[tuple[str, str]],
    *,
    domain: str,
    area: str,
    depth: int,
    task_hint: str = "",
    routing_hint: str = "",
) -> None:
    lines = [
        "---",
        "type: directory_index",
        f"domain: {domain}",
        f"area: {area}",
        f"depth: {depth}",
        "metadata_profile: uniform-enterprise",
        "owner: enterprise-data-governance",
    ]
    if task_hint:
        lines.append(f"task_hint: {task_hint}")
    if routing_hint:
        lines.append(f"routing_hint: {routing_hint}")
    lines.append("---")
    fm = "\n".join(lines) + "\n"
    body = "\n".join(f"- [{label}]({href})" for label, href in items)
    write(BUNDLES["uniform"] / EFP / rel, f"{fm}# {heading}\n\n{body}\n")


def index_frontloaded(
    rel: Path,
    heading: str,
    items: list[tuple[str, str]],
    *,
    domain: str,
    area: str,
    depth: int,
    task_hint: str = "",
    routing_hint: str = "",
    priority_hint: str = "",
) -> None:
    lines = [
        "---",
        "type: directory_index",
        f"domain: {domain}",
        f"area: {area}",
        f"depth: {depth}",
        "metadata_profile: frontloaded-enterprise",
        "owner: knowledge-team",
    ]
    if depth <= 6 and task_hint:
        lines.append(f"task_hint: {task_hint}")
    if depth <= 4 and routing_hint:
        lines.append(f"routing_hint: {routing_hint}")
    if depth <= 2 and priority_hint:
        lines.append(f"priority_hint: {priority_hint}")
    lines.append("---")
    fm = "\n".join(lines) + "\n"
    body = "\n".join(f"- [{label}]({href})" for label, href in items)
    write(BUNDLES["frontloaded"] / EFP / rel, f"{fm}# {heading}\n\n{body}\n")


def index_all(
    rel: Path,
    heading: str,
    items: list[tuple[str, str]],
    *,
    domain: str,
    area: str,
    depth: int,
    task_hint: str = "",
    routing_hint: str = "",
    priority_hint: str = "",
) -> None:
    index_strict(rel, heading, items)
    index_extended(rel, heading, items, domain=domain, area=area, depth=depth,
                   task_hint=task_hint, routing_hint=routing_hint,
                   priority_hint=priority_hint)
    index_uniform(rel, heading, items, domain=domain, area=area, depth=depth,
                  task_hint=task_hint, routing_hint=routing_hint)
    index_frontloaded(rel, heading, items, domain=domain, area=area, depth=depth,
                      task_hint=task_hint, routing_hint=routing_hint,
                      priority_hint=priority_hint)


# ---------------------------------------------------------------------------
# 1. CONCEPT FILES — same across all three variants
# ---------------------------------------------------------------------------

# --- updated CA refi root cause (now carries structured facts) ---
concept(Path("incidents/2026-09-california-refi-fee/root-cause.md"), """\
---
id: fnf.incident.2026_09_california_refi_fee.root_cause
type: root_cause
title: California refinance fee root cause
incident_id: fnf-inc-2026-09-california-refi-fee
affected_kpi: settlement fee revenue variance
affected_segment: California refinance closings for FNF National Title
pipeline: settlement_fee_revenue_v2
bad_join_key: loan_number
correct_join_key: closing_id
impacted_asset: finance.settlement_fee_revenue_daily
tags:
  - enterprise-fnf
  - root-cause
  - california
  - revenue
---
# Root Cause

The September 10, 2026 California refinance fee understatement was caused by
`settlement_fee_revenue_v2` joining `closing_order_fact` using `loan_number`.

`loan_number` is not unique at closing grain. A refinance closing on the same
property can carry the same `loan_number` across multiple order rows, causing
a fan-out that suppressed fee aggregation in `finance.settlement_fee_revenue_daily`.
The correct join key is `closing_id`.

This incident is unrelated to the Florida purchase escrow disbursement
reconciliation overstatement of September 15.
""")

# --- new CA refi remediation ---
concept(Path("incidents/2026-09-california-refi-fee/remediation.md"), """\
---
id: fnf.incident.2026_09_california_refi_fee.remediation
type: remediation
title: California refinance fee remediation
incident_id: fnf-inc-2026-09-california-refi-fee
owner: settlement-data-engineering
tags:
  - enterprise-fnf
  - remediation
  - california
---
# Remediation

Switch `settlement_fee_revenue_v2` to join `closing_order_fact` on `closing_id`
instead of `loan_number`. Quarantine `loan_number` joins in fee revenue
workloads, and backfill `finance.settlement_fee_revenue_daily` for California
refinance closings under FNF National Title for the affected window.
""")

# --- new escrow hold mismatch incident (Aug 2026 distractor) ---
concept(Path("incidents/2026-08-escrow-hold-mismatch/root-cause.md"), """\
---
id: fnf.incident.2026_08_escrow_hold_mismatch.root_cause
type: root_cause
title: Escrow hold mismatch root cause
incident_id: fnf-inc-2026-08-escrow-hold-mismatch
affected_kpi: escrow hold balance variance
affected_segment: Florida purchase closings for Old Republic National Title
pipeline: escrow_balance_sync_v1
bad_join_key: escrow_account_id
correct_join_key: disbursement_hold_id
impacted_asset: finance.escrow_balance_daily
tags:
  - enterprise-fnf
  - root-cause
  - escrow
  - distractor
---
# Root Cause

The August 2026 escrow hold mismatch was caused by `escrow_balance_sync_v1`
joining `disbursement_hold_fact` using `escrow_account_id` instead of
`disbursement_hold_id`. `escrow_account_id` is shared across multiple holds
within an account, causing `finance.escrow_balance_daily` to overcount open
hold balances for Florida purchase closings under Old Republic National Title.

This incident affected the escrow hold balance KPI, not the escrow disbursement
reconciliation variance KPI. Old Republic National Title is not the underwriter
involved in the September 15 escrow disbursement incident.
""")

concept(Path("incidents/2026-08-escrow-hold-mismatch/remediation.md"), """\
---
id: fnf.incident.2026_08_escrow_hold_mismatch.remediation
type: remediation
title: Escrow hold mismatch remediation
incident_id: fnf-inc-2026-08-escrow-hold-mismatch
owner: escrow-data-engineering
tags:
  - enterprise-fnf
  - remediation
  - escrow
  - distractor
---
# Remediation

Switch `escrow_balance_sync_v1` to join on `disbursement_hold_id` and rebuild
`finance.escrow_balance_daily` for the affected window. Quarantine
`escrow_account_id` joins in hold-balance aggregations.
""")

# --- new party identity sync incident (Oct 2026 distractor) ---
concept(Path("incidents/2026-10-party-identity-sync/root-cause.md"), """\
---
id: fnf.incident.2026_10_party_identity_sync.root_cause
type: root_cause
title: Party identity sync root cause
incident_id: fnf-inc-2026-10-party-identity-sync
affected_kpi: party identity match rate
affected_segment: nationwide closings
pipeline: party_identity_sync_v2
bad_join_key: normalized_tax_id
correct_join_key: party_id
impacted_asset: party.party_identity_bridge
tags:
  - enterprise-fnf
  - root-cause
  - party
  - distractor
---
# Root Cause

The October 2026 party identity sync incident caused duplicate party rows in
`party.party_identity_bridge`. `party_identity_sync_v2` merged incoming party
records by `normalized_tax_id` instead of `party_id`, collapsing distinct legal
entities that shared a tax identifier (joint ventures, successor entities).

This incident corrupted the bridge table itself, distinct from the September 15
escrow disbursement incident where the pipeline joined an already-correct bridge
table using the wrong key.
""")

concept(Path("incidents/2026-10-party-identity-sync/remediation.md"), """\
---
id: fnf.incident.2026_10_party_identity_sync.remediation
type: remediation
title: Party identity sync remediation
incident_id: fnf-inc-2026-10-party-identity-sync
owner: identity-data-engineering
tags:
  - enterprise-fnf
  - remediation
  - party
  - distractor
---
# Remediation

Revert `party_identity_sync_v2` to merge on `party_id`. Rebuild
`party.party_identity_bridge` from the pre-merge snapshot and reprocess
downstream reconciliation workloads that consumed the corrupted bridge.
""")

# --- pipeline distractors ---
concept(Path("data-platform/pipelines/settlement/disbursement-recon/v1-transform.md"), """\
---
id: fnf.pipeline.settlement_disbursement_recon_v1
type: pipeline_transform
title: settlement_disbursement_recon_v1
owner: settlement-data-engineering
schedule: daily
target_asset: fnf.dw.finance.view.disbursement_recon_daily
deprecated: true
deprecated_reason: replaced by v2, then v3
tags:
  - enterprise-fnf
  - pipeline
  - deprecated
---
# settlement_disbursement_recon_v1

`settlement_disbursement_recon_v1` was the original daily build of
`finance.disbursement_recon_daily`. It joined `escrow_disbursement_fact` to
`party_identity_bridge` using `policy_number`, which caused a different class of
fan-out before this pipeline was deprecated.

This version is no longer in production and is not the pipeline involved in the
September 15, 2026 incident.
""")

concept(Path("data-platform/pipelines/settlement/disbursement-recon/v2-transform.md"), """\
---
id: fnf.pipeline.settlement_disbursement_recon_v2
type: pipeline_transform
title: settlement_disbursement_recon_v2
owner: settlement-data-engineering
schedule: hourly
target_asset: fnf.dw.finance.view.disbursement_recon_daily
deprecated: true
deprecated_reason: replaced by v3 on September 15 deploy
tags:
  - enterprise-fnf
  - pipeline
  - deprecated
---
# settlement_disbursement_recon_v2

`settlement_disbursement_recon_v2` correctly joined `escrow_disbursement_fact`
to `party_identity_bridge` using `closing_party_role_id`. It ran without
incident from February through September 14, 2026.

The September 15 deploy replaced it with `v3`, which introduced the
`normalized_tax_id` join bug. `v2` was not the root cause of the incident.
""")

concept(Path("data-platform/pipelines/settlement/fee-recon/v2-transform.md"), """\
---
id: fnf.pipeline.settlement_fee_revenue_v2
type: pipeline_transform
title: settlement_fee_revenue_v2
owner: settlement-data-engineering
schedule: daily
target_asset: fnf.dw.finance.view.settlement_fee_revenue_daily
bad_join_key: loan_number
correct_join_key: closing_id
tags:
  - enterprise-fnf
  - pipeline
  - california
  - root-cause
---
# settlement_fee_revenue_v2

`settlement_fee_revenue_v2` builds `finance.settlement_fee_revenue_daily` from
`settlement.closing_order_fact` and fee schedule tables.

The September 2026 deploy introduced a join on `loan_number` instead of
`closing_id`. Because `loan_number` is not unique at closing grain — a
refinance on the same property can carry the same loan number across multiple
order rows — fee revenue rows were de-duplicated incorrectly, understating
California refinance fee revenue for FNF National Title.

The correct join key is `closing_id`.
""")

concept(Path("data-platform/pipelines/party/party-identity-sync.md"), """\
---
id: fnf.pipeline.party_identity_sync_v2
type: pipeline_transform
title: party_identity_sync_v2
owner: identity-data-engineering
schedule: daily
target_asset: fnf.dw.party.table.party_identity_bridge
tags:
  - enterprise-fnf
  - pipeline
  - party
  - distractor
---
# party_identity_sync_v2

`party_identity_sync_v2` ingests party identity records from upstream source
systems and merges them into `party.party_identity_bridge` using `party_id` as
the deduplication key.

This pipeline does not build the finance reconciliation views. It was involved
in the October 2026 party identity incident, not the September 15 escrow
disbursement reconciliation incident.
""")

concept(Path("data-platform/pipelines/escrow/escrow-balance-sync.md"), """\
---
id: fnf.pipeline.escrow_balance_sync_v1
type: pipeline_transform
title: escrow_balance_sync_v1
owner: escrow-data-engineering
schedule: hourly
target_asset: fnf.dw.finance.view.escrow_balance_daily
tags:
  - enterprise-fnf
  - pipeline
  - escrow
  - distractor
---
# escrow_balance_sync_v1

`escrow_balance_sync_v1` builds `finance.escrow_balance_daily` from
`settlement.disbursement_hold_fact`. It was involved in the August 2026 escrow
hold mismatch incident.

This pipeline does not build `finance.disbursement_recon_daily` and is not
related to the September 15 disbursement reconciliation incident.
""")

# --- party table distractors ---
concept(Path("data-platform/warehouses/enterprise-dw/schemas/party/tables/closing-agent-lookup.md"), """\
---
id: fnf.dw.party.table.closing_agent_lookup
type: warehouse_table
title: party.closing_agent_lookup
owner: identity-data-products
warehouse: enterprise_dw
schema: party
object_name: closing_agent_lookup
grain: agent_license_id
primary_key: agent_license_id
alternate_keys:
  - agent_tax_id
  - party_id
tags:
  - enterprise-fnf
  - party
  - agent
  - distractor
---
# party.closing_agent_lookup

Closing agent lookup maps licensed title agents to closings. The table grain
is `agent_license_id`.

`agent_tax_id` is an alternate identifier for the agent entity, distinct from
the `normalized_tax_id` used in `party_identity_bridge` for closing party roles.
This table was not involved in the September 15 escrow disbursement
reconciliation incident.
""")

concept(Path("data-platform/warehouses/enterprise-dw/schemas/party/tables/entity-tax-registry.md"), """\
---
id: fnf.dw.party.table.entity_tax_registry
type: warehouse_table
title: party.entity_tax_registry
owner: identity-data-products
warehouse: enterprise_dw
schema: party
object_name: entity_tax_registry
grain: tax_entity_id
primary_key: tax_entity_id
alternate_keys:
  - normalized_tax_id
  - ein
tags:
  - enterprise-fnf
  - party
  - tax
  - distractor
---
# party.entity_tax_registry

Entity tax registry maps corporate and trust entities to their tax identifiers
for remittance and reporting purposes.

`normalized_tax_id` here refers to corporate entities only. It is not the same
usage as the `normalized_tax_id` column in `party_identity_bridge`, which maps
individual closing party roles. This table was not involved in the September 15
escrow disbursement reconciliation incident.
""")

# --- finance view distractors ---
concept(Path("data-platform/warehouses/enterprise-dw/schemas/finance/views/escrow-balance-daily.md"), """\
---
id: fnf.dw.finance.view.escrow_balance_daily
type: warehouse_view
title: finance.escrow_balance_daily
owner: finance-data-products
warehouse: enterprise_dw
schema: finance
object_name: escrow_balance_daily
grain: business_date, escrow_account_id
primary_kpi: escrow hold balance variance
upstream:
  - fnf.dw.settlement.table.disbursement_hold_fact
tags:
  - enterprise-fnf
  - finance
  - escrow
  - distractor
---
# finance.escrow_balance_daily

`finance.escrow_balance_daily` is the KPI view for escrow hold balance
variance. It tracks open disbursement holds by escrow account.

This view was impacted by the August 2026 escrow hold mismatch incident
involving `escrow_balance_sync_v1`. It is not the impacted view for the
September 15 escrow disbursement reconciliation incident, which affected
`finance.disbursement_recon_daily`.
""")

concept(Path("data-platform/warehouses/enterprise-dw/schemas/finance/views/disbursement-summary-weekly.md"), """\
---
id: fnf.dw.finance.view.disbursement_summary_weekly
type: warehouse_view
title: finance.disbursement_summary_weekly
owner: finance-data-products
warehouse: enterprise_dw
schema: finance
object_name: disbursement_summary_weekly
grain: week_ending_date, state_code, underwriter_code
primary_kpi: weekly disbursement volume
upstream:
  - fnf.dw.finance.view.disbursement_recon_daily
tags:
  - enterprise-fnf
  - finance
  - reconciliation
  - distractor
---
# finance.disbursement_summary_weekly

`finance.disbursement_summary_weekly` is an aggregated weekly rollup of
disbursement reconciliation data sourced from `disbursement_recon_daily`.

Because it is downstream of `disbursement_recon_daily`, it also showed inflated
figures after the September 15 incident. However, it is not the root-cause
impacted asset. Fixing `disbursement_recon_daily` will cascade to correct this
view automatically.
""")

concept(Path("data-platform/warehouses/enterprise-dw/schemas/finance/views/underwriter-remittance-variance-daily.md"), """\
---
id: fnf.dw.finance.view.underwriter_remittance_variance_daily
type: warehouse_view
title: finance.underwriter_remittance_variance_daily
owner: finance-data-products
warehouse: enterprise_dw
schema: finance
object_name: underwriter_remittance_variance_daily
grain: business_date, underwriter_code
primary_kpi: underwriter remittance variance
upstream:
  - fnf.dw.finance.table.underwriter_remittance_fact
tags:
  - enterprise-fnf
  - finance
  - remittance
  - distractor
---
# finance.underwriter_remittance_variance_daily

`finance.underwriter_remittance_variance_daily` tracks daily premium and fee
remittance variance by underwriter. It is sourced from
`underwriter_remittance_fact`, not from `escrow_disbursement_fact`.

This view was not affected by the September 15 escrow disbursement
reconciliation incident.
""")

# --- updated settlement-fee-revenue-daily (remove distractor-only framing) ---
concept(Path("data-platform/warehouses/enterprise-dw/schemas/finance/views/settlement-fee-revenue-daily.md"), """\
---
id: fnf.dw.finance.view.settlement_fee_revenue_daily
type: warehouse_view
title: finance.settlement_fee_revenue_daily
owner: finance-data-products
warehouse: enterprise_dw
schema: finance
object_name: settlement_fee_revenue_daily
grain: business_date, state_code, underwriter_code, closing_type
primary_kpi: settlement fee revenue variance
upstream:
  - fnf.dw.settlement.table.closing_order_fact
pii_classification: internal-confidential
sla: T+1 07:00 ET
tags:
  - enterprise-fnf
  - finance
  - revenue
---
# finance.settlement_fee_revenue_daily

`finance.settlement_fee_revenue_daily` is the KPI view for settlement fee
revenue variance. It aggregates title and closing fees from
`settlement.closing_order_fact` by business date, state, underwriter, and
closing type.

Joins to `closing_order_fact` must use `closing_id`. `loan_number` must not be
used as a join key because a refinance transaction on the same property can
carry the same loan number across multiple closing order rows.

This view was affected by the September 10, 2026 California refinance fee
understatement incident. It is not the impacted view for the September 15
escrow disbursement reconciliation incident, which affected
`finance.disbursement_recon_daily`.
""")

# --- updated closing-order-fact (add loan_number guidance) ---
concept(Path("data-platform/warehouses/enterprise-dw/schemas/settlement/tables/closing-order-fact.md"), """\
---
id: fnf.dw.settlement.table.closing_order_fact
type: warehouse_table
title: settlement.closing_order_fact
owner: settlement-data-products
warehouse: enterprise_dw
schema: settlement
object_name: closing_order_fact
grain: closing_id
primary_key: closing_id
alternate_keys:
  - loan_number
  - order_number
tags:
  - enterprise-fnf
  - settlement
  - closing
---
# settlement.closing_order_fact

Closing order fact tracks order-level settlement milestones. The table grain
is `closing_id`.

`loan_number` is an alternate attribute, not the grain. A refinance closing on
the same property can carry the same `loan_number` across multiple closing order
rows, making `loan_number` non-unique at closing grain. It must not be used to
join or aggregate closing fees.

This table is the primary upstream of `finance.settlement_fee_revenue_daily`
and was involved in the September 10, 2026 California refinance fee incident.
It is not the duplicated asset in the September 15 escrow disbursement
reconciliation incident.
""")

# --- settlement table distractors ---
concept(Path("data-platform/warehouses/enterprise-dw/schemas/settlement/tables/disbursement-hold-fact.md"), """\
---
id: fnf.dw.settlement.table.disbursement_hold_fact
type: warehouse_table
title: settlement.disbursement_hold_fact
owner: settlement-data-products
warehouse: enterprise_dw
schema: settlement
object_name: disbursement_hold_fact
grain: disbursement_hold_id
primary_key: disbursement_hold_id
foreign_keys:
  - escrow_account_id
  - closing_id
tags:
  - enterprise-fnf
  - escrow
  - settlement
  - distractor
---
# settlement.disbursement_hold_fact

Disbursement hold fact stores escrow hold events prior to disbursement release.
Each row represents a hold placed on an escrow account for a specific closing.

This table was involved in the August 2026 escrow hold mismatch incident
(where `escrow_account_id` was used incorrectly) but is not involved in the
September 15 escrow disbursement reconciliation incident.
""")

concept(Path("data-platform/warehouses/enterprise-dw/schemas/settlement/tables/wire-transfer-fact.md"), """\
---
id: fnf.dw.settlement.table.wire_transfer_fact
type: warehouse_table
title: settlement.wire_transfer_fact
owner: settlement-data-products
warehouse: enterprise_dw
schema: settlement
object_name: wire_transfer_fact
grain: wire_transfer_id
primary_key: wire_transfer_id
foreign_keys:
  - closing_id
  - escrow_account_id
  - closing_party_role_id
tags:
  - enterprise-fnf
  - settlement
  - wire
  - distractor
---
# settlement.wire_transfer_fact

Wire transfer fact stores outbound settlement wire events. Each wire is
associated with a `closing_id` and `closing_party_role_id` for the receiving
party.

Wire transfer data did not feed `finance.disbursement_recon_daily` in the
September 15 incident. That view sourced from `settlement.escrow_disbursement_fact`.
""")

concept(Path("data-platform/warehouses/enterprise-dw/schemas/settlement/tables/escrow-clearing-fact.md"), """\
---
id: fnf.dw.settlement.table.escrow_clearing_fact
type: warehouse_table
title: settlement.escrow_clearing_fact
owner: settlement-data-products
warehouse: enterprise_dw
schema: settlement
object_name: escrow_clearing_fact
grain: clearing_event_id
primary_key: clearing_event_id
foreign_keys:
  - escrow_disbursement_id
  - closing_id
  - closing_party_role_id
tags:
  - enterprise-fnf
  - escrow
  - settlement
  - distractor
---
# settlement.escrow_clearing_fact

Escrow clearing fact records ledger clearing events confirming disbursement
settlement. It is a downstream confirmation table, not a source of
disbursement rows.

`finance.disbursement_recon_daily` compares `escrow_disbursement_fact` against
clearing totals. The September 15 incident was caused by incorrect party-role
joining in the recon pipeline, not by data errors in this clearing table.
""")

# --- business segment distractors ---
concept(Path("business/title/regions/florida/underwriters/fnf-national-title/refinance-closings.md"), """\
---
id: fnf.business.title.florida.fnf_national_title.refinance_closings
type: business_segment
title: Florida refinance closings for FNF National Title
owner: title-operations-analytics
region: florida
underwriter: FNF National Title
closing_type: refinance
critical_kpis:
  - escrow disbursement reconciliation variance
  - underwriter remittance accuracy
tags:
  - enterprise-fnf
  - business-segment
  - title
  - distractor
---
# Florida Refinance Closings For FNF National Title

This segment covers Florida refinance closings under FNF National Title.

The September 15, 2026 escrow disbursement reconciliation incident affected
Florida **purchase** closings, not refinance closings. The data for refinance
closings in this segment was not duplicated by the `normalized_tax_id` join bug.
""")

concept(Path("business/title/regions/florida/underwriters/old-republic-national-title/purchase-closings.md"), """\
---
id: fnf.business.title.florida.old_republic_national_title.purchase_closings
type: business_segment
title: Florida purchase closings for Old Republic National Title
owner: title-operations-analytics
region: florida
underwriter: Old Republic National Title
closing_type: purchase
critical_kpis:
  - escrow disbursement reconciliation variance
tags:
  - enterprise-fnf
  - business-segment
  - title
  - distractor
---
# Florida Purchase Closings For Old Republic National Title

This segment covers Florida purchase closings under the Old Republic National
Title underwriter.

Old Republic National Title was not the underwriter affected by the September
15, 2026 escrow disbursement reconciliation incident. The affected underwriter
was FNF National Title.
""")

concept(Path("business/title/regions/georgia/underwriters/fnf-national-title/purchase-closings.md"), """\
---
id: fnf.business.title.georgia.fnf_national_title.purchase_closings
type: business_segment
title: Georgia purchase closings for FNF National Title
owner: title-operations-analytics
region: georgia
underwriter: FNF National Title
closing_type: purchase
critical_kpis:
  - escrow disbursement reconciliation variance
tags:
  - enterprise-fnf
  - business-segment
  - title
  - distractor
---
# Georgia Purchase Closings For FNF National Title

Georgia purchase closings under FNF National Title did not show anomalous
escrow disbursement reconciliation variance in September 2026. The incident
was scoped to Florida purchase closings.
""")

concept(Path("business/title/regions/texas/underwriters/fnf-national-title/purchase-closings.md"), """\
---
id: fnf.business.title.texas.fnf_national_title.purchase_closings
type: business_segment
title: Texas purchase closings for FNF National Title
owner: title-operations-analytics
region: texas
underwriter: FNF National Title
closing_type: purchase
critical_kpis:
  - escrow disbursement reconciliation variance
tags:
  - enterprise-fnf
  - business-segment
  - title
  - distractor
---
# Texas Purchase Closings For FNF National Title

Texas purchase closings under FNF National Title were not affected by the
September 15, 2026 escrow disbursement reconciliation incident. The incident
was scoped to Florida.
""")

concept(Path("business/title/regions/california/underwriters/fnf-national-title/refinance-closings.md"), """\
---
id: fnf.business.title.california.fnf_national_title.refinance_closings
type: business_segment
title: California refinance closings for FNF National Title
owner: title-operations-analytics
region: california
underwriter: FNF National Title
closing_type: refinance
critical_kpis:
  - settlement fee revenue variance
tags:
  - enterprise-fnf
  - business-segment
  - california
  - revenue
---
# California Refinance Closings For FNF National Title

California refinance closings under FNF National Title are measured by
settlement fee revenue variance.

This segment was affected by the September 10, 2026 California refinance fee
understatement incident. `settlement_fee_revenue_v2` joined `closing_order_fact`
using `loan_number` instead of `closing_id`, suppressing fee revenue for this
segment.

These closings were not part of the September 15 Florida escrow disbursement
reconciliation incident.
""")


# ---------------------------------------------------------------------------
# 2. INDEX FILES — differ by variant
# ---------------------------------------------------------------------------

HINT_FL = "florida fnf national title escrow disbursement reconciliation"
HINT_BOTH = "florida fnf national title escrow disbursement reconciliation california refinance fee revenue"
ROUTING = "inspect warehouse schemas, pipelines, business segments, and incident notes"

# incidents/index.md
index_all(
    Path("incidents/index.md"),
    "Enterprise Incidents",
    [
        ("Florida escrow reconciliation", "2026-09-florida-escrow-recon/index.md"),
        ("California refinance fee", "2026-09-california-refi-fee/index.md"),
        ("Escrow hold mismatch", "2026-08-escrow-hold-mismatch/index.md"),
        ("Party identity sync", "2026-10-party-identity-sync/index.md"),
    ],
    domain="incidents", area="incidents", depth=1,
    task_hint=HINT_BOTH, routing_hint=ROUTING,
)

# incidents/2026-09-california-refi-fee/index.md (update to add remediation)
index_all(
    Path("incidents/2026-09-california-refi-fee/index.md"),
    "California Refinance Fee",
    [
        ("Root cause", "root-cause.md"),
        ("Remediation", "remediation.md"),
    ],
    domain="incidents", area="california-refi-fee", depth=2,
    task_hint="california fnf national title refinance fee revenue settlement",
)

# incidents/2026-08-escrow-hold-mismatch/index.md
index_all(
    Path("incidents/2026-08-escrow-hold-mismatch/index.md"),
    "Escrow Hold Mismatch",
    [
        ("Root cause", "root-cause.md"),
        ("Remediation", "remediation.md"),
    ],
    domain="incidents", area="escrow-hold-mismatch", depth=2,
)

# incidents/2026-10-party-identity-sync/index.md
index_all(
    Path("incidents/2026-10-party-identity-sync/index.md"),
    "Party Identity Sync",
    [
        ("Root cause", "root-cause.md"),
        ("Remediation", "remediation.md"),
    ],
    domain="incidents", area="party-identity-sync", depth=2,
)

# pipelines/index.md (add party, escrow)
index_all(
    Path("data-platform/pipelines/index.md"),
    "Pipelines",
    [
        ("Settlement", "settlement/index.md"),
        ("Tax", "tax/index.md"),
        ("Party", "party/index.md"),
        ("Escrow", "escrow/index.md"),
    ],
    domain="data-platform", area="pipelines", depth=2,
    task_hint=HINT_BOTH, routing_hint=ROUTING,
)

# pipelines/settlement/index.md (add fee-recon)
index_all(
    Path("data-platform/pipelines/settlement/index.md"),
    "Settlement Pipelines",
    [
        ("Disbursement recon", "disbursement-recon/index.md"),
        ("Fee recon", "fee-recon/index.md"),
    ],
    domain="data-platform", area="settlement", depth=3,
    task_hint=HINT_BOTH, routing_hint=ROUTING,
    priority_hint="likely decisive enterprise schema path",
)

# pipelines/settlement/disbursement-recon/index.md (add v1, v2)
index_all(
    Path("data-platform/pipelines/settlement/disbursement-recon/index.md"),
    "Disbursement Recon Pipeline",
    [
        ("V1 transform (deprecated)", "v1-transform.md"),
        ("V2 transform (deprecated)", "v2-transform.md"),
        ("V3 transform", "v3-transform.md"),
    ],
    domain="data-platform", area="disbursement-recon", depth=4,
    task_hint=HINT_FL,
    priority_hint="likely decisive enterprise schema path",
)

# pipelines/settlement/fee-recon/index.md (new)
index_all(
    Path("data-platform/pipelines/settlement/fee-recon/index.md"),
    "Fee Recon Pipeline",
    [
        ("V2 transform", "v2-transform.md"),
    ],
    domain="data-platform", area="fee-recon", depth=4,
    task_hint="california fnf national title refinance fee revenue settlement",
)

# pipelines/party/index.md (new)
index_all(
    Path("data-platform/pipelines/party/index.md"),
    "Party Pipelines",
    [
        ("Party identity sync", "party-identity-sync.md"),
    ],
    domain="data-platform", area="party", depth=3,
)

# pipelines/escrow/index.md (new)
index_all(
    Path("data-platform/pipelines/escrow/index.md"),
    "Escrow Pipelines",
    [
        ("Escrow balance sync", "escrow-balance-sync.md"),
    ],
    domain="data-platform", area="escrow", depth=3,
)

# schemas/party/tables/index.md (add new tables)
index_all(
    Path("data-platform/warehouses/enterprise-dw/schemas/party/tables/index.md"),
    "Party Tables",
    [
        ("Party identity bridge", "party-identity-bridge.md"),
        ("Closing agent lookup", "closing-agent-lookup.md"),
        ("Entity tax registry", "entity-tax-registry.md"),
    ],
    domain="data-platform", area="tables", depth=7,
    task_hint=HINT_FL,
    routing_hint="inspect finance view, settlement table, party bridge, pipeline, business segment, and incident",
    priority_hint="likely decisive enterprise schema path",
)

# schemas/finance/views/index.md (add new views)
index_all(
    Path("data-platform/warehouses/enterprise-dw/schemas/finance/views/index.md"),
    "Finance Views",
    [
        ("Disbursement recon daily", "disbursement-recon-daily.md"),
        ("Settlement fee revenue daily", "settlement-fee-revenue-daily.md"),
        ("Escrow balance daily", "escrow-balance-daily.md"),
        ("Disbursement summary weekly", "disbursement-summary-weekly.md"),
        ("Underwriter remittance variance daily", "underwriter-remittance-variance-daily.md"),
    ],
    domain="data-platform", area="views", depth=7,
    task_hint=HINT_BOTH,
    routing_hint="inspect finance view, settlement table, party bridge, pipeline, business segment, and incident",
    priority_hint="likely decisive enterprise schema path",
)

# schemas/settlement/tables/index.md (add new tables)
index_all(
    Path("data-platform/warehouses/enterprise-dw/schemas/settlement/tables/index.md"),
    "Settlement Tables",
    [
        ("Escrow disbursement fact", "escrow-disbursement-fact.md"),
        ("Closing order fact", "closing-order-fact.md"),
        ("Disbursement hold fact", "disbursement-hold-fact.md"),
        ("Wire transfer fact", "wire-transfer-fact.md"),
        ("Escrow clearing fact", "escrow-clearing-fact.md"),
    ],
    domain="data-platform", area="tables", depth=6,
    task_hint=HINT_BOTH,
    routing_hint="inspect finance view, settlement table, party bridge, pipeline, business segment, and incident",
    priority_hint="likely decisive enterprise schema path",
)

# business/title/regions/index.md (add GA, TX)
index_all(
    Path("business/title/regions/index.md"),
    "Title Regions",
    [
        ("Florida", "florida/index.md"),
        ("California", "california/index.md"),
        ("Georgia", "georgia/index.md"),
        ("Texas", "texas/index.md"),
    ],
    domain="business", area="regions", depth=3,
    task_hint=HINT_FL,
)

# florida/underwriters/index.md (add Old Republic)
index_all(
    Path("business/title/regions/florida/underwriters/index.md"),
    "Florida Underwriters",
    [
        ("FNF National Title", "fnf-national-title/index.md"),
        ("Old Republic National Title", "old-republic-national-title/index.md"),
    ],
    domain="business", area="underwriters", depth=5,
    task_hint=HINT_FL,
)

# florida/underwriters/fnf-national-title/index.md (add refinance-closings)
index_all(
    Path("business/title/regions/florida/underwriters/fnf-national-title/index.md"),
    "FNF National Title Florida",
    [
        ("Purchase closings", "purchase-closings.md"),
        ("Refinance closings", "refinance-closings.md"),
    ],
    domain="business", area="fnf-national-title", depth=6,
    task_hint=HINT_FL,
    priority_hint="likely decisive enterprise schema path",
)

# florida/underwriters/old-republic-national-title/index.md (new)
index_all(
    Path("business/title/regions/florida/underwriters/old-republic-national-title/index.md"),
    "Old Republic National Title Florida",
    [
        ("Purchase closings", "purchase-closings.md"),
    ],
    domain="business", area="old-republic-national-title", depth=6,
)

# georgia indexes (new)
index_all(
    Path("business/title/regions/georgia/index.md"),
    "Georgia Title Region",
    [("Underwriters", "underwriters/index.md")],
    domain="business", area="georgia", depth=4,
)
index_all(
    Path("business/title/regions/georgia/underwriters/index.md"),
    "Georgia Underwriters",
    [("FNF National Title", "fnf-national-title/index.md")],
    domain="business", area="underwriters", depth=5,
)
index_all(
    Path("business/title/regions/georgia/underwriters/fnf-national-title/index.md"),
    "FNF National Title Georgia",
    [("Purchase closings", "purchase-closings.md")],
    domain="business", area="fnf-national-title", depth=6,
)

# texas indexes (new)
index_all(
    Path("business/title/regions/texas/index.md"),
    "Texas Title Region",
    [("Underwriters", "underwriters/index.md")],
    domain="business", area="texas", depth=4,
)
index_all(
    Path("business/title/regions/texas/underwriters/index.md"),
    "Texas Underwriters",
    [("FNF National Title", "fnf-national-title/index.md")],
    domain="business", area="underwriters", depth=5,
)
index_all(
    Path("business/title/regions/texas/underwriters/fnf-national-title/index.md"),
    "FNF National Title Texas",
    [("Purchase closings", "purchase-closings.md")],
    domain="business", area="fnf-national-title", depth=6,
)


# ---------------------------------------------------------------------------
# 3. TASK FILES
# ---------------------------------------------------------------------------

# 3a. New CA refi task
ca_task = {
    "task_id": "california-refi-fee-v1",
    "prompt": (
        "Use the OKF bundle to investigate the synthetic Fidelity National Financial enterprise schema incident "
        "for September 10, 2026. Explain why California refinance settlement fee revenue was understated for "
        "FNF National Title closings. Provide the affected KPI, affected business segment, root cause, bad join key, "
        "correct join key, impacted view, pipeline, remediation, and citations."
    ),
    "expected_facts": {
        "affected_kpi": {
            "accepted": [
                "settlement fee revenue variance",
                "settlement_fee_revenue_variance",
            ]
        },
        "affected_segment": {
            "accepted": [
                "california refinance closings for fnf national title",
                "california refinance closings under fnf national title",
                "fnf national title california refinance closings",
            ]
        },
        "root_cause": {
            "accepted": [
                "settlement_fee_revenue_v2 joined closing_order_fact by loan_number",
                "fee revenue transform joined closing_order_fact using loan_number instead of closing_id",
                "loan_number is not unique at closing grain causing fee row fan-out",
            ]
        },
        "bad_join_key": {
            "accepted": [
                "loan_number instead of closing_id",
                "loan_number not closing_id",
            ]
        },
        "correct_join_key": {
            "accepted": [
                "closing_id",
                "closing id",
            ]
        },
        "impacted_asset": {
            "accepted": [
                "finance.settlement_fee_revenue_daily",
                "settlement_fee_revenue_daily",
            ]
        },
        "pipeline": {
            "accepted": [
                "settlement_fee_revenue_v2",
                "settlement fee revenue v2",
            ]
        },
        "remediation": {
            "accepted": [
                "rebuild finance.settlement_fee_revenue_daily using closing_id and backfill california refinance closings",
                "switch settlement_fee_revenue_v2 to closing_id, quarantine loan_number joins, and backfill california refinance closings",
                "switch the transform to closing_id and backfill california refinance closings for fnf national title",
            ]
        },
    },
    "required_citations": [
        "/enterprise-fnf/data-platform/warehouses/enterprise-dw/schemas/finance/views/settlement-fee-revenue-daily.md",
        "/enterprise-fnf/data-platform/warehouses/enterprise-dw/schemas/settlement/tables/closing-order-fact.md",
        "/enterprise-fnf/data-platform/pipelines/settlement/fee-recon/v2-transform.md",
        "/enterprise-fnf/business/title/regions/california/underwriters/fnf-national-title/refinance-closings.md",
        "/enterprise-fnf/incidents/2026-09-california-refi-fee/root-cause.md",
        "/enterprise-fnf/incidents/2026-09-california-refi-fee/remediation.md",
    ],
    "distractors": [
        "florida purchase closings",
        "escrow disbursement reconciliation variance",
        "disbursement_recon_daily",
        "normalized_tax_id instead of loan_number",
        "closing_party_role_id instead of closing_id",
        "settlement_disbursement_recon_v3",
        "party_identity_bridge",
    ],
    "distractor_penalty": 0.25,
    "trace_expectations": {
        "target_duration_ms": 300000,
        "max_unique_files_read": 22,
        "relevant_paths": [
            "/index.md",
            "/enterprise-fnf/index.md",
            "/enterprise-fnf/data-platform/index.md",
            "/enterprise-fnf/data-platform/warehouses/index.md",
            "/enterprise-fnf/data-platform/warehouses/enterprise-dw/index.md",
            "/enterprise-fnf/data-platform/warehouses/enterprise-dw/schemas/index.md",
            "/enterprise-fnf/data-platform/warehouses/enterprise-dw/schemas/finance/index.md",
            "/enterprise-fnf/data-platform/warehouses/enterprise-dw/schemas/finance/views/index.md",
            "/enterprise-fnf/data-platform/warehouses/enterprise-dw/schemas/settlement/index.md",
            "/enterprise-fnf/data-platform/warehouses/enterprise-dw/schemas/settlement/tables/index.md",
            "/enterprise-fnf/data-platform/pipelines/index.md",
            "/enterprise-fnf/data-platform/pipelines/settlement/index.md",
            "/enterprise-fnf/data-platform/pipelines/settlement/fee-recon/index.md",
            "/enterprise-fnf/business/index.md",
            "/enterprise-fnf/business/title/index.md",
            "/enterprise-fnf/business/title/regions/index.md",
            "/enterprise-fnf/business/title/regions/california/index.md",
            "/enterprise-fnf/business/title/regions/california/underwriters/index.md",
            "/enterprise-fnf/business/title/regions/california/underwriters/fnf-national-title/index.md",
            "/enterprise-fnf/incidents/index.md",
            "/enterprise-fnf/incidents/2026-09-california-refi-fee/index.md",
        ],
        "distractor_paths": [
            "/enterprise-fnf/business/title/regions/florida/underwriters/fnf-national-title/purchase-closings.md",
            "/enterprise-fnf/data-platform/warehouses/enterprise-dw/schemas/finance/views/disbursement-recon-daily.md",
            "/enterprise-fnf/data-platform/warehouses/enterprise-dw/schemas/party/tables/party-identity-bridge.md",
            "/enterprise-fnf/data-platform/pipelines/settlement/disbursement-recon/v3-transform.md",
            "/enterprise-fnf/incidents/2026-09-florida-escrow-recon/root-cause.md",
        ],
    },
}
task_path = ROOT / "tasks" / "california-refi-fee-synthesis.json"
task_path.write_text(json.dumps(ca_task, indent=2) + "\n", encoding="utf-8")
print(f"wrote {task_path}")

# 3b. Update FL task — stricter accepted answers
fl_task_path = ROOT / "tasks" / "enterprise-fnf-synthesis.json"
fl_task = json.loads(fl_task_path.read_text(encoding="utf-8"))

fl_task["expected_facts"]["affected_kpi"]["accepted"] = [
    "escrow disbursement reconciliation variance",
    "escrow_recon_variance",
]
fl_task["expected_facts"]["impacted_asset"]["accepted"] = [
    "finance.disbursement_recon_daily",
]
fl_task["expected_facts"]["root_cause"]["accepted"] = [
    "disbursement recon transform joined party_identity_bridge by normalized_tax_id",
    "party identity bridge reused normalized_tax_id across buyer and seller roles",
    "settlement_disbursement_recon_v3 joined party_identity_bridge using normalized_tax_id",
]
fl_task["expected_facts"]["bad_join_key"]["accepted"] = [
    "normalized_tax_id instead of closing_party_role_id",
    "normalized_tax_id not closing_party_role_id",
]

# Add new distractor paths to trace_expectations
fl_task["trace_expectations"]["distractor_paths"].extend([
    "/enterprise-fnf/data-platform/pipelines/settlement/disbursement-recon/v1-transform.md",
    "/enterprise-fnf/data-platform/pipelines/settlement/disbursement-recon/v2-transform.md",
    "/enterprise-fnf/data-platform/warehouses/enterprise-dw/schemas/settlement/tables/escrow-clearing-fact.md",
    "/enterprise-fnf/business/title/regions/florida/underwriters/old-republic-national-title/purchase-closings.md",
    "/enterprise-fnf/incidents/2026-09-california-refi-fee/root-cause.md",
])

fl_task_path.write_text(json.dumps(fl_task, indent=2) + "\n", encoding="utf-8")
print(f"updated {fl_task_path}")


# ---------------------------------------------------------------------------
# 4. ANSWER + TRACE for CA task
# ---------------------------------------------------------------------------

ca_answer = {
    "task_id": "california-refi-fee-v1",
    "bundle_variant": "strict",
    "answer": (
        "California refinance settlement fee revenue was understated for FNF National Title closings because "
        "settlement_fee_revenue_v2 joined closing_order_fact using loan_number instead of closing_id. "
        "loan_number is not unique at closing grain for refinance transactions, causing fee rows to be "
        "de-duplicated incorrectly and suppressing aggregated revenue in finance.settlement_fee_revenue_daily. "
        "The fix is to rebuild the view using closing_id, quarantine loan_number joins, and backfill "
        "California refinance closings for FNF National Title."
    ),
    "facts": {
        "affected_kpi": "settlement fee revenue variance",
        "affected_segment": "California refinance closings for FNF National Title",
        "root_cause": "settlement_fee_revenue_v2 joined closing_order_fact by loan_number",
        "bad_join_key": "loan_number instead of closing_id",
        "correct_join_key": "closing_id",
        "impacted_asset": "finance.settlement_fee_revenue_daily",
        "pipeline": "settlement_fee_revenue_v2",
        "remediation": "switch settlement_fee_revenue_v2 to closing_id, quarantine loan_number joins, and backfill california refinance closings",
    },
    "citations": [
        "/enterprise-fnf/data-platform/warehouses/enterprise-dw/schemas/finance/views/settlement-fee-revenue-daily.md",
        "/enterprise-fnf/data-platform/warehouses/enterprise-dw/schemas/settlement/tables/closing-order-fact.md",
        "/enterprise-fnf/data-platform/pipelines/settlement/fee-recon/v2-transform.md",
        "/enterprise-fnf/business/title/regions/california/underwriters/fnf-national-title/refinance-closings.md",
        "/enterprise-fnf/incidents/2026-09-california-refi-fee/root-cause.md",
        "/enterprise-fnf/incidents/2026-09-california-refi-fee/remediation.md",
    ],
}
answer_path = ROOT / "answers" / "california-refi-fee-correct.json"
answer_path.write_text(json.dumps(ca_answer, indent=2) + "\n", encoding="utf-8")
print(f"wrote {answer_path}")

ca_trace = {
    "agent": "example-agent",
    "bundle_variant": "strict",
    "duration_ms": 134000,
    "events": [
        {"ts_ms": 0,      "type": "read", "path": "/index.md"},
        {"ts_ms": 8000,   "type": "read", "path": "/enterprise-fnf/index.md"},
        {"ts_ms": 19000,  "type": "read", "path": "/enterprise-fnf/incidents/index.md"},
        {"ts_ms": 31000,  "type": "read", "path": "/enterprise-fnf/incidents/2026-09-california-refi-fee/root-cause.md"},
        {"ts_ms": 48000,  "type": "read", "path": "/enterprise-fnf/incidents/2026-09-california-refi-fee/remediation.md"},
        {"ts_ms": 61000,  "type": "read", "path": "/enterprise-fnf/data-platform/pipelines/settlement/fee-recon/v2-transform.md"},
        {"ts_ms": 77000,  "type": "read", "path": "/enterprise-fnf/data-platform/warehouses/enterprise-dw/schemas/finance/views/settlement-fee-revenue-daily.md"},
        {"ts_ms": 93000,  "type": "read", "path": "/enterprise-fnf/data-platform/warehouses/enterprise-dw/schemas/settlement/tables/closing-order-fact.md"},
        {"ts_ms": 112000, "type": "read", "path": "/enterprise-fnf/business/title/regions/california/underwriters/fnf-national-title/refinance-closings.md"},
        {"ts_ms": 134000, "type": "answer"},
    ],
}
trace_path = ROOT / "traces" / "california-refi-fee-efficient.json"
trace_path.write_text(json.dumps(ca_trace, indent=2) + "\n", encoding="utf-8")
print(f"wrote {trace_path}")

# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------
total = 0
for bundle_name, bundle in BUNDLES.items():
    count = len(list((bundle / EFP).rglob("*.md")))
    print(f"  {bundle_name}: {count} .md files in enterprise-fnf")
    total += count
print(f"Done. Total enterprise-fnf .md files across all bundles: {total}")
