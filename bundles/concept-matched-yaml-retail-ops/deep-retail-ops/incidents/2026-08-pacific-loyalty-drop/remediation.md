---
id: deep.incident.2026_08_pacific_loyalty_drop.remediation
type: remediation
title: "Pacific loyalty conversion drop remediation"
incident_id: inc-2026-08-pacific-loyalty-drop
experiment_id: exp-2026-q3-loyalty-wallet-accelerator
tags:
  - deep-benchmark
  - remediation
domain: incidents
area: 2026-08-pacific-loyalty-drop
depth: 2
metadata_profile: uniform-heavy
owner: knowledge-team
task_hint: "deep retail loyalty conversion synthesis"
routing_hint: "inspect regional metric, experiment, identity key, wallet pipeline, and incident remediation"
---
# Remediation

Disable variant B, purge `wallet_eligibility_cache`, and rebuild allocation by
`customer_profile_id`.

Do not apply the fraud step-up playbook or tax display rollback. Those are
separate distractors.

