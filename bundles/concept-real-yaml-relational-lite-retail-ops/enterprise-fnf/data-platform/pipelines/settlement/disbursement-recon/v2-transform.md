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
