---
id: fnf.dw.finance.table.underwriter_remittance_fact
type: warehouse_table
title: finance.underwriter_remittance_fact
owner: concept-knowledge-team
grain: remittance_id
tags:
  - remittance
domain: data-platform
area: tables
depth: 7
metadata_profile: concept-drift-enterprise
task_hint: "florida fnf national title escrow disbursement reconciliation"
routing_hint: "inspect warehouse schemas, pipelines, business segments, and incident notes"
---
# finance.underwriter_remittance_fact

Underwriter remittance fact stores premium and fee remittance rows. It is
downstream of settlement events but was not duplicated in the incident.

