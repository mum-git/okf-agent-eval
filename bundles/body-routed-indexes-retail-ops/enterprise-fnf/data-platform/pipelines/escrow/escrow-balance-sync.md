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
