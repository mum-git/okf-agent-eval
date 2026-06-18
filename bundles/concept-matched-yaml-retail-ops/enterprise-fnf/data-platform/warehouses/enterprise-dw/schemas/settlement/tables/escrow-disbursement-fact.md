---
id: fnf.dw.settlement.table.escrow_disbursement_fact
type: warehouse_table
title: settlement.escrow_disbursement_fact
owner: enterprise-data-governance
warehouse: enterprise_dw
schema: settlement
object_name: escrow_disbursement_fact
grain: escrow_disbursement_id
primary_key: escrow_disbursement_id
foreign_keys:
  - closing_id
  - closing_party_role_id
  - underwriter_id
pii_classification: restricted-financial
tags:
  - enterprise-fnf
  - escrow
  - settlement
domain: data-platform
area: tables
depth: 6
metadata_profile: uniform-enterprise
task_hint: "florida fnf national title escrow disbursement reconciliation california refinance fee revenue"
routing_hint: "inspect finance view, settlement table, party bridge, pipeline, business segment, and incident"
---
# settlement.escrow_disbursement_fact

Escrow disbursement fact stores disbursement ledger events for purchase and
refinance closings. Each row belongs to a specific `closing_party_role_id`.

For reconciliation joins, `closing_party_role_id` is the correct key for party
role attribution. `normalized_tax_id` is not unique at closing-role grain.

