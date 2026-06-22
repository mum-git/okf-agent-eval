---
id: fnf.incident.2026_09_florida_escrow_recon.remediation
type: remediation
title: Florida escrow reconciliation remediation
incident_id: fnf-inc-2026-09-florida-escrow-recon
owner: settlement-data-engineering
tags:
  - enterprise-fnf
  - remediation
---
# Remediation

Switch the transform to `closing_party_role_id`, quarantine
`normalized_tax_id` joins in reconciliation workloads, and backfill Florida
purchase closings for FNF National Title.

The rebuild target is `finance.disbursement_recon_daily`, sourced from
`settlement.escrow_disbursement_fact`.

