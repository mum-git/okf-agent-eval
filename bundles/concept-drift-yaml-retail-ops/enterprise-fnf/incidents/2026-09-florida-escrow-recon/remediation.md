---
id: fnf.incident.2026_09_florida_escrow_recon.remediation
type: remediation
title: "Florida escrow reconciliation remediation"
incident_id: fnf-inc-2026-09-florida-escrow-recon
owner: concept-knowledge-team
tags:
  - enterprise-fnf
  - remediation
domain: incidents
area: 2026-09-florida-escrow-recon
depth: 3
metadata_profile: concept-drift-enterprise
task_hint: "florida fnf national title escrow disbursement reconciliation"
routing_hint: "inspect warehouse schemas, pipelines, business segments, and incident notes"
---
# Remediation

Switch the transform to `closing_party_role_id`, quarantine
`normalized_tax_id` joins in reconciliation workloads, and backfill Florida
purchase closings for FNF National Title.

The rebuild target is `finance.disbursement_recon_daily`, sourced from
`settlement.escrow_disbursement_fact`.

