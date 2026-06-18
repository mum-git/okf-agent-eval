---
id: fnf.pipeline.settlement_disbursement_recon_v3
type: pipeline_transform
title: settlement_disbursement_recon_v3
owner: concept-knowledge-team
schedule: hourly
target_asset: fnf.dw.finance.view.disbursement_recon_daily
bad_join_key: normalized_tax_id
correct_join_key: closing_party_role_id
tags:
  - enterprise-fnf
  - pipeline
  - root-cause
domain: data-platform
area: disbursement-recon
depth: 5
metadata_profile: concept-drift-enterprise
task_hint: "florida fnf national title escrow disbursement reconciliation"
---
# settlement_disbursement_recon_v3

`settlement_disbursement_recon_v3` builds `finance.disbursement_recon_daily`
from escrow disbursement and ledger clearing records.

The September 15 deploy introduced a join from
`settlement.escrow_disbursement_fact` to `party.party_identity_bridge` using
`normalized_tax_id`. That join should use `closing_party_role_id`.

