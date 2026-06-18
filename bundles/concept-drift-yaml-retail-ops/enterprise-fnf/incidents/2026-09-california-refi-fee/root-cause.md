---
id: fnf.incident.2026_09_california_refi_fee.root_cause
type: root_cause
title: "California refinance fee root cause"
incident_id: fnf-inc-2026-09-california-refi-fee
affected_kpi: "settlement fee revenue variance"
affected_segment: "California refinance closings for FNF National Title"
pipeline: settlement_fee_revenue_v2
bad_join_key: loan_number
correct_join_key: closing_id
impacted_asset: finance.settlement_fee_revenue_daily
tags:
  - enterprise-fnf
  - root-cause
  - california
  - revenue
domain: incidents
area: california-refi-fee
depth: 3
metadata_profile: concept-drift-enterprise
owner: concept-knowledge-team
task_hint: "california fnf national title refinance fee revenue settlement"
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
