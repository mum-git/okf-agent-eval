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
