---
id: fnf.dw.settlement.table.wire_transfer_fact
type: warehouse_table
title: settlement.wire_transfer_fact
owner: settlement-data-products
warehouse: enterprise_dw
schema: settlement
object_name: wire_transfer_fact
grain: wire_transfer_id
primary_key: wire_transfer_id
foreign_keys:
  - closing_id
  - escrow_account_id
  - closing_party_role_id
tags:
  - enterprise-fnf
  - settlement
  - wire
  - distractor
---
# settlement.wire_transfer_fact

Wire transfer fact stores outbound settlement wire events. Each wire is
associated with a `closing_id` and `closing_party_role_id` for the receiving
party.

Wire transfer data did not feed `finance.disbursement_recon_daily` in the
September 15 incident. That view sourced from `settlement.escrow_disbursement_fact`.
