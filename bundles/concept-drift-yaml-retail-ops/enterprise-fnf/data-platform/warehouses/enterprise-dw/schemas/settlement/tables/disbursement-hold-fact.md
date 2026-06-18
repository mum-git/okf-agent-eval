---
id: fnf.dw.settlement.table.disbursement_hold_fact
type: warehouse_table
title: settlement.disbursement_hold_fact
owner: concept-knowledge-team
warehouse: enterprise_dw
schema: settlement
object_name: disbursement_hold_fact
grain: disbursement_hold_id
primary_key: disbursement_hold_id
foreign_keys:
  - escrow_account_id
  - closing_id
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
# settlement.disbursement_hold_fact

Disbursement hold fact stores escrow hold events prior to disbursement release.
Each row represents a hold placed on an escrow account for a specific closing.

This table was involved in the August 2026 escrow hold mismatch incident
(where `escrow_account_id` was used incorrectly) but is not involved in the
September 15 escrow disbursement reconciliation incident.
