---
id: fnf.dw.party.table.closing_agent_lookup
type: warehouse_table
title: party.closing_agent_lookup
owner: enterprise-data-governance
warehouse: enterprise_dw
schema: party
object_name: closing_agent_lookup
grain: agent_license_id
primary_key: agent_license_id
alternate_keys:
  - agent_tax_id
  - party_id
tags:
  - enterprise-fnf
  - party
  - agent
  - distractor
domain: data-platform
area: tables
depth: 7
metadata_profile: uniform-enterprise
task_hint: "florida fnf national title escrow disbursement reconciliation"
routing_hint: "inspect finance view, settlement table, party bridge, pipeline, business segment, and incident"
---
# party.closing_agent_lookup

Closing agent lookup maps licensed title agents to closings. The table grain
is `agent_license_id`.

`agent_tax_id` is an alternate identifier for the agent entity, distinct from
the `normalized_tax_id` used in `party_identity_bridge` for closing party roles.
This table was not involved in the September 15 escrow disbursement
reconciliation incident.
