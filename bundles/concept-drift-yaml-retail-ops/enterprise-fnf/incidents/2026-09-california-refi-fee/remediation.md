---
id: fnf.incident.2026_09_california_refi_fee.remediation
type: remediation
title: "California refinance fee remediation"
incident_id: fnf-inc-2026-09-california-refi-fee
owner: concept-knowledge-team
tags:
  - enterprise-fnf
  - remediation
  - california
domain: incidents
area: california-refi-fee
depth: 3
metadata_profile: concept-drift-enterprise
task_hint: "california fnf national title refinance fee revenue settlement"
---
# Remediation

Switch `settlement_fee_revenue_v2` to join `closing_order_fact` on `closing_id`
instead of `loan_number`. Quarantine `loan_number` joins in fee revenue
workloads, and backfill `finance.settlement_fee_revenue_daily` for California
refinance closings under FNF National Title for the affected window.
