---
id: fnf.dw.finance.view.disbursement_summary_weekly
type: warehouse_view
title: finance.disbursement_summary_weekly
owner: finance-data-products
warehouse: enterprise_dw
schema: finance
object_name: disbursement_summary_weekly
grain: week_ending_date, state_code, underwriter_code
primary_kpi: weekly disbursement volume
upstream:
  - fnf.dw.finance.view.disbursement_recon_daily
tags:
  - enterprise-fnf
  - finance
  - reconciliation
  - distractor
---
# finance.disbursement_summary_weekly

`finance.disbursement_summary_weekly` is an aggregated weekly rollup of
disbursement reconciliation data sourced from `disbursement_recon_daily`.

Because it is downstream of `disbursement_recon_daily`, it also showed inflated
figures after the September 15 incident. However, it is not the root-cause
impacted asset. Fixing `disbursement_recon_daily` will cascade to correct this
view automatically.
