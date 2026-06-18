---
id: fnf.pipeline.party_identity_sync_v2
type: pipeline_transform
title: party_identity_sync_v2
owner: concept-knowledge-team
schedule: daily
target_asset: fnf.dw.party.table.party_identity_bridge
tags:
  - enterprise-fnf
  - pipeline
  - party
  - distractor
domain: data-platform
area: party
depth: 4
metadata_profile: concept-drift-enterprise
---
# party_identity_sync_v2

`party_identity_sync_v2` ingests party identity records from upstream source
systems and merges them into `party.party_identity_bridge` using `party_id` as
the deduplication key.

This pipeline does not build the finance reconciliation views. It was involved
in the October 2026 party identity incident, not the September 15 escrow
disbursement reconciliation incident.
