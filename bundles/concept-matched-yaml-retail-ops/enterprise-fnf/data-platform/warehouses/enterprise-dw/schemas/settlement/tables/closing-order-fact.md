---
id: fnf.dw.settlement.table.closing_order_fact
type: warehouse_table
title: settlement.closing_order_fact
owner: enterprise-data-governance
warehouse: enterprise_dw
schema: settlement
object_name: closing_order_fact
grain: closing_id
primary_key: closing_id
alternate_keys:
  - loan_number
  - order_number
tags:
  - enterprise-fnf
  - settlement
  - closing
domain: data-platform
area: tables
depth: 6
metadata_profile: uniform-enterprise
task_hint: "florida fnf national title escrow disbursement reconciliation california refinance fee revenue"
routing_hint: "inspect finance view, settlement table, party bridge, pipeline, business segment, and incident"
---
# settlement.closing_order_fact

Closing order fact tracks order-level settlement milestones. The table grain
is `closing_id`.

`loan_number` is an alternate attribute, not the grain. A refinance closing on
the same property can carry the same `loan_number` across multiple closing order
rows, making `loan_number` non-unique at closing grain. It must not be used to
join or aggregate closing fees.

This table is the primary upstream of `finance.settlement_fee_revenue_daily`
and was involved in the September 10, 2026 California refinance fee incident.
It is not the duplicated asset in the September 15 escrow disbursement
reconciliation incident.
