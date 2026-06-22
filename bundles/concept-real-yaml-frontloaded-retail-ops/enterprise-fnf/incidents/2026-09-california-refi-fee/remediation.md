---
id: fnf.incident.2026_09_california_refi_fee.remediation
type: remediation
title: California refinance fee remediation
incident_id: fnf-inc-2026-09-california-refi-fee
owner: settlement-data-engineering
tags:
  - enterprise-fnf
  - remediation
  - california
---
# Remediation

Switch `settlement_fee_revenue_v2` to join `closing_order_fact` on `closing_id`
instead of `loan_number`. Quarantine `loan_number` joins in fee revenue
workloads, and backfill `finance.settlement_fee_revenue_daily` for California
refinance closings under FNF National Title for the affected window.
