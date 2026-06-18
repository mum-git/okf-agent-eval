---
id: incident.2026_06_margin_anomaly.remediation
type: remediation
title: Remediation for June 2026 margin anomaly
incident_id: inc-2026-06-margin-anomaly
rollout_id: ff-2026-06-pricing-shadow-ledger
owner: finance-analytics
tags:
  - rollback
  - rebuild
---
# Remediation

The approved remediation is to roll back
`ff-2026-06-pricing-shadow-ledger` and rebuild `margin_daily` from
`order_line_id`-deduplicated order line ledger rows.

Do not apply the tax rounding v2 playbook. It is unrelated to this incident.

