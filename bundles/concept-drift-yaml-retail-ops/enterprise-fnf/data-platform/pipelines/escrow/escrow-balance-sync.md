---
id: fnf.pipeline.escrow_balance_sync_v1
type: pipeline_transform
title: escrow_balance_sync_v1
owner: concept-knowledge-team
schedule: hourly
target_asset: fnf.dw.finance.view.escrow_balance_daily
tags:
  - enterprise-fnf
  - pipeline
  - escrow
  - distractor
domain: data-platform
area: escrow
depth: 4
metadata_profile: concept-drift-enterprise
---
# escrow_balance_sync_v1

`escrow_balance_sync_v1` builds `finance.escrow_balance_daily` from
`settlement.disbursement_hold_fact`. It was involved in the August 2026 escrow
hold mismatch incident.

This pipeline does not build `finance.disbursement_recon_daily` and is not
related to the September 15 disbursement reconciliation incident.
