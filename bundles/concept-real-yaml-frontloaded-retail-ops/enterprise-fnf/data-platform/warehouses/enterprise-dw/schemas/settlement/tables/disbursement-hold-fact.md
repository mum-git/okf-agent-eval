---
id: fnf.dw.settlement.table.disbursement_hold_fact
type: warehouse_table
title: settlement.disbursement_hold_fact
owner: settlement-data-products
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
---
# settlement.disbursement_hold_fact

Disbursement hold fact stores escrow hold events prior to disbursement release.
Each row represents a hold placed on an escrow account for a specific closing.

This table was involved in the August 2026 escrow hold mismatch incident
(where `escrow_account_id` was used incorrectly) but is not involved in the
September 15 escrow disbursement reconciliation incident.
