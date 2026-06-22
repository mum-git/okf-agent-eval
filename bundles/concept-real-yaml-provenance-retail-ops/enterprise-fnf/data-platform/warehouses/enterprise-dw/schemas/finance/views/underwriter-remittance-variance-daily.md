---
id: fnf.dw.finance.view.underwriter_remittance_variance_daily
type: warehouse_view
title: finance.underwriter_remittance_variance_daily
owner: finance-data-products
warehouse: enterprise_dw
schema: finance
object_name: underwriter_remittance_variance_daily
grain: business_date, underwriter_code
primary_kpi: underwriter remittance variance
upstream:
  - fnf.dw.finance.table.underwriter_remittance_fact
tags:
  - enterprise-fnf
  - finance
  - remittance
  - distractor
---
# finance.underwriter_remittance_variance_daily

`finance.underwriter_remittance_variance_daily` tracks daily premium and fee
remittance variance by underwriter. It is sourced from
`underwriter_remittance_fact`, not from `escrow_disbursement_fact`.

This view was not affected by the September 15 escrow disbursement
reconciliation incident.
