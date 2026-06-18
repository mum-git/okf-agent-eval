---
id: fnf.incident.2026_09_florida_escrow_recon.root_cause
type: root_cause
title: "Florida escrow reconciliation root cause"
incident_id: fnf-inc-2026-09-florida-escrow-recon
affected_kpi: "escrow disbursement reconciliation variance"
affected_segment: "Florida purchase closings for FNF National Title"
pipeline: settlement_disbursement_recon_v3
bad_join_key: normalized_tax_id
correct_join_key: closing_party_role_id
impacted_asset: finance.disbursement_recon_daily
tags:
  - enterprise-fnf
  - root-cause
  - escrow
domain: incidents
area: 2026-09-florida-escrow-recon
depth: 2
metadata_profile: uniform-enterprise
owner: enterprise-data-governance
task_hint: "florida fnf national title escrow disbursement reconciliation"
routing_hint: "inspect warehouse schemas, pipelines, business segments, and incident notes"
---
# Root Cause

The September 15, 2026 Florida escrow reconciliation overstatement was caused
by `settlement_disbursement_recon_v3` joining `party_identity_bridge` by
`normalized_tax_id`.

`normalized_tax_id` matched multiple buyer and seller party roles inside the
same closing. That duplicated escrow disbursements in
`finance.disbursement_recon_daily`. The correct key is
`closing_party_role_id`.

