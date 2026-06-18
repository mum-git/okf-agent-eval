---
id: fnf.dw.settlement.table.escrow_clearing_fact
type: warehouse_table
title: settlement.escrow_clearing_fact
owner: concept-knowledge-team
warehouse: enterprise_dw
schema: settlement
object_name: escrow_clearing_fact
grain: clearing_event_id
primary_key: clearing_event_id
foreign_keys:
  - escrow_disbursement_id
  - closing_id
  - closing_party_role_id
tags:
  - enterprise-fnf
  - escrow
  - settlement
  - distractor
domain: data-platform
area: tables
depth: 7
metadata_profile: concept-drift-enterprise
task_hint: "florida fnf national title escrow disbursement reconciliation california refinance fee revenue"
routing_hint: "inspect finance view, settlement table, party bridge, pipeline, business segment, and incident"
---
# settlement.escrow_clearing_fact

Escrow clearing fact records ledger clearing events confirming disbursement
settlement. It is a downstream confirmation table, not a source of
disbursement rows.

`finance.disbursement_recon_daily` compares `escrow_disbursement_fact` against
clearing totals. The September 15 incident was caused by incorrect party-role
joining in the recon pipeline, not by data errors in this clearing table.
