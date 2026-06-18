---
id: fnf.dw.finance.view.escrow_balance_daily
type: warehouse_view
title: finance.escrow_balance_daily
owner: enterprise-data-governance
warehouse: enterprise_dw
schema: finance
object_name: escrow_balance_daily
grain: "business_date, escrow_account_id"
primary_kpi: "escrow hold balance variance"
upstream:
  - fnf.dw.settlement.table.disbursement_hold_fact
tags:
  - enterprise-fnf
  - finance
  - escrow
  - distractor
domain: data-platform
area: views
depth: 7
metadata_profile: uniform-enterprise
task_hint: "florida fnf national title escrow disbursement reconciliation california refinance fee revenue"
routing_hint: "inspect finance view, settlement table, party bridge, pipeline, business segment, and incident"
---
# finance.escrow_balance_daily

`finance.escrow_balance_daily` is the KPI view for escrow hold balance
variance. It tracks open disbursement holds by escrow account.

This view was impacted by the August 2026 escrow hold mismatch incident
involving `escrow_balance_sync_v1`. It is not the impacted view for the
September 15 escrow disbursement reconciliation incident, which affected
`finance.disbursement_recon_daily`.
