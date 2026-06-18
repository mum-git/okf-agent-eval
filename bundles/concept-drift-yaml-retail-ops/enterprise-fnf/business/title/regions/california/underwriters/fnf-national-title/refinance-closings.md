---
id: fnf.business.title.california.fnf_national_title.refinance_closings
type: business_segment
title: "California refinance closings for FNF National Title"
owner: concept-knowledge-team
region: california
underwriter: "FNF National Title"
closing_type: refinance
critical_kpis:
  - "settlement fee revenue variance"
tags:
  - enterprise-fnf
  - business-segment
  - california
  - revenue
domain: business
area: fnf-national-title
depth: 7
metadata_profile: concept-drift-enterprise
task_hint: "florida fnf national title escrow disbursement reconciliation"
routing_hint: "inspect warehouse schemas, pipelines, business segments, and incident notes"
---
# California Refinance Closings For FNF National Title

California refinance closings under FNF National Title are measured by
settlement fee revenue variance.

This segment was affected by the September 10, 2026 California refinance fee
understatement incident. `settlement_fee_revenue_v2` joined `closing_order_fact`
using `loan_number` instead of `closing_id`, suppressing fee revenue for this
segment.

These closings were not part of the September 15 Florida escrow disbursement
reconciliation incident.
