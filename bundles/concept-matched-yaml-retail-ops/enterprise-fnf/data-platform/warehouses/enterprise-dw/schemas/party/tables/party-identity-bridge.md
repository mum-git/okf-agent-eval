---
id: fnf.dw.party.table.party_identity_bridge
type: warehouse_table
title: party.party_identity_bridge
owner: enterprise-data-governance
warehouse: enterprise_dw
schema: party
object_name: party_identity_bridge
grain: closing_party_role_id
primary_key: closing_party_role_id
alternate_keys:
  - party_id
  - normalized_tax_id
pii_classification: restricted-pii
tags:
  - enterprise-fnf
  - identity
  - party
domain: data-platform
area: tables
depth: 7
metadata_profile: uniform-enterprise
task_hint: "florida fnf national title escrow disbursement reconciliation"
routing_hint: "inspect finance view, settlement table, party bridge, pipeline, business segment, and incident"
---
# party.party_identity_bridge

Party identity bridge maps parties to their roles in closings. The table grain
is `closing_party_role_id`.

`normalized_tax_id` is an alternate identifier only. It can appear on multiple
party roles in a single closing, including buyer, seller, trust, and business
entity roles. It must not be used to join escrow disbursements to closing roles.

