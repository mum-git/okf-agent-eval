---
id: fnf.incident.2026_08_escrow_hold_mismatch.root_cause
type: root_cause
title: "Escrow hold mismatch root cause"
incident_id: fnf-inc-2026-08-escrow-hold-mismatch
affected_kpi: "escrow hold balance variance"
affected_segment: "Florida purchase closings for Old Republic National Title"
pipeline: escrow_balance_sync_v1
bad_join_key: escrow_account_id
correct_join_key: disbursement_hold_id
impacted_asset: finance.escrow_balance_daily
tags:
  - enterprise-fnf
  - root-cause
  - escrow
  - distractor
domain: incidents
area: escrow-hold-mismatch
depth: 3
metadata_profile: concept-drift-enterprise
owner: concept-knowledge-team
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
