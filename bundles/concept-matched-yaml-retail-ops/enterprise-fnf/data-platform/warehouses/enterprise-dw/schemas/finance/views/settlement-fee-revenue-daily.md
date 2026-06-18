---
id: fnf.dw.finance.view.settlement_fee_revenue_daily
type: warehouse_view
title: finance.settlement_fee_revenue_daily
owner: enterprise-data-governance
warehouse: enterprise_dw
schema: finance
object_name: settlement_fee_revenue_daily
grain: "business_date, state_code, underwriter_code, closing_type"
primary_kpi: "settlement fee revenue variance"
upstream:
  - fnf.dw.settlement.table.closing_order_fact
pii_classification: internal-confidential
sla: "T+1 07:00 ET"
tags:
  - enterprise-fnf
  - finance
  - revenue
domain: data-platform
area: views
depth: 7
metadata_profile: uniform-enterprise
task_hint: "florida fnf national title escrow disbursement reconciliation california refinance fee revenue"
routing_hint: "inspect finance view, settlement table, party bridge, pipeline, business segment, and incident"
---
# finance.settlement_fee_revenue_daily

`finance.settlement_fee_revenue_daily` is the KPI view for settlement fee
revenue variance. It aggregates title and closing fees from
`settlement.closing_order_fact` by business date, state, underwriter, and
closing type.

Joins to `closing_order_fact` must use `closing_id`. `loan_number` must not be
used as a join key because a refinance transaction on the same property can
carry the same loan number across multiple closing order rows.

This view was affected by the September 10, 2026 California refinance fee
understatement incident. It is not the impacted view for the September 15
escrow disbursement reconciliation incident, which affected
`finance.disbursement_recon_daily`.
