---
id: fnf.incident.2026_10_party_identity_sync.remediation
type: remediation
title: "Party identity sync remediation"
incident_id: fnf-inc-2026-10-party-identity-sync
owner: concept-knowledge-team
tags:
  - enterprise-fnf
  - remediation
  - party
  - distractor
domain: incidents
area: party-identity-sync
depth: 3
metadata_profile: concept-drift-enterprise
---
# Remediation

Revert `party_identity_sync_v2` to merge on `party_id`. Rebuild
`party.party_identity_bridge` from the pre-merge snapshot and reprocess
downstream reconciliation workloads that consumed the corrupted bridge.
