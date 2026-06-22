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
