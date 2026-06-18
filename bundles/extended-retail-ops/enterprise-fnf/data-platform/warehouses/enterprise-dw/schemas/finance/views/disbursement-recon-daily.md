---
id: fnf.dw.finance.view.disbursement_recon_daily
type: warehouse_view
title: finance.disbursement_recon_daily
owner: finance-data-products
warehouse: enterprise_dw
schema: finance
object_name: disbursement_recon_daily
grain: business_date, state_code, underwriter_code, closing_type
primary_kpi: escrow disbursement reconciliation variance
upstream:
  - fnf.dw.settlement.table.escrow_disbursement_fact
  - fnf.dw.party.table.party_identity_bridge
pii_classification: internal-confidential
sla: T+1 06:00 ET
tags:
  - enterprise-fnf
  - finance
  - reconciliation
---
# finance.disbursement_recon_daily

`finance.disbursement_recon_daily` is the KPI view for escrow disbursement
reconciliation variance. It compares escrow disbursements posted in settlement
systems with ledger clearing totals.

The view must join party identity through `closing_party_role_id`. Joining
through `normalized_tax_id` is prohibited because the same tax identifier can
appear in multiple buyer, seller, trust, or entity roles inside a closing.

