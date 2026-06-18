---
id: fnf.incident.2026_08_escrow_hold_mismatch.remediation
type: remediation
title: "Escrow hold mismatch remediation"
incident_id: fnf-inc-2026-08-escrow-hold-mismatch
owner: enterprise-data-governance
tags:
  - enterprise-fnf
  - remediation
  - escrow
  - distractor
domain: incidents
area: escrow-hold-mismatch
depth: 2
metadata_profile: uniform-enterprise
---
# Remediation

Switch `escrow_balance_sync_v1` to join on `disbursement_hold_id` and rebuild
`finance.escrow_balance_daily` for the affected window. Quarantine
`escrow_account_id` joins in hold-balance aggregations.
