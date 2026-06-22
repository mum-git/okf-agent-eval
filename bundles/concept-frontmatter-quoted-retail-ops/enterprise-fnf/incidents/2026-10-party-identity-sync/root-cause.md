---
id: fnf.incident.2026_10_party_identity_sync.root_cause
type: root_cause
title: Party identity sync root cause
incident_id: fnf-inc-2026-10-party-identity-sync
affected_kpi: party identity match rate
affected_segment: nationwide closings
pipeline: party_identity_sync_v2
bad_join_key: normalized_tax_id
correct_join_key: party_id
impacted_asset: party.party_identity_bridge
tags:
  - enterprise-fnf
  - root-cause
  - party
  - distractor
---
# Root Cause

The October 2026 party identity sync incident caused duplicate party rows in
`party.party_identity_bridge`. `party_identity_sync_v2` merged incoming party
records by `normalized_tax_id` instead of `party_id`, collapsing distinct legal
entities that shared a tax identifier (joint ventures, successor entities).

This incident corrupted the bridge table itself, distinct from the September 15
escrow disbursement incident where the pipeline joined an already-correct bridge
table using the wrong key.
