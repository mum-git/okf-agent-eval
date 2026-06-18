---
id: fnf.dw.party.table.entity_tax_registry
type: warehouse_table
title: party.entity_tax_registry
owner: identity-data-products
warehouse: enterprise_dw
schema: party
object_name: entity_tax_registry
grain: tax_entity_id
primary_key: tax_entity_id
alternate_keys:
  - normalized_tax_id
  - ein
tags:
  - enterprise-fnf
  - party
  - tax
  - distractor
---
# party.entity_tax_registry

Entity tax registry maps corporate and trust entities to their tax identifiers
for remittance and reporting purposes.

`normalized_tax_id` here refers to corporate entities only. It is not the same
usage as the `normalized_tax_id` column in `party_identity_bridge`, which maps
individual closing party roles. This table was not involved in the September 15
escrow disbursement reconciliation incident.
